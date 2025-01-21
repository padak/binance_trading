#!/usr/bin/env python3
import os
from datetime import datetime
from binance import ThreadedWebsocketManager, Client
from dotenv import load_dotenv
import logging
import time
import socket
import requests

"""
Binance WebSocket Monitor
Uses WSS (WebSocket Secure) by default:
- Connects to wss://stream.binance.com:9443
- All data is encrypted using TLS/SSL
- Automatic handling of secure connection by ThreadedWebsocketManager
- Automatic reconnection on connection drops (max 5 retries with exponential backoff)
- Heartbeat monitoring to detect connection health
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
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
            
        # Check for error messages
        if msg.get('e') == 'error':
            logger.error(f"WebSocket error message received: {msg.get('m')}")
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

def check_internet_connection():
    """Check if we can reach Binance"""
    try:
        # Try to resolve and connect to Binance
        socket.create_connection(("api.binance.com", 443), timeout=3)
        return True
    except OSError:
        return False

def main():
    twm = None
    reconnect_count = 0
    max_reconnects = 5
    
    try:
        while True:  # Outer loop for connection management
            try:
                # Check internet connectivity first
                if not check_internet_connection():
                    logger.warning("No internet connection. Waiting for network...")
                    time.sleep(5)  # Wait before checking again
                    continue

                # Initialize ThreadedWebsocketManager with read-only API keys
                if twm is None:
                    twm = ThreadedWebsocketManager(api_key=API_KEY, api_secret=API_SECRET)
                    logger.info("Starting WebSocket manager...")
                    twm.start()
                    print("Starting Binance order monitor (WSS)...")
                    print("Press Ctrl+C to exit")
                
                # Start user data socket (secure WebSocket connection)
                conn_key = twm.start_user_socket(callback=process_message)
                logger.info("WebSocket connection established")
                
                # Reset reconnect counter on successful connection
                reconnect_count = 0
                
                # Inner loop for connection monitoring
                while True:
                    if not twm.is_alive():
                        raise Exception("WebSocket connection lost")
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Connection error: {e}")
                
                if twm:
                    try:
                        twm.stop()
                        logger.info("Closed previous connection")
                    except:
                        pass
                    twm = None

                if reconnect_count < max_reconnects:
                    reconnect_count += 1
                    wait_time = 2 ** reconnect_count
                    logger.warning(f"Connection lost! Attempting reconnection {reconnect_count}/{max_reconnects} in {wait_time} seconds...")
                    time.sleep(wait_time)  # Exponential backoff
                else:
                    logger.error("Max reconnection attempts reached. Exiting...")
                    break
                    
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        
    finally:
        if twm:
            logger.info("Closing WebSocket connection...")
            try:
                twm.stop()
                logger.info("WebSocket connection closed")
            except:
                pass

if __name__ == "__main__":
    main() 