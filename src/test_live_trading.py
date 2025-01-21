"""
Test script for live trading analysis with AI consultation.

This script:
1. Fetches real TRUMPUSDC data from Binance
2. Gets AI recommendation for BUY
3. Simulates/Monitors order
4. Gets AI recommendation for SELL
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from services.market_data import MarketDataService
from core.state_manager import StateManager, TradingState

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_market_data(market_data: MarketDataService) -> dict:
    """Fetch comprehensive market data."""
    try:
        # Get current market snapshot
        snapshot = await market_data.get_market_snapshot()
        
        # Get historical data (last 24h in 5m intervals)
        candles = await market_data.get_price_history(interval='5m', limit=288)
        
        # Calculate historical metrics
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        volumes = [c.volume for c in candles]
        
        return {
            'current': {
                'price': snapshot.get('price'),
                'ma_signal': snapshot.get('ma_signal'),
                'rsi': snapshot.get('rsi'),
                'macd': snapshot.get('macd_signal'),
                'order_book_imbalance': snapshot.get('order_book_imbalance')
            },
            'historical': {
                '24h_high': max(highs) if highs else 0,
                '24h_low': min(lows) if lows else 0,
                '24h_volume': sum(volumes) if volumes else 0,
                'avg_price': sum([c.close for c in candles]) / len(candles) if candles else 0,
                'volatility': (max(highs) - min(lows)) / min(lows) if lows and min(lows) > 0 else 0
            },
            'sentiment': {
                'buy_sell_ratio': snapshot.get('buy_sell_ratio', 1.0),
                'large_orders': snapshot.get('large_orders', 0)
            }
        }
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        raise

async def main():
    """Main execution flow."""
    market_data = None
    try:
        logger.info("Starting live trading analysis...")
        
        # Get API keys from environment
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            raise ValueError("Binance API keys not found in environment variables")
        
        # Initialize services
        market_data = MarketDataService(symbol="TRUMPUSDC")
        await market_data.start(api_key=api_key, api_secret=api_secret)
        
        # Wait a bit for WebSocket connections to establish
        await asyncio.sleep(2)
        
        state_manager = StateManager(symbol="TRUMPUSDC")
        
        # 1. Get current market data
        logger.info("Fetching market data...")
        data = await get_market_data(market_data)
        logger.info(f"Current price: {data['current']['price']} USDC")
        
        # 2. Get AI recommendation for BUY
        if state_manager.current_state == TradingState.READY_TO_BUY:
            logger.info("Getting BUY recommendation from AI...")
            buy_recommendation = await state_manager.consult_ai(data)
            
            if buy_recommendation:
                logger.info("\nBUY Recommendation:")
                logger.info(f"Price: {buy_recommendation.get('base_price')} USDC")
                logger.info(f"Range: {buy_recommendation.get('price_range')}")
                logger.info(f"Confidence: {buy_recommendation.get('confidence')}")
                logger.info(f"Reasoning: {buy_recommendation.get('reasoning')}")
                
                # Simulate buy order fill
                logger.info("\nSimulating BUY order fill...")
                await state_manager.transition(TradingState.BUYING)
                await state_manager.handle_order_update({
                    'orderId': '1',
                    'status': 'FILLED',
                    'price': str(buy_recommendation['base_price']),
                    'quantity': '0.25'  # 10 USDC worth at 40 USDC price
                })
                
                # 3. Get updated market data
                logger.info("\nFetching updated market data...")
                data = await get_market_data(market_data)
                
                # 4. Get AI recommendation for SELL
                if state_manager.current_state == TradingState.READY_TO_SELL:
                    logger.info("Getting SELL recommendation from AI...")
                    sell_recommendation = await state_manager.consult_ai(data)
                    
                    if sell_recommendation:
                        logger.info("\nSELL Recommendation:")
                        logger.info(f"Price: {sell_recommendation.get('base_price')} USDC")
                        logger.info(f"Range: {sell_recommendation.get('price_range')}")
                        logger.info(f"Confidence: {sell_recommendation.get('confidence')}")
                        logger.info(f"Reasoning: {sell_recommendation.get('reasoning')}")
        
        logger.info("\nAnalysis completed.")
        
    except Exception as e:
        logger.error(f"Error in live trading analysis: {e}")
        raise
    finally:
        if market_data:
            await market_data.stop()

if __name__ == "__main__":
    asyncio.run(main()) 