#!/usr/bin/env python3
import os
import argparse
from binance import Client
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    API_KEY = os.getenv('BINANCE_TRADE_API_KEY')
    API_SECRET = os.getenv('BINANCE_TRADE_API_SECRET')

    if not API_KEY or not API_SECRET:
        print("Error: Trading API credentials not found in .env file")
        print("Please add BINANCE_TRADE_API_KEY and BINANCE_TRADE_API_SECRET to your .env file")
        return

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Place a sell order on Binance')
    parser.add_argument('--symbol', type=str, default='TRUMPUSDC', help='Trading pair (default: TRUMPUSDC)')
    parser.add_argument('--quantity', type=float, required=True, help='Amount to sell')
    parser.add_argument('--price', type=float, required=True, help='Sell price in USDC')
    args = parser.parse_args()

    try:
        # Initialize Binance client
        client = Client(API_KEY, API_SECRET)
        
        # Format price and quantity according to market rules
        price = "{:.2f}".format(args.price)
        quantity = "{:.8f}".format(args.quantity)
        
        # Place the sell order
        order = client.create_order(
            symbol=args.symbol,
            side='SELL',
            type='LIMIT',
            timeInForce='GTC',
            quantity=quantity,
            price=price
        )
        
        # Print order details
        print("\nSell order placed successfully:")
        print(f"Symbol: {order['symbol']}")
        print(f"Order ID: {order['orderId']}")
        print(f"Type: {order['type']}")
        print(f"Side: {order['side']}")
        print(f"Price: {order['price']} USDC")
        print(f"Quantity: {order['origQty']} {args.symbol.replace('USDC', '')}")
        print(f"Status: {order['status']}")
        
    except Exception as e:
        print(f"Error placing sell order: {e}")

if __name__ == "__main__":
    main() 