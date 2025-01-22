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
import time
from binance.enums import *  # Import Binance enums

from services.market_data import MarketDataService
from services.sentiment_analyzer import SentimentAnalyzer
from services.correlation_analyzer import CorrelationAnalyzer
from core.state_manager import StateManager, TradingState

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cleanup(self):
    """Cleanup resources properly"""
    try:
        logging.info("Starting cleanup...")
        
        # Stop market data service
        if hasattr(self, 'market_data'):
            await self.market_data.stop()
            logging.info("Market data service stopped")
            
        # Close Binance client connection
        if hasattr(self, 'client'):
            await self.client.close_connection()
            logging.info("Binance client connection closed")
            
        # Close any remaining aiohttp sessions
        for task in asyncio.all_tasks():
            if 'aiohttp' in str(task):
                try:
                    task.cancel()
                    await task
                except asyncio.CancelledError:
                    pass
                    
        logging.info("Cleanup completed successfully")
    except Exception as e:
        logging.error(f"Error during cleanup: {str(e)}")
    finally:
        logging.info("Shutdown complete")

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
    client = None
    market_data = None
    state_manager = None
    
    try:
        async with managed_resources() as session:
            # Initialize services
            api_key = os.getenv("BINANCE_TRADE_API_KEY")
            api_secret = os.getenv("BINANCE_TRADE_API_SECRET")
            
            if not api_key or not api_secret:
                raise ValueError("Binance Trading API credentials not found")
            
            # Initialize client without recvWindow
            client = await AsyncClient.create(
                api_key=api_key,
                api_secret=api_secret
            )

            market_data = MarketDataService("TRUMPUSDC")
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
            
            # Get market data
            market_snapshot = await market_data.get_market_snapshot(max_retries=3, retry_delay=2.0)
            if not market_snapshot.get('price'):
                raise ValueError("Failed to get valid market price")
            
            # Print market analysis
            logger.info("\nMarket Analysis:")
            logger.info(f"Current Price: {market_snapshot['price']} USDC")
            
            # Analyze market patterns
            patterns = analyze_market_patterns(market_snapshot)
            for detail in patterns['pattern_details']:
                logger.info(detail)
            
            if not (patterns['has_sufficient_volume'] and patterns['has_price_swings']):
                raise ValueError("Insufficient market conditions for trading")
            
            # Get correlation data for AI
            correlation_data = await correlation.get_correlation_data("TRUMPUSDC")
            
            # Consult AI for BUY
            buy_decision = await state_manager.consult_ai(
                "BUY",
                market_snapshot,
                None,  # Skip sentiment data
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
                return
            
            # Place BUY order
            if buy_decision["price"] > 0:
                logger.info("Placing BUY order...")
                
                # Check available balance and calculate maximum quantity
                available_balance = await state_manager.get_available_balance()
                price = Decimal(str(buy_decision["price"]))
                max_quantity = (available_balance * Decimal("0.99")) / price  # Use 99% of balance to account for fees
                
                # Apply LOT_SIZE rules for TRUMPUSDC
                MIN_QTY = Decimal("0.001")  # Minimum quantity
                STEP_SIZE = Decimal("0.001")  # Must be multiple of this
                MIN_NOTIONAL = Decimal("1.0")  # Minimum order value in USDC
                
                # Calculate valid quantity respecting LOT_SIZE rules
                # Target 1.2 USDC order value
                target_value = Decimal("1.2")
                desired_quantity = min((target_value / price).quantize(STEP_SIZE), max_quantity)
                # Round down to nearest step size
                valid_quantity = (desired_quantity // STEP_SIZE) * STEP_SIZE
                
                # Check minimum quantity
                if valid_quantity < MIN_QTY:
                    logger.error(f"Calculated quantity {valid_quantity} is below minimum {MIN_QTY}")
                    return
                
                # Check minimum order value
                order_value = valid_quantity * price
                if order_value < MIN_NOTIONAL:
                    # Adjust quantity to meet minimum order value
                    valid_quantity = (MIN_NOTIONAL / price).quantize(STEP_SIZE, rounding='ROUND_UP')
                    logger.info(f"Adjusted quantity to {valid_quantity} to meet minimum order value of {MIN_NOTIONAL} USDC")
                
                logger.info(f"Available USDC: {available_balance}")
                logger.info(f"Order Quantity: {valid_quantity} TRUMP at {price} USDC")
                logger.info(f"Total Order Value: {valid_quantity * price} USDC")
                
                try:
                    order = await state_manager.place_buy_order(
                        price=price,
                        quantity=valid_quantity
                    )
                    logger.info("Waiting for BUY order to fill...")
                    
                    # Check order status every second
                    while True:
                        order_status = await state_manager.client.get_order(
                            symbol=state_manager.symbol,
                            orderId=order['orderId']
                        )
                        
                        if order_status['status'] == 'FILLED':
                            # Update state manager with the fill
                            await state_manager.handle_order_update(order_status)
                            entry_price = Decimal(str(order_status['price']))
                            logger.info(f"BUY order filled at {entry_price}")
                            
                            # Use the AI recommendation we already have for the exit price
                            # The market conditions haven't changed significantly in these few seconds
                            if buy_decision["confidence"] > 0.7:
                                # Calculate sell price with 0.5% minimum margin, rounded to 2 decimal places
                                margin = max(Decimal("0.005"), Decimal("0.01"))  # Use 1% if AI is confident
                                sell_price = (entry_price * (Decimal("1") + margin)).quantize(Decimal("0.01"))
                                
                                logger.info(f"Using {margin*100:.1f}% margin based on market conditions")
                                logger.info(f"Placing SELL order at {sell_price} USDC ({margin*100:.1f}% profit target)")
                                
                                # Get quantity from current position
                                sell_quantity = state_manager.current_position.quantity
                                logger.info(f"Selling position quantity: {sell_quantity} TRUMP")
                                
                                # Place sell order immediately
                                await state_manager.place_sell_order(
                                    price=sell_price,
                                    quantity=sell_quantity
                                )
                                
                                # Monitor SELL order status
                                logger.info("Waiting for SELL order to fill...")
                                sell_orders = await state_manager.client.get_open_orders(
                                    symbol=state_manager.symbol,
                                    recvWindow=60000  # Add recvWindow parameter
                                )
                                sell_order = next((order for order in sell_orders if order['side'] == 'SELL'), None)
                                
                                if sell_order:
                                    last_check_time = time.time()
                                    while True:
                                        current_time = time.time()
                                        
                                        # Refresh client connection every 5 minutes
                                        if current_time - last_check_time > 300:  # 5 minutes
                                            logger.info("Refreshing API connection...")
                                            await state_manager.client.close_connection()
                                            state_manager.client = await AsyncClient.create(
                                                api_key=os.getenv("BINANCE_TRADE_API_KEY"),
                                                api_secret=os.getenv("BINANCE_TRADE_API_SECRET")
                                            )
                                            last_check_time = current_time
                                        
                                        order_status = await state_manager.client.get_order(
                                            symbol=state_manager.symbol,
                                            orderId=sell_order['orderId'],
                                            recvWindow=60000  # Add recvWindow parameter
                                        )
                                        
                                        if order_status['status'] == 'FILLED':
                                            # Update state manager with the fill
                                            await state_manager.handle_order_update(order_status)
                                            exit_price = Decimal(str(order_status['price']))
                                            logger.info(f"SELL order filled at {exit_price}")
                                            
                                            # Log trade summary after both orders are filled
                                            if state_manager.trades:
                                                last_trade = state_manager.trades[-1]
                                                logger.info("\nTrade Summary:")
                                                logger.info(f"Entry Price: {last_trade.buy_order.price} USDC")
                                                logger.info(f"Exit Price: {last_trade.sell_order.price} USDC")
                                                logger.info(f"Quantity: {last_trade.buy_order.quantity} TRUMP")
                                                logger.info(f"Profit/Loss: {last_trade.profit_loss} USDC")
                                            break
                                        elif order_status['status'] in ['CANCELED', 'REJECTED', 'EXPIRED']:
                                            logger.error(f"SELL order {order_status['status']}")
                                            return
                                        
                                        await asyncio.sleep(1)
                                else:
                                    logger.error("Could not find SELL order in open orders")
                                    return
                            else:
                                # If AI not confident, use conservative 0.5% margin
                                sell_price = (entry_price * Decimal("1.005")).quantize(Decimal("0.01"))
                                logger.info(f"Using conservative 0.5% margin due to low AI confidence")
                                logger.info(f"Placing SELL order at {sell_price} USDC")
                                
                                # Get quantity from current position
                                sell_quantity = state_manager.current_position.quantity
                                logger.info(f"Selling position quantity: {sell_quantity} TRUMP")
                                
                                await state_manager.place_sell_order(
                                    price=sell_price,
                                    quantity=sell_quantity
                                )
                                
                                # Monitor SELL order status
                                logger.info("Waiting for SELL order to fill...")
                                sell_orders = await state_manager.client.get_open_orders(
                                    symbol=state_manager.symbol,
                                    recvWindow=60000  # Add recvWindow parameter
                                )
                                sell_order = next((order for order in sell_orders if order['side'] == 'SELL'), None)
                                
                                if sell_order:
                                    last_check_time = time.time()
                                    while True:
                                        current_time = time.time()
                                        
                                        # Refresh client connection every 5 minutes
                                        if current_time - last_check_time > 300:  # 5 minutes
                                            logger.info("Refreshing API connection...")
                                            await state_manager.client.close_connection()
                                            state_manager.client = await AsyncClient.create(
                                                api_key=os.getenv("BINANCE_TRADE_API_KEY"),
                                                api_secret=os.getenv("BINANCE_TRADE_API_SECRET")
                                            )
                                            last_check_time = current_time
                                        
                                        order_status = await state_manager.client.get_order(
                                            symbol=state_manager.symbol,
                                            orderId=sell_order['orderId'],
                                            recvWindow=60000  # Add recvWindow parameter
                                        )
                                        
                                        if order_status['status'] == 'FILLED':
                                            # Update state manager with the fill
                                            await state_manager.handle_order_update(order_status)
                                            exit_price = Decimal(str(order_status['price']))
                                            logger.info(f"SELL order filled at {exit_price}")
                                            
                                            # Log trade summary after both orders are filled
                                            if state_manager.trades:
                                                last_trade = state_manager.trades[-1]
                                                logger.info("\nTrade Summary:")
                                                logger.info(f"Entry Price: {last_trade.buy_order.price} USDC")
                                                logger.info(f"Exit Price: {last_trade.sell_order.price} USDC")
                                                logger.info(f"Quantity: {last_trade.buy_order.quantity} TRUMP")
                                                logger.info(f"Profit/Loss: {last_trade.profit_loss} USDC")
                                            break
                                        elif order_status['status'] in ['CANCELED', 'REJECTED', 'EXPIRED']:
                                            logger.error(f"SELL order {order_status['status']}")
                                            return
                                        
                                        await asyncio.sleep(1)
                                else:
                                    logger.error("Could not find SELL order in open orders")
                                    return
                            break
                        elif order_status['status'] in ['CANCELED', 'REJECTED', 'EXPIRED']:
                            logger.error(f"Order {order_status['status']}")
                            return
                        
                        await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error placing buy order: {e}")
                    return
            
            logger.info("Test cycle completed successfully!")
    
    except Exception as e:
        logger.error(f"Error during trading cycle: {e}")
        raise
    finally:
        logger.info("Shutting down gracefully...")
        if market_data:
            await market_data.stop()
        if client:
            try:
                await client.close_connection()
            except Exception as e:
                logger.error(f"Error closing client connection: {e}")

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