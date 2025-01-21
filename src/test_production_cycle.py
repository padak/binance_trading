#!/usr/bin/env python3
"""
Production test script that runs one complete BUY/SELL cycle.
This script initializes all required services, executes a single trade cycle,
and provides detailed logging of the process.

TODO:
- Optimize AI consultation frequency to reduce API costs:
  1. Add cooldown period after rejected recommendations (e.g., wait 5-10 minutes instead of 1)
  2. Track market conditions that led to low confidence and skip AI calls in similar conditions
  3. Implement caching for AI recommendations with similar market conditions
  4. Add price change threshold - only consult AI if price moved significantly
  5. Consider implementing a pre-filter using technical indicators before calling AI
"""

import asyncio
import logging
import os
import argparse
from binance import AsyncClient
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv
import signal
from contextlib import asynccontextmanager
import aiohttp

from services.market_data import MarketDataService
from services.sentiment_analyzer import SentimentAnalyzer
from services.correlation_analyzer import CorrelationAnalyzer
from core.state_manager import StateManager

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cleanup(session=None):
    """Cleanup resources"""
    if session and not session.closed:
        await session.close()
    logger.info("Cleanup completed")

@asynccontextmanager
async def managed_resources():
    """Context manager for handling resources"""
    session = None
    try:
        session = aiohttp.ClientSession()
        yield session
    finally:
        await cleanup(session)

def validate_market_data(market_snapshot, sentiment_data, correlation_data):
    """Validate data completeness before consulting AI.
    Only core market data is required, sentiment and correlation are optional but logged."""
    
    # Core market data that must be present
    required_market_data = {
        'price': float,      # Current price is essential
        'volume': float,     # Need volume for liquidity check
    }
    
    # Optional but valuable market data
    optional_market_data = {
        'best_bid': float,
        'best_ask': float,
        'bid_volume': float,
        'ask_volume': float,
        'ma5': float,
        'ma20': float,
        'rsi': float,
        'vwap': float
    }
    
    # Validate required market data
    if not market_snapshot:
        logger.warning("Market snapshot is empty")
        return False
        
    for field, field_type in required_market_data.items():
        if field not in market_snapshot or not isinstance(market_snapshot[field], field_type):
            logger.warning(f"Missing required {field} in market data")
            return False
    
    # Log missing optional data
    for field in optional_market_data:
        if field not in market_snapshot:
            logger.info(f"Optional {field} not available")
    
    # Log missing correlation data
    if not correlation_data or 'btc_correlation' not in correlation_data:
        logger.info("BTC correlation data not available")
    
    # Log available sentiment sources
    if sentiment_data:
        available_sources = []
        if sentiment_data.get('market_mood'):
            available_sources.append("Fear & Greed Index")
        if sentiment_data.get('news_sentiment'):
            available_sources.append("News Sentiment")
        if sentiment_data.get('social_sentiment'):
            available_sources.append("Social Sentiment")
        if available_sources:
            logger.info(f"Available sentiment sources: {', '.join(available_sources)}")
        else:
            logger.info("No sentiment sources available")
    
    return True  # Continue if we have the core market data

def analyze_market_patterns(market_snapshot):
    """Analyze market patterns to determine if conditions are suitable for trading"""
    patterns = {
        'has_sufficient_volume': False,
        'has_price_swings': False,
        'has_order_book_depth': False,
        'pattern_details': []
    }
    
    # Check trading volume
    if market_snapshot.get('volume', 0) > 100000:  # Minimum 100k USDC daily volume
        patterns['has_sufficient_volume'] = True
        patterns['pattern_details'].append(f"High trading volume: {market_snapshot['volume']} USDC/24h")
    
    # Check price swings (if historical data available)
    if 'price_history' in market_snapshot and market_snapshot['price_history']:
        candles = market_snapshot['price_history']
        if len(candles) >= 12:  # Need at least 1 hour of data
            # Calculate overall price change
            first_price = candles[0]['close']
            last_price = candles[-1]['close']
            total_change_pct = ((last_price - first_price) / first_price) * 100
            
            # Calculate individual swings and collect price data
            swings = []
            price_data = []
            for p in candles[-12:]:
                swing_pct = (p['high'] - p['low']) / p['low'] * 100
                swings.append(swing_pct)
                price_data.append(f"{datetime.fromtimestamp(p['timestamp']/1000).strftime('%H:%M')}: "
                                f"H={p['high']:.2f} L={p['low']:.2f} ({swing_pct:+.2f}%)")
            
            avg_swing = sum(swings) / len(swings)
            max_swing = max(swings)
            
            # Log all price movement details
            patterns['pattern_details'].append(f"Price movement details:")
            patterns['pattern_details'].append(f"  - Hour start price: {first_price:.2f} USDC")
            patterns['pattern_details'].append(f"  - Current price: {last_price:.2f} USDC")
            patterns['pattern_details'].append(f"  - Total change: {total_change_pct:+.2f}% in last hour")
            patterns['pattern_details'].append(f"  - Average swing: {avg_swing:.2f}% per 5min")
            patterns['pattern_details'].append(f"  - Largest swing: {max_swing:.2f}%")
            patterns['pattern_details'].append(f"  - Last hour price swings:")
            for pd in price_data:
                patterns['pattern_details'].append(f"    {pd}")
            
            # Check if we have sufficient movement
            if abs(total_change_pct) > 0.5 or max_swing > 0.5:
                patterns['has_price_swings'] = True
                patterns['pattern_details'].append("  ✓ Sufficient price movement detected")
            else:
                patterns['pattern_details'].append("  ✗ Insufficient price movement:")
                patterns['pattern_details'].append(f"    - Need >0.5% total change (current: {abs(total_change_pct):.2f}%)")
                patterns['pattern_details'].append(f"    - OR >0.5% swing (current max: {max_swing:.2f}%)")
        else:
            candles_count = len(candles)
            patterns['pattern_details'].append(f"Price history incomplete: Have {candles_count}/12 5-min candles")
            if candles_count > 0:
                # Show what data we do have
                last_candle = candles[-1]
                patterns['pattern_details'].append(f"Latest candle: H={last_candle['high']:.2f} L={last_candle['low']:.2f}")
            patterns['pattern_details'].append(f"Waiting for more data (need 1 hour of history)")
    else:
        patterns['pattern_details'].append("Price history not available")
        patterns['pattern_details'].append("Check if historical data loading is working correctly")
    
    # Check order book depth
    bid_depth = market_snapshot.get('bid_volume', 0)
    ask_depth = market_snapshot.get('ask_volume', 0)
    if bid_depth > 10000 and ask_depth > 10000:  # Minimum 10k USDC on each side
        patterns['has_order_book_depth'] = True
        patterns['pattern_details'].append(f"Order book status: DEEP - {bid_depth:.0f} USDC bids / {ask_depth:.0f} USDC asks")
    else:
        patterns['pattern_details'].append(f"Order book status: SHALLOW - {bid_depth:.0f} USDC bids / {ask_depth:.0f} USDC asks")
    
    return patterns

async def run_single_cycle(dry_run=False):
    """Run a single trading cycle with proper cleanup"""
    try:
        async with managed_resources() as session:
            # Initialize services
            api_key = os.getenv("BINANCE_TRADE_API_KEY")
            api_secret = os.getenv("BINANCE_TRADE_API_SECRET")
            
            if not api_key or not api_secret:
                raise ValueError("Binance Trading API credentials not found")
            
            client = await AsyncClient.create(api_key, api_secret)
            market_data = MarketDataService("TRUMPUSDC")
            sentiment = SentimentAnalyzer(client)
            correlation = CorrelationAnalyzer(client)
            state_manager = StateManager("TRUMPUSDC")
            
            # Start services
            await market_data.start(api_key=api_key, api_secret=api_secret)
            if not dry_run:
                await state_manager.start(api_key=api_key, api_secret=api_secret)
            
            # Wait for initial data collection
            logger.info("Waiting for initial market data collection...")
            await asyncio.sleep(5)  # Wait for WebSockets to connect and receive initial data
            
            logger.info("Analyzing market conditions...")
            try:
                while True:
                    # Get market data
                    market_snapshot = await market_data.get_market_snapshot(max_retries=3, retry_delay=2.0)
                    
                    if not market_snapshot.get('price'):
                        logger.warning("Failed to get valid market price, waiting 60 seconds...")
                        await asyncio.sleep(60)
                        continue
                    
                    # Print market analysis
                    logger.info("\nMarket Analysis:")
                    logger.info(f"Current Price: {market_snapshot['price']} USDC")
                    
                    # Analyze market patterns
                    patterns = analyze_market_patterns(market_snapshot)
                    
                    for detail in patterns['pattern_details']:
                        logger.info(detail)
                    
                    # Only proceed if we have good trading conditions
                    if patterns['has_sufficient_volume'] and patterns['has_price_swings']:
                        # Get additional data for AI
                        sentiment_data = await sentiment.get_sentiment_data("TRUMP")
                        correlation_data = await correlation.get_correlation_data("TRUMPUSDC")
                        
                        # Consult AI
                        buy_decision = await state_manager.consult_ai(
                            "BUY",
                            market_snapshot,
                            sentiment_data,
                            correlation_data
                        )
                        
                        logger.info("\nAI Analysis:")
                        logger.info(f"Suggested Entry Price: {buy_decision['price']} USDC")
                        logger.info(f"Confidence Score: {buy_decision['confidence']}")
                        logger.info(f"Pattern Recognition: {buy_decision['reasoning']}")
                        
                        if dry_run:
                            logger.info("\nDRY RUN - Would place order:")
                            logger.info(f"Type: BUY")
                            logger.info(f"Price: {buy_decision['price']} USDC")
                            logger.info(f"Size: 0.25 TRUMP")
                            await asyncio.sleep(60)
                            continue
                        
                        # Place order if price is valid
                        if buy_decision["price"] > 0:
                            logger.info("Placing BUY order...")
                            await state_manager.place_buy_order(buy_decision["price"], Decimal("0.25"))
                            break
                    else:
                        logger.info("\nInsufficient market conditions for trading:")
                        if not patterns['has_sufficient_volume']:
                            logger.info("- Low trading volume")
                            # Show volume details
                            logger.info(f"  Current volume: {market_snapshot.get('volume', 0):.2f} USDC/24h")
                            logger.info(f"  Required: >100,000 USDC/24h")
                            
                        if not patterns['has_price_swings']:
                            logger.info("- Insufficient price movement")
                            # Show price movement details that we collected
                            price_details = [d for d in patterns['pattern_details'] 
                                          if "price" in d.lower() or "swing" in d.lower()]
                            for detail in price_details:
                                logger.info(f"  {detail}")
                            
                        if not patterns['has_order_book_depth']:
                            logger.info("- Shallow order book")
                            # Show order book details
                            bid_depth = market_snapshot.get('bid_volume', 0)
                            ask_depth = market_snapshot.get('ask_volume', 0)
                            logger.info(f"  Current depth: {bid_depth:.0f} USDC bids / {ask_depth:.0f} USDC asks")
                            logger.info(f"  Required: >10,000 USDC on each side")
                        
                    logger.info("\nWaiting 60 seconds before next analysis...")
                    try:
                        await asyncio.sleep(60)
                    except asyncio.CancelledError:
                        logger.info("Received shutdown signal during wait")
                        raise
                        
            except asyncio.CancelledError:
                logger.info("Shutting down during analysis...")
                await market_data.stop()
                if not dry_run:
                    await state_manager.stop()
                await cleanup(session)
                return
            
            if dry_run:
                return
                
            # Only proceed to wait for order if we successfully placed one
            if state_manager.current_position is None:
                logger.info("No buy order placed, exiting...")
                return
                
            # Wait for BUY order to fill
            logger.info("Waiting for BUY order to fill...")
            while state_manager.current_position is None:
                await asyncio.sleep(5)
            
            entry_price = state_manager.current_position.entry_price
            logger.info(f"BUY order filled at {entry_price}")
            
            # Wait for SELL conditions
            logger.info("Waiting for optimal SELL conditions...")
            while True:
                # Get current market data
                market_snapshot = await market_data.get_market_snapshot()
                current_price = Decimal(market_snapshot["price"])
                
                # Only consider selling if we're in profit
                if current_price > entry_price:
                    sentiment_data = await sentiment.get_sentiment_data("TRUMP")
                    correlation_data = await correlation.get_correlation_data("TRUMPUSDC")
                    
                    # Consult AI for SELL decision
                    sell_decision = await state_manager.consult_ai(
                        "SELL",
                        market_snapshot,
                        sentiment_data,
                        correlation_data
                    )
                    
                    if sell_decision["confidence"] > 0.7:
                        logger.info(f"AI recommends SELL at {sell_decision['price']} with confidence {sell_decision['confidence']}")
                        await state_manager.place_sell_order(sell_decision["price"], state_manager.current_position.quantity)
                        break
                        
                await asyncio.sleep(60)  # Check every minute
                
            # Wait for SELL order to fill
            logger.info("Waiting for SELL order to fill...")
            while state_manager.current_position is not None:
                await asyncio.sleep(5)
            
            # Log final balance and trade summary
            final_balance = await state_manager.get_available_balance()
            profit = final_balance - initial_balance
            logger.info(f"Trade completed!")
            logger.info(f"Final USDC Balance: {final_balance}")
            logger.info(f"Profit/Loss: {profit} USDC")
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Error during trading cycle: {e}")
    finally:
        logger.info("Shutting down gracefully...")
        # Cleanup
        await market_data.stop()
        await client.close_connection()

def handle_signal(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    # Get the current event loop
    loop = asyncio.get_event_loop()
    # Cancel all running tasks
    for task in asyncio.all_tasks(loop):
        task.cancel()

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run trading cycle')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no orders placed)')
    args = parser.parse_args()
    
    try:
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        
        await run_single_cycle(dry_run=args.dry_run)
    except asyncio.CancelledError:
        logger.info("Main task cancelled")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        logger.info("Shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True) 