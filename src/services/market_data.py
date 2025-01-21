#!/usr/bin/env python3
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
from binance import ThreadedWebsocketManager
import logging
import statistics

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
    def __init__(self, max_depth: int = 50):
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        self.max_depth = max_depth
        self.cancel_counts: Dict[float, int] = {}
        self.last_update = datetime.now()
        
    def update(self, side: str, price: float, quantity: float):
        """Update order book with new data"""
        book = self.bids if side.upper() == 'BUY' else self.asks
        old_quantity = book.get(price, 0)
        
        if quantity > 0:
            book[price] = quantity
        else:
            if price in book:
                self.cancel_counts[price] = self.cancel_counts.get(price, 0) + 1
            book.pop(price, None)
            
        # Calculate metrics
        self._update_metrics(side, price, old_quantity, quantity)
            
    def _update_metrics(self, side: str, price: float, old_qty: float, new_qty: float):
        """Update order book metrics"""
        now = datetime.now()
        time_diff = (now - self.last_update).total_seconds()
        
        # Track cancellation rate
        if time_diff >= 60:  # Reset every minute
            self.cancel_counts.clear()
            self.last_update = now
            
    def get_liquidity_metrics(self) -> Dict:
        """Calculate advanced liquidity metrics"""
        return {
            "spread": min(self.asks.keys()) - max(self.bids.keys()) if self.asks and self.bids else 0,
            "bid_depth": sum(qty * price for price, qty in self.bids.items()),
            "ask_depth": sum(qty * price for price, qty in self.asks.items()),
            "cancel_rate": len([c for c in self.cancel_counts.values() if c > 5]) / len(self.cancel_counts) if self.cancel_counts else 0
        }
        
    def detect_spoofing(self) -> bool:
        """Detect potential spoofing activity"""
        high_cancel_count = sum(1 for count in self.cancel_counts.values() if count > 5)
        total_orders = len(self.bids) + len(self.asks)
        return high_cancel_count / total_orders > 0.9 if total_orders > 0 else False
    
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
        
        self.rsi_period = 14
        self.rsi_values = deque(maxlen=self.rsi_period)
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.macd_values = deque(maxlen=max(self.macd_slow, self.macd_signal))
        
        self.futures_data = {}
        
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
            
    def calculate_rsi(self) -> float:
        """Calculate Relative Strength Index"""
        if len(self.rsi_values) < self.rsi_period:
            return 50.0  # Default neutral value
            
        gains = []
        losses = []
        for i in range(1, len(self.rsi_values)):
            change = self.rsi_values[i] - self.rsi_values[i-1]
            if change >= 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-change)
                
        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
        
    def calculate_macd(self) -> Dict[str, float]:
        """Calculate MACD indicators"""
        if len(self.macd_values) < self.macd_slow:
            return {"macd": 0, "signal": 0, "histogram": 0}
            
        # Calculate EMAs
        ema_fast = sum(list(self.macd_values)[-self.macd_fast:]) / self.macd_fast
        ema_slow = sum(list(self.macd_values)[-self.macd_slow:]) / self.macd_slow
        
        macd_line = ema_fast - ema_slow
        signal_line = sum(list(self.macd_values)[-self.macd_signal:]) / self.macd_signal
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": macd_line - signal_line
        }
        
    async def get_market_snapshot(self) -> Dict:
        """Get comprehensive market data snapshot including historical context"""
        current_data = {
            "market_state": {
                "current_price": self.last_price,
                "order_book_imbalance": self.order_book.get_imbalance(),
                "volume_profile": {
                    "bid_volume": sum(bid[1] for bid in self.order_book.bids[:10]),
                    "ask_volume": sum(ask[1] for ask in self.order_book.asks[:10])
                },
                "technical_indicators": {
                    "ma5": self.calculate_ma(5),
                    "ma20": self.calculate_ma(20),
                    "vwap": self.calculate_vwap(),
                    "rsi": self.calculate_rsi(),
                    "macd": self.calculate_macd()
                },
                "liquidity_metrics": self.order_book.get_liquidity_metrics(),
                "manipulation_indicators": {
                    "spoofing_detected": self.order_book.detect_spoofing(),
                    "abnormal_volume": self.detect_abnormal_volume(),
                    "price_volume_divergence": self.detect_price_volume_divergence()
                }
            },
            "futures_market": await self._get_futures_data(),
            "historical": await self._get_historical_data(),
            "sentiment": await self._get_market_sentiment(),
            "metadata": {
                "symbol": self.symbol,
                "timestamp": datetime.now().isoformat()
            }
        }
        return current_data

    async def _get_historical_data(self) -> Dict:
        """Collect historical price and trade data"""
        try:
            # Get 24h ticker data
            ticker = await self.client.get_ticker(symbol=self.symbol)
            
            # Get recent trades
            trades = await self.client.get_recent_trades(symbol=self.symbol, limit=100)
            
            # Calculate metrics
            prices = [float(trade['price']) for trade in trades]
            avg_price = sum(prices) / len(prices)
            volatility = statistics.stdev(prices) if len(prices) > 1 else 0
            
            return {
                "24h_high": float(ticker['highPrice']),
                "24h_low": float(ticker['lowPrice']),
                "24h_volume": float(ticker['volume']),
                "avg_price": avg_price,
                "volatility": volatility
            }
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return {}

    async def _get_market_sentiment(self) -> Dict:
        """Analyze market sentiment from recent trades and orders"""
        try:
            trades = await self.client.get_recent_trades(symbol=self.symbol, limit=500)
            
            # Calculate buy/sell ratio
            buys = sum(1 for trade in trades if trade['isBuyerMaker'])
            sells = len(trades) - buys
            buy_sell_ratio = buys / sells if sells > 0 else 1
            
            # Count large orders
            large_orders = sum(1 for trade in trades 
                             if float(trade['quoteQty']) > 1000)  # Orders > 1000 USDC
            
            return {
                "buy_sell_ratio": round(buy_sell_ratio, 2),
                "large_orders": large_orders
            }
        except Exception as e:
            logger.error(f"Error getting market sentiment: {e}")
            return {}
        
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

    def detect_abnormal_volume(self) -> bool:
        """Detect abnormal volume (>5x 30-day average)"""
        if len(self.candles) < 30:
            return False
        avg_volume = sum(c.volume for c in list(self.candles)[-30:]) / 30
        current_volume = self.candles[-1].volume if self.candles else 0
        return current_volume > (avg_volume * 5)
        
    def detect_price_volume_divergence(self) -> bool:
        """Detect price-volume divergence"""
        if len(self.candles) < 5:
            return False
            
        recent_candles = list(self.candles)[-5:]
        price_trend = recent_candles[-1].close - recent_candles[0].close
        volume_trend = recent_candles[-1].volume - recent_candles[0].volume
        
        # Divergence: price up, volume down or vice versa
        return (price_trend > 0 and volume_trend < 0) or (price_trend < 0 and volume_trend > 0) 

    async def _get_futures_data(self) -> Dict:
        """Collect futures market data"""
        try:
            # Get perpetual futures data
            perp_symbol = f"{self.symbol}_PERP"
            futures_ticker = await self.client.futures_ticker(symbol=perp_symbol)
            funding_rate = await self.client.futures_funding_rate(symbol=perp_symbol)
            open_interest = await self.client.futures_open_interest(symbol=perp_symbol)
            
            # Calculate futures premium
            spot_price = self.last_price or 0
            futures_price = float(futures_ticker['lastPrice'])
            premium = ((futures_price - spot_price) / spot_price) * 100 if spot_price > 0 else 0
            
            return {
                "futures_price": futures_price,
                "premium_percent": round(premium, 2),
                "funding_rate": float(funding_rate[0]['fundingRate']) if funding_rate else 0,
                "open_interest": float(open_interest['openInterest']),
                "open_interest_change_24h": self._calculate_oi_change(),
                "liquidations_24h": await self._get_liquidations()
            }
        except Exception as e:
            logger.error(f"Error getting futures data: {e}")
            return {}
            
    async def _get_liquidations(self) -> float:
        """Get 24h liquidation data"""
        try:
            liquidation_orders = await self.client.futures_liquidation_orders(symbol=self.symbol)
            total_liquidations = sum(float(order['executedQty']) * float(order['price']) 
                                   for order in liquidation_orders)
            return total_liquidations
        except Exception as e:
            logger.error(f"Error getting liquidations: {e}")
            return 0
            
    def _calculate_oi_change(self) -> float:
        """Calculate 24h change in Open Interest"""
        try:
            if 'previous_oi' in self.futures_data:
                current_oi = float(self.futures_data.get('open_interest', 0))
                previous_oi = float(self.futures_data.get('previous_oi', 0))
                return ((current_oi - previous_oi) / previous_oi) * 100 if previous_oi > 0 else 0
            return 0
        except Exception as e:
            logger.error(f"Error calculating OI change: {e}")
            return 0 