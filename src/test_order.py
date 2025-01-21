#!/usr/bin/env python3
"""
Simple script to test placing orders on Binance.
Usage:
    Without parameters: Shows current price
    With parameters: Places a limit order
    
Example:
    Show price: python test_order.py
    Place order: python test_order.py TRUMPUSDC 43.50 0.25
"""

import asyncio
import os
import argparse
from decimal import Decimal
from binance import AsyncClient
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_current_price(client: AsyncClient, symbol: str) -> float:
    """Get current price for a symbol"""
    try:
        ticker = await client.get_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except Exception as e:
        logger.error(f"Error getting price: {e}")
        raise

async def place_test_order(symbol: str, side: str, price: str, quantity: str):
    """Place a test limit order"""
    try:
        # Load API credentials
        load_dotenv()
        api_key = os.getenv('BINANCE_TRADE_API_KEY')
        api_secret = os.getenv('BINANCE_TRADE_API_SECRET')
        
        if not api_key or not api_secret:
            raise ValueError("API credentials not found in .env file")
            
        # Initialize client
        client = await AsyncClient.create(api_key, api_secret)
        
        try:
            # Get current price first
            current_price = await get_current_price(client, symbol)
            logger.info(f"Current {symbol} price: {current_price:.2f} USDC")
            
            if not price or not quantity:
                return
            
            # Place order
            order = await client.create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                timeInForce='GTC',
                quantity=quantity,
                price=price
            )
            
            # Print order details
            logger.info("\nOrder placed successfully:")
            logger.info(f"Order ID: {order['orderId']}")
            logger.info(f"Symbol: {order['symbol']}")
            logger.info(f"Side: {order['side']}")
            logger.info(f"Type: {order['type']}")
            logger.info(f"Price: {order['price']}")
            logger.info(f"Quantity: {order['origQty']}")
            logger.info(f"Status: {order['status']}")
            
            # Calculate total value
            total_value = float(order['price']) * float(order['origQty'])
            logger.info(f"Total Value: {total_value:.2f} USDC")
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise
            
        finally:
            await client.close_connection()
            
    except Exception as e:
        logger.error(f"Error in place_test_order: {e}")
        raise

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test Binance order placement')
    parser.add_argument('symbol', nargs='?', default='TRUMPUSDC', help='Trading pair (default: TRUMPUSDC)')
    parser.add_argument('price', nargs='?', help='Limit price in USDC')
    parser.add_argument('quantity', nargs='?', help='Amount to buy')
    parser.add_argument('--side', choices=['BUY', 'SELL'], default='BUY', help='Order side (default: BUY)')
    args = parser.parse_args()
    
    try:
        await place_test_order(args.symbol, args.side, args.price, args.quantity)
    except Exception as e:
        logger.error(f"Main error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 