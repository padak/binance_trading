#!/usr/bin/env python3
"""
Production test script that runs one complete BUY/SELL cycle.
This script initializes all required services, executes a single trade cycle,
and provides detailed logging of the process.
"""

import asyncio
import logging
import os
from binance import AsyncClient
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv

from services.market_data import MarketDataService
from services.sentiment_analyzer import SentimentAnalyzer
from services.correlation_analyzer import CorrelationAnalyzer
from core.state_manager import StateManager

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_single_cycle():
    """Run a single BUY/SELL cycle with the trading bot"""
    market_data = None
    client = None
    try:
        # Load API keys
        api_key = os.getenv("BINANCE_TRADE_API_KEY")
        api_secret = os.getenv("BINANCE_TRADE_API_SECRET")
        
        if not api_key or not api_secret:
            raise ValueError("Binance Trading API credentials not found in environment variables")
            
        # Initialize Binance client
        client = await AsyncClient.create(api_key, api_secret)
        
        # Initialize services
        market_data = MarketDataService("TRUMPUSDC")
        sentiment = SentimentAnalyzer(client)
        correlation = CorrelationAnalyzer(client)
        state_manager = StateManager("TRUMPUSDC")
        
        # Start services
        await market_data.start(api_key=api_key, api_secret=api_secret)
        await state_manager.start(api_key=api_key, api_secret=api_secret)
        
        # Log initial balance
        initial_balance = await state_manager.get_available_balance()
        logger.info(f"Initial USDC Balance: {initial_balance}")
        
        # Wait for BUY order
        logger.info("Waiting for optimal BUY conditions...")
        while True:
            # Get market data
            market_snapshot = await market_data.get_market_snapshot()
            sentiment_data = await sentiment.get_sentiment_data("TRUMP")
            correlation_data = await correlation.get_correlation_data("TRUMPUSDC")
            
            # Consult AI for BUY decision
            buy_decision = await state_manager.consult_ai(
                "BUY",
                market_snapshot,
                sentiment_data,
                correlation_data
            )
            
            if buy_decision["confidence"] > 0.7:
                logger.info(f"AI recommends BUY at {buy_decision['price']} with confidence {buy_decision['confidence']}")
                await state_manager.place_buy_order(buy_decision["price"], Decimal("0.25"))
                break
                
            await asyncio.sleep(60)  # Check every minute
            
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
        
    except Exception as e:
        logger.error(f"Error during trading cycle: {e}")
        raise
        
    finally:
        # Cleanup
        await market_data.stop()
        await client.close_connection()
        
if __name__ == "__main__":
    asyncio.run(run_single_cycle()) 