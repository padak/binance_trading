#!/usr/bin/env python3
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
from binance import ThreadedWebsocketManager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int
    vwap: Optional[float] = None
    
class OrderBook:
    def __init__(self, max_depth: int = 20):
        self.bids: Dict[float, float] = {}  # price -> quantity
        self.asks: Dict[float, float] = {}  # price -> quantity
        self.max_depth = max_depth
        
    def update(self, side: str, price: float, quantity: float):
        """Update order book with new data"""
        book = self.bids if side.upper() == 'BUY' else self.asks
        if quantity > 0:
            book[price] = quantity
        else:
            book.pop(price, None)
            
        # Maintain max depth
        if len(book) > self.max_depth:
            if side.upper() == 'BUY':
                min_price = min(self.bids.keys())
                self.bids.pop(min_price)
            else:
                max_price = max(self.asks.keys())
                self.asks.pop(max_price)
    
    @property
    def bid_volume(self) -> float:
        """Total volume on bid side"""
        return sum(self.bids.values())
    
    @property
    def ask_volume(self) -> float:
        """Total volume on ask side"""
        return sum(self.asks.values())
    
    def get_imbalance(self) -> float:
        """Calculate order book imbalance"""
        total_volume = self.bid_volume + self.ask_volume
        if total_volume == 0:
            return 0
        return (self.bid_volume - self.ask_volume) / total_volume

class MarketDataService:
    def __init__(self, symbol: str, candle_limit: int = 1000):
        """
        Initialize the market data service
        
        Args:
            symbol: Trading pair symbol (e.g., 'TRUMPUSDC')
            candle_limit: Maximum number of candles to store
        """
        self.symbol = symbol
        self.order_book = OrderBook()
        self.trades = deque(maxlen=1000)  # Last 1000 trades
        self.candles = deque(maxlen=candle_limit)  # Store candles
        self.current_candle: Optional[Candle] = None
        self.last_price: Optional[float] = None
        
        # Technical indicators
        self.ma5: Optional[float] = None
        self.ma20: Optional[float] = None
        self.vwap: Optional[float] = None
        
        # WebSocket manager
        self.twm: Optional[ThreadedWebsocketManager] = None
        
    def start(self, api_key: str, api_secret: str):
        """Start market data collection"""
        self.twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
        self.twm.start()
        
        # Start trade socket
        self.twm.start_symbol_ticker_socket(
            callback=self._handle_ticker,
            symbol=self.symbol
        )
        
        # Start order book socket
        self.twm.start_depth_socket(
            callback=self._handle_depth,
            symbol=self.symbol
        )
        
        logger.info(f"Started market data collection for {self.symbol}")
        
    def stop(self):
        """Stop market data collection"""
        if self.twm:
            self.twm.stop()
            self.twm = None
        logger.info("Stopped market data collection")
        
    def _handle_ticker(self, msg: dict):
        """Process ticker updates"""
        try:
            if msg.get('e') == 'error':
                logger.error(f"WebSocket error in ticker: {msg.get('m')}")
                return
                
            price = float(msg.get('c', 0))  # Close price
            if price > 0:
                self.last_price = price
                self._update_indicators()
                
        except Exception as e:
            logger.error(f"Error processing ticker: {e}")
            
    def _handle_depth(self, msg: dict):
        """Process order book updates"""
        try:
            if msg.get('e') == 'error':
                logger.error(f"WebSocket error in depth: {msg.get('m')}")
                return
                
            # Update bids
            for bid in msg.get('b', []):
                self.order_book.update('BUY', float(bid[0]), float(bid[1]))
                
            # Update asks
            for ask in msg.get('a', []):
                self.order_book.update('SELL', float(ask[0]), float(ask[1]))
                
        except Exception as e:
            logger.error(f"Error processing depth: {e}")
            
    def _update_indicators(self):
        """Update technical indicators"""
        if len(self.candles) >= 5:
            closes = [c.close for c in list(self.candles)[-5:]]
            self.ma5 = sum(closes) / 5
            
        if len(self.candles) >= 20:
            closes = [c.close for c in list(self.candles)[-20:]]
            self.ma20 = sum(closes) / 20
            
    def get_market_snapshot(self) -> dict:
        """
        Get current market state for AI analysis
        """
        return {
            "market_state": {
                "current_price": self.last_price,
                "order_book_imbalance": self.order_book.get_imbalance(),
                "volume_profile": {
                    "bid_volume": self.order_book.bid_volume,
                    "ask_volume": self.order_book.ask_volume
                },
                "technical_indicators": {
                    "ma5": self.ma5,
                    "ma20": self.ma20,
                    "vwap": self.vwap
                }
            },
            "metadata": {
                "symbol": self.symbol,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    def get_optimal_entry_levels(self, usdc_amount: float) -> List[float]:
        """
        Calculate optimal entry price levels for a given USDC amount
        
        Args:
            usdc_amount: Amount of USDC to trade
            
        Returns:
            List of suggested entry prices
        """
        if not self.last_price:
            return []
            
        # Get order book imbalance
        imbalance = self.order_book.get_imbalance()
        
        # Base price adjustment on imbalance
        base_adjustment = -0.002 if imbalance > 0 else -0.004  # More conservative when selling pressure
        
        # Calculate entry levels (multiple levels for better fill probability)
        levels = []
        for i in range(3):  # 3 price levels
            adjustment = base_adjustment * (1 + i * 0.5)  # Increase adjustment for each level
            price = self.last_price * (1 + adjustment)
            levels.append(round(price, 2))
            
        return sorted(levels)  # Sort from lowest to highest price 