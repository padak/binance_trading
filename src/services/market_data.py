#!/usr/bin/env python3
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
from binance import AsyncClient, BinanceSocketManager
import logging
import statistics
import asyncio
import os

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/market_data_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
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
        
        # Async client and socket manager
        self.client: Optional[AsyncClient] = None
        self.bsm: Optional[BinanceSocketManager] = None
        self.socket_tasks = []
        
        self.rsi_period = 14
        self.rsi_values = deque(maxlen=self.rsi_period)
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.macd_values = deque(maxlen=max(self.macd_slow, self.macd_signal))
        
        self.futures_data = {}
        
    async def start(self, api_key: str, api_secret: str):
        """Start market data collection"""
        try:
            logger.info(f"Initializing market data service for {self.symbol}")
            
            # Initialize async client
            self.client = await AsyncClient.create(api_key=api_key, api_secret=api_secret)
            self.bsm = BinanceSocketManager(self.client)
            
            # Get initial price before starting WebSocket
            try:
                ticker = await self.client.get_symbol_ticker(symbol=self.symbol)
                self.last_price = float(ticker['price'])
                logger.info(f"Initial price fetched: {self.last_price}")
                
                # Get initial 24h volume
                ticker_24h = await self.client.get_ticker(symbol=self.symbol)
                self.volume_24h = float(ticker_24h['volume'])
                logger.info(f"Initial 24h volume fetched: {self.volume_24h}")
                
                # Get initial order book snapshot
                logger.info("Fetching initial order book...")
                depth = await self.client.get_order_book(symbol=self.symbol)
                for bid in depth['bids']:
                    self.order_book.update('BUY', float(bid[0]), float(bid[1]))
                for ask in depth['asks']:
                    self.order_book.update('SELL', float(ask[0]), float(ask[1]))
                logger.info(f"Initial order book loaded with {len(depth['bids'])} bids and {len(depth['asks'])} asks")
                
                # Fetch historical candles
                logger.info("Fetching historical candles...")
                historical_candles = await self.get_price_history(interval='5m', limit=288)  # Last 24 hours
                self.candles.extend(historical_candles)
                logger.info(f"Loaded {len(historical_candles)} historical candles")
                
                # Update indicators with historical data
                self._update_indicators()
                logger.info("Technical indicators initialized with historical data")
                
            except Exception as e:
                logger.error(f"Error fetching initial data: {e}")
            
            # Start trade socket
            logger.info("Starting ticker WebSocket...")
            ts = self.bsm.symbol_ticker_socket(self.symbol)
            self.socket_tasks.append(asyncio.create_task(self._handle_socket(ts, self._handle_ticker)))
            
            # Start trade socket for volume tracking
            logger.info("Starting trades WebSocket...")
            trades_socket = self.bsm.trade_socket(self.symbol)
            self.socket_tasks.append(asyncio.create_task(self._handle_socket(trades_socket, self._handle_trades)))
            
            # Start order book socket
            logger.info("Starting depth WebSocket...")
            depth_socket = self.bsm.depth_socket(self.symbol)
            self.socket_tasks.append(asyncio.create_task(self._handle_socket(depth_socket, self._handle_depth)))
            
            # Start candle manager
            logger.info("Starting candle manager...")
            self.socket_tasks.append(asyncio.create_task(self._candle_manager()))
            
            logger.info("Market data service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error starting market data service: {e}")
            raise
        
    async def stop(self):
        """Stop market data collection"""
        # Cancel all socket tasks
        for task in self.socket_tasks:
            task.cancel()
        self.socket_tasks.clear()
        
        # Close the client
        if self.client:
            await self.client.close_connection()
            self.client = None
            
        logger.info("Stopped market data collection")
        
    async def _handle_socket(self, socket, handler):
        """Generic socket message handler"""
        async with socket as ts:
            logger.info(f"WebSocket connected: {handler.__name__}")
            while True:
                try:
                    msg = await ts.recv()
                    logger.debug(f"Received WebSocket message: {msg.get('e')} for {handler.__name__}")
                    await handler(msg)
                except Exception as e:
                    logger.error(f"Socket error in {handler.__name__}: {e}")
                    break
            logger.warning(f"WebSocket disconnected: {handler.__name__}")
        
    async def _handle_ticker(self, msg: dict):
        """Process ticker updates"""
        try:
            if msg.get('e') == 'error':
                logger.error(f"WebSocket error in ticker: {msg.get('m')}")
                return
                
            price = float(msg.get('c', 0))  # Close price
            if price > 0:
                logger.debug(f"Received price update: {price}")
                self.last_price = price
                self._update_indicators()
                logger.debug(f"Updated indicators - MA5: {self.ma5}, MA20: {self.ma20}")
            else:
                logger.warning(f"Received invalid price: {msg}")
                
        except Exception as e:
            logger.error(f"Error processing ticker: {e}, Message: {msg}")
            
    async def _handle_depth(self, msg: dict):
        """Process order book updates"""
        try:
            if msg.get('e') == 'error':
                logger.error(f"WebSocket error in depth: {msg.get('m')}")
                return
                
            # For depth update
            if msg.get('e') == 'depthUpdate':
                # Update bids
                for bid in msg.get('b', []):  # b = bids
                    price = float(bid[0])
                    quantity = float(bid[1])
                    self.order_book.update('BUY', price, quantity)
                    
                # Update asks
                for ask in msg.get('a', []):  # a = asks
                    price = float(ask[0])
                    quantity = float(ask[1])
                    self.order_book.update('SELL', price, quantity)
                    
                logger.debug(f"Order book updated - Bids: {len(self.order_book.bids)}, "
                           f"Asks: {len(self.order_book.asks)}, "
                           f"Imbalance: {self.order_book.get_imbalance():.2f}")
                
        except Exception as e:
            logger.error(f"Error processing depth: {e}, Message: {msg}")
            
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
        
    def analyze_price_swings(self, candles: List[Candle]) -> Dict:
        """Analyze price movement patterns in the last 60 candles"""
        if len(candles) < 2:
            return {"up": 0, "down": 0, "volatility": 0, "swing_points": []}
            
        swings = {"up": 0, "down": 0}
        price_changes = []
        swing_points = []
        prev_direction = None
        
        for i in range(1, len(candles)):
            curr_price = candles[i].close
            prev_price = candles[i-1].close
            price_change = ((curr_price - prev_price) / prev_price) * 100
            price_changes.append(abs(price_change))
            
            # Detect swing if price change is significant (>0.1%)
            if abs(price_change) > 0.1:
                current_direction = "up" if price_change > 0 else "down"
                
                # Count swing only when direction changes
                if prev_direction and current_direction != prev_direction:
                    swings[prev_direction] += 1
                    swing_points.append({
                        "time": candles[i].timestamp.strftime("%Y-%m-%d %H:%M"),
                        "price": curr_price,
                        "direction": current_direction,
                        "change": price_change
                    })
                
                prev_direction = current_direction
        
        # Calculate volatility (standard deviation of price changes)
        volatility = statistics.stdev(price_changes) if len(price_changes) > 1 else 0
        
        return {
            "up": swings["up"],
            "down": swings["down"],
            "volatility": volatility,
            "swing_points": swing_points[-10:]  # Last 10 swing points
        }

    def calculate_trend_strength(self, candles: List[Candle]) -> Dict:
        """Calculate trend strength using price action and volume"""
        if len(candles) < 20:
            return {"strength": 0, "direction": "neutral"}
            
        # Calculate price changes and corresponding volumes
        price_changes = []
        volumes = []
        
        for i in range(1, len(candles)):
            price_change = ((candles[i].close - candles[i-1].close) / candles[i-1].close) * 100
            price_changes.append(price_change)
            volumes.append(candles[i].volume)
        
        # Calculate trend direction
        trend_direction = "up" if sum(price_changes) > 0 else "down"
        
        # Calculate trend strength based on price momentum and volume
        avg_volume = statistics.mean(volumes)
        volume_factor = sum(v > avg_volume for v in volumes) / len(volumes)
        
        # Price momentum (recent changes weighted more heavily)
        weights = np.linspace(1, 2, len(price_changes))
        weighted_changes = np.multiply(price_changes, weights)
        price_momentum = np.mean(weighted_changes)
        
        # Combine factors for overall strength (0-100)
        strength = min(100, abs(price_momentum * 10) * volume_factor)
        
        return {
            "strength": strength,
            "direction": trend_direction,
            "momentum": price_momentum,
            "volume_factor": volume_factor
        }

    async def get_market_snapshot(self, max_retries: int = 3, retry_delay: float = 2.0) -> Dict:
        """
        Get current market snapshot with validation and retries
        
        Args:
            max_retries: Maximum number of retries to get valid data
            retry_delay: Delay between retries in seconds
            
        Returns:
            Dict containing market data
        """
        for attempt in range(max_retries):
            try:
                # If we don't have a price yet, try to fetch it
                if self.last_price is None:
                    logger.warning("No price available, fetching from API...")
                    ticker = await self.client.get_symbol_ticker(symbol=self.symbol)
                    self.last_price = float(ticker['price'])
                    
                # Get order book metrics
                liquidity = self.order_book.get_liquidity_metrics()
                
                # Get 24h volume if we don't have it
                if not hasattr(self, 'volume_24h') or self.volume_24h == 0:
                    ticker_24h = await self.client.get_ticker(symbol=self.symbol)
                    self.volume_24h = float(ticker_24h['volume'])
                
                # Convert candles to dict format for the snapshot
                price_history = []
                if self.candles:
                    for candle in list(self.candles)[-12:]:  # Last hour of data (12 x 5min candles)
                        price_history.append({
                            'timestamp': int(candle.timestamp.timestamp() * 1000),
                            'open': candle.open,
                            'high': candle.high,
                            'low': candle.low,
                            'close': candle.close,
                            'volume': candle.volume,
                            'trades': candle.trades,
                            'vwap': candle.vwap if candle.vwap else None
                        })
                    logger.debug(f"Added {len(price_history)} candles to market snapshot")
                    
                    # Calculate price movement metrics
                    if len(price_history) >= 2:
                        first_candle = price_history[0]
                        last_candle = price_history[-1]
                        total_change = ((last_candle['close'] - first_candle['close']) / first_candle['close']) * 100
                        high = max(c['high'] for c in price_history)
                        low = min(c['low'] for c in price_history)
                        logger.debug(f"Price movement: {total_change:.2f}% (High: {high:.2f}, Low: {low:.2f})")
                
                snapshot = {
                    'price': self.last_price,
                    'volume': self.volume_24h,  # Use 24h volume instead of trade collection
                    'best_bid': max(self.order_book.bids.keys()) if self.order_book.bids else None,
                    'best_ask': min(self.order_book.asks.keys()) if self.order_book.asks else None,
                    'bid_volume': self.order_book.bid_volume,
                    'ask_volume': self.order_book.ask_volume,
                    'ma5': self.ma5,
                    'ma20': self.ma20,
                    'vwap': self.vwap,
                    'spread': liquidity['spread'],
                    'bid_depth': liquidity['bid_depth'],
                    'ask_depth': liquidity['ask_depth'],
                    'cancel_rate': liquidity['cancel_rate'],
                    'price_history': price_history
                }
                
                # Validate core data
                if snapshot['price'] is None or snapshot['price'] == 0:
                    raise ValueError("Invalid price in snapshot")
                if snapshot['volume'] is None or snapshot['volume'] == 0:
                    raise ValueError("Invalid volume in snapshot")
                    
                logger.info(f"Market snapshot generated successfully on attempt {attempt + 1}")
                return snapshot
                
            except Exception as e:
                logger.warning(f"Failed to get market snapshot (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to get valid market snapshot after all retries")
                    raise

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

    def calculate_ma_signal(self) -> float:
        """Calculate moving average signal (-1 bearish, 0 neutral, 1 bullish)"""
        if not self.ma5 or not self.ma20:
            return 0
        return 1 if self.ma5 > self.ma20 else -1 if self.ma5 < self.ma20 else 0
    
    def calculate_macd_signal(self) -> float:
        """Calculate MACD signal (-1 bearish, 0 neutral, 1 bullish)"""
        macd_data = self.calculate_macd()
        if not macd_data:
            return 0
        return 1 if macd_data['histogram'] > 0 else -1 if macd_data['histogram'] < 0 else 0
    
    def calculate_order_book_imbalance(self) -> float:
        """Calculate order book imbalance"""
        return self.order_book.get_imbalance()
    
    def calculate_buy_sell_ratio(self) -> float:
        """Calculate buy/sell ratio from recent trades"""
        if not self.trades:
            return 1.0
        buys = sum(1 for trade in self.trades if trade.get('isBuyerMaker', False))
        sells = len(self.trades) - buys
        return buys / sells if sells > 0 else 1.0
    
    def detect_large_orders(self) -> int:
        """Count number of large orders (>1000 USDC) in recent trades"""
        if not self.trades:
            return 0
        return sum(1 for trade in self.trades 
                  if float(trade.get('quoteQty', 0)) > 1000) 

    async def get_price_history(self, interval: str = '5m', limit: int = 288) -> List[Candle]:
        """
        Get historical price data
        
        Args:
            interval: Kline interval (e.g., '5m', '15m', '1h')
            limit: Number of candles to fetch
            
        Returns:
            List of Candle objects
        """
        try:
            klines = await self.client.get_klines(
                symbol=self.symbol,
                interval=interval,
                limit=limit
            )
            
            return [
                Candle(
                    timestamp=datetime.fromtimestamp(kline[0] / 1000),
                    open=float(kline[1]),
                    high=float(kline[2]),
                    low=float(kline[3]),
                    close=float(kline[4]),
                    volume=float(kline[5]),
                    trades=int(kline[8]),
                    vwap=float(kline[7]) if len(kline) > 7 else None
                )
                for kline in klines
            ]
        except Exception as e:
            logger.error(f"Error fetching price history: {e}")
            return [] 

    async def _handle_trade(self, msg: dict):
        """Process trade updates"""
        try:
            if msg.get('e') == 'error':
                logger.error(f"WebSocket error in trades: {msg.get('m')}")
                return
                
            # Add trade to our collection
            if msg.get('q'):  # quantity
                self.trades.append(float(msg['q']))
                logger.debug(f"Recorded trade of {msg['q']} {self.symbol}")
                
        except Exception as e:
            logger.error(f"Error processing trade: {e}, Message: {msg}")

    async def _handle_trades(self, msg: dict):
        """Process trade updates"""
        try:
            if msg.get('e') == 'error':
                logger.error(f"WebSocket error in trades: {msg.get('m')}")
                return
                
            # Add trade to our collection
            self.trades.append(msg)
            
            # Update current candle if we have one
            if self.current_candle:
                price = float(msg.get('p', 0))  # Price
                volume = float(msg.get('q', 0))  # Quantity
                
                self.current_candle.high = max(self.current_candle.high, price)
                self.current_candle.low = min(self.current_candle.low, price)
                self.current_candle.close = price
                self.current_candle.volume += volume
                self.current_candle.trades += 1
                
                # Update VWAP
                if volume > 0:
                    if not self.current_candle.vwap:
                        self.current_candle.vwap = price
                    else:
                        self.current_candle.vwap = (
                            (self.current_candle.vwap * (self.current_candle.volume - volume) + 
                             price * volume) / self.current_candle.volume
                        )
            
            logger.debug(f"Processed trade: Price={msg.get('p')}, Quantity={msg.get('q')}")
            
        except Exception as e:
            logger.error(f"Error processing trade: {e}, Message: {msg}") 

    async def _candle_manager(self):
        """Manages candle creation and updates at regular intervals"""
        try:
            while True:
                now = datetime.now()
                # Round down to nearest 5 minute interval
                interval_minutes = 5
                minutes_to_next = interval_minutes - (now.minute % interval_minutes)
                seconds_to_next = minutes_to_next * 60 - now.second
                
                # Wait until next interval
                await asyncio.sleep(seconds_to_next)
                
                # Create new candle
                if self.last_price:
                    self.current_candle = Candle(
                        timestamp=datetime.now(),
                        open=self.last_price,
                        high=self.last_price,
                        low=self.last_price,
                        close=self.last_price,
                        volume=0.0,
                        trades=0
                    )
                    
                    # Wait for the interval duration
                    await asyncio.sleep(interval_minutes * 60)
                    
                    # Add completed candle to history
                    if self.current_candle:
                        self.candles.append(self.current_candle)
                        self._update_indicators()
                        logger.debug(f"New candle created: O={self.current_candle.open:.2f}, "
                                   f"H={self.current_candle.high:.2f}, L={self.current_candle.low:.2f}, "
                                   f"C={self.current_candle.close:.2f}, V={self.current_candle.volume:.2f}")
                        self.current_candle = None
                    
        except asyncio.CancelledError:
            logger.info("Candle manager stopped")
        except Exception as e:
            logger.error(f"Error in candle manager: {e}") 