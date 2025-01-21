#!/usr/bin/env python3
"""
Test script to monitor Binance WebSocket streams.
Uses the same WebSocket handling approach as our MarketDataService.
"""

import asyncio
import os
from binance import AsyncClient, BinanceSocketManager
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebSocketTester:
    def __init__(self, symbol: str = "TRUMPUSDC"):
        self.symbol = symbol
        self.client = None
        self.bsm = None
        self.socket_tasks = []
        
    async def start(self, api_key: str, api_secret: str):
        """Start WebSocket connections"""
        try:
            logger.info(f"Initializing WebSocket tester for {self.symbol}")
            
            # Initialize async client
            self.client = await AsyncClient.create(api_key=api_key, api_secret=api_secret)
            self.bsm = BinanceSocketManager(self.client)
            
            # Start trade socket
            logger.info("Starting trades WebSocket...")
            trades_socket = self.bsm.trade_socket(self.symbol)
            self.socket_tasks.append(asyncio.create_task(self._handle_socket(trades_socket, self._handle_trades)))
            
            # Start order book socket
            logger.info("Starting depth WebSocket...")
            depth_socket = self.bsm.depth_socket(self.symbol)
            self.socket_tasks.append(asyncio.create_task(self._handle_socket(depth_socket, self._handle_depth)))
            
            # Start user data socket
            logger.info("Starting user data WebSocket...")
            user_socket = self.bsm.user_socket()
            self.socket_tasks.append(asyncio.create_task(self._handle_socket(user_socket, self._handle_user_data)))
            
            logger.info("All WebSocket streams started")
            
        except Exception as e:
            logger.error(f"Error starting WebSocket tester: {e}")
            raise
            
    async def stop(self):
        """Stop WebSocket connections"""
        for task in self.socket_tasks:
            task.cancel()
        self.socket_tasks.clear()
        
        if self.client:
            await self.client.close_connection()
            self.client = None
            
        logger.info("WebSocket tester stopped")
        
    async def _handle_socket(self, socket, handler):
        """Generic socket message handler"""
        async with socket as ts:
            logger.info(f"WebSocket connected: {handler.__name__}")
            while True:
                try:
                    msg = await ts.recv()
                    await handler(msg)
                except Exception as e:
                    logger.error(f"Socket error in {handler.__name__}: {e}")
                    break
            logger.warning(f"WebSocket disconnected: {handler.__name__}")
            
    async def _handle_trades(self, msg: dict):
        """Process trade updates - Price and size only"""
        try:
            if msg.get('e') == 'trade':
                # Commented out to reduce noise
                # print(f"\n[MARKET TRADE] {msg.get('p')} USDC x {msg.get('q')} TRUMP")
                pass
                
        except Exception as e:
            logger.error(f"Error processing trade: {e}")
            
    async def _handle_depth(self, msg: dict):
        """Process order book updates - Top levels and spread only"""
        try:
            if msg.get('e') == 'depthUpdate':
                # Commented out to reduce noise
                # Get best bid and ask
                # bids = msg.get('b', [])
                # asks = msg.get('a', [])
                
                # if bids and asks:
                #     best_bid = float(bids[0][0])
                #     best_ask = float(asks[0][0])
                #     spread = best_ask - best_bid
                    
                #     print(f"\n[ORDER BOOK]")
                #     print(f"  SPREAD: {spread:.8f} USDC")
                #     print(f"  BEST BID: {best_bid} x {bids[0][1]} TRUMP")
                #     print(f"  BEST ASK: {best_ask} x {asks[0][1]} TRUMP")
                pass
                        
        except Exception as e:
            logger.error(f"Error processing depth: {e}")
            
    async def _handle_user_data(self, msg: dict):
        """Process user data updates - Order status updates only"""
        try:
            if msg.get('e') == 'executionReport':
                order_id = msg.get('i')  # Order ID
                status = msg.get('X')    # Order status
                side = msg.get('S')      # BUY or SELL
                symbol = msg.get('s')    # Trading pair
                
                if status == 'FILLED':
                    logger.info(f"ORDER FILLED - ID: {order_id}")
                    logger.info(f"  {side}: {msg.get('z')} {symbol} @ {msg.get('p')} USDC")
                    logger.info(f"  Total value: {float(msg.get('z')) * float(msg.get('p')):.2f} USDC")
                elif status == 'NEW':
                    logger.info(f"NEW ORDER - ID: {order_id}")
                    logger.info(f"  {side}: {msg.get('q')} {symbol} @ {msg.get('p')} USDC")
                else:
                    logger.info(f"ORDER UPDATE - ID: {order_id}")
                    logger.info(f"  Status: {status}")
                    logger.info(f"  {side}: {msg.get('q')} {symbol}")
                
        except Exception as e:
            logger.error(f"Error processing user data: {e}")

async def main():
    """Main function"""
    # Load API credentials
    api_key = os.getenv('BINANCE_TRADE_API_KEY')
    api_secret = os.getenv('BINANCE_TRADE_API_SECRET')
    
    if not api_key or not api_secret:
        raise ValueError("Binance API credentials not found in environment")
    
    # Initialize WebSocket tester
    ws_tester = WebSocketTester("TRUMPUSDC")
    
    try:
        # Start WebSocket streams
        await ws_tester.start(api_key, api_secret)
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping by user request...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        await ws_tester.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass 