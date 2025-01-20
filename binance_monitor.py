#!/usr/bin/env python3
import os
from datetime import datetime
from binance import ThreadedWebsocketManager, Client
from dotenv import load_dotenv
import logging
import time

"""
Binance WebSocket Monitor
Uses WSS (WebSocket Secure) by default:
- Connects to wss://stream.binance.com:9443
- All data is encrypted using TLS/SSL
- Automatic handling of secure connection by ThreadedWebsocketManager
"""

# Load environment variables
load_dotenv()
# Read-only API keys for monitoring
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# Trading API keys for placing orders
TRADE_API_KEY = os.getenv('BINANCE_TRADE_API_KEY')
TRADE_API_SECRET = os.getenv('BINANCE_TRADE_API_SECRET')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Initialize Binance clients
monitor_client = Client(API_KEY, API_SECRET)  # For monitoring
trade_client = Client(TRADE_API_KEY, TRADE_API_SECRET)  # For trading

def place_sell_order(symbol, quantity, buy_price):
    """Place a sell order at a higher price"""
    try:
        # Calculate sell price (e.g., 5% higher than buy price)
        sell_price = float(buy_price) * 1.05
        
        # Round the price and quantity according to market rules
        sell_price = "{:.2f}".format(sell_price)  # Adjust precision as needed
        
        # Place the sell order using trading API keys
        order = trade_client.create_order(
            symbol=symbol,
            side='SELL',
            type='LIMIT',
            timeInForce='GTC',
            quantity=quantity,
            price=sell_price
        )
        
        print(f"\nPlaced SELL order:")
        print(f"Symbol: {order['symbol']}")
        print(f"Quantity: {order['origQty']}")
        print(f"Price: {order['price']}")
        print(f"Order ID: {order['orderId']}")
        
    except Exception as e:
        logger.error(f"Error placing sell order: {e}")

def process_message(msg):
    """Process incoming WebSocket message (received over WSS)"""
    try:
        if not isinstance(msg, dict):
            return
            
        event_type = msg.get('e')
        if not event_type:
            return
            
        timestamp = msg.get('E', 0)
        time_str = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        if event_type == 'executionReport':  # Order update
            print("\n" + "="*50 + " ORDER UPDATE " + "="*50)
            print(f"""
Time: {time_str}
Symbol: {msg.get('s')}
Side: {msg.get('S')}
Type: {msg.get('o')}
Status: {msg.get('X')}
Price: {msg.get('p')}
Quantity: {msg.get('q')}
Order ID: {msg.get('i')}
{'Filled: ' + msg.get('l', '0') if msg.get('X') == 'FILLED' else ''}
""")
            print("="*120)
            
            # If a BUY order is filled, place a SELL order
            if msg.get('S') == 'BUY' and msg.get('X') == 'FILLED':
                place_sell_order(
                    symbol=msg.get('s'),
                    quantity=msg.get('q'),
                    buy_price=msg.get('p')
                )
        
        elif event_type == 'outboundAccountPosition':  # Account update
            print(f"\n{time_str} - Account Update:")
            for balance in msg.get('B', []):
                free = float(balance.get('f', 0))
                locked = float(balance.get('l', 0))
                if free > 0 or locked > 0:
                    print(f"Asset: {balance.get('a')}, Free: {free}, Locked: {locked}")
        
        elif event_type == 'balanceUpdate':  # Balance update
            print(f"\n{time_str} - Balance Update:")
            print(f"Asset: {msg.get('a')}, Delta: {msg.get('d')}")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        logger.debug(f"Message content: {msg}")

def main():
    twm = None
    try:
        # Initialize ThreadedWebsocketManager with read-only API keys
        # Uses WSS (WebSocket Secure) by default: wss://stream.binance.com:9443
        twm = ThreadedWebsocketManager(api_key=API_KEY, api_secret=API_SECRET)
        twm.start()
        
        print("Starting Binance order monitor (WSS)...")
        print("Press Ctrl+C to exit")
        
        # Start user data socket (secure WebSocket connection)
        conn_key = twm.start_user_socket(callback=process_message)
        
        # Keep the script running
        twm.join()
            
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Error in main loop: {e}")
        
    finally:
        if twm:
            twm.stop()

if __name__ == "__main__":
    main() 