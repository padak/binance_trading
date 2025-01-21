"""
Trading Engine - Core decision making component that coordinates all services.

This module implements the main trading engine that:
1. Aggregates data from all services (Market Data, Sentiment, Correlation)
2. Applies trading strategies
3. Makes final trading decisions
4. Manages order execution through the State Manager
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from services.market_data import MarketDataService
from services.correlation_analyzer import CorrelationAnalyzer
from services.sentiment_analyzer import SentimentAnalyzer
from core.state_manager import StateManager, TradingState, Position

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradingSignal:
    """Represents a trading signal with confidence and supporting data."""
    action: str  # 'BUY' or 'SELL'
    confidence: float  # 0.0 to 1.0
    price: Decimal
    quantity: Decimal
    timestamp: datetime
    reasons: Dict[str, float]  # Source -> Confidence mapping

@dataclass
class MarketCondition:
    """Aggregated market conditions from all services."""
    price: Decimal
    btc_correlation: float
    market_sentiment: float
    technical_signals: Dict[str, float]
    order_book_imbalance: float
    fear_greed_index: int

class TradingEngine:
    def __init__(
        self,
        symbol: str,
        market_data: MarketDataService,
        sentiment_analyzer: SentimentAnalyzer,
        correlation_analyzer: CorrelationAnalyzer,
        state_manager: StateManager,
        config: Optional[Dict] = None
    ):
        """Initialize the trading engine with required services."""
        self.symbol = symbol
        self.market_data = market_data
        self.sentiment_analyzer = sentiment_analyzer
        self.correlation_analyzer = correlation_analyzer
        self.state_manager = state_manager
        
        # Default configuration
        self.config = {
            'min_confidence': 0.7,           # Minimum confidence for trade execution
            'max_position_size': Decimal('10'),  # Maximum position size in USDC (reduced from 1000)
            'risk_per_trade': Decimal('0.1'),   # 10% risk per trade (increased from 2% due to small account)
            'technical_weight': 0.4,         # Weight for technical signals
            'sentiment_weight': 0.3,         # Weight for sentiment signals
            'correlation_weight': 0.3,       # Weight for correlation signals
            'stop_loss_pct': Decimal('0.02'),   # 2% stop loss
            'take_profit_pct': Decimal('0.05')  # 5% take profit
        }
        if config:
            self.config.update(config)
        
        self.active = False
        logger.info(f"Trading Engine initialized for {symbol}")

    async def start(self):
        """Start the trading engine."""
        self.active = True
        logger.info("Trading Engine started")
        
        while self.active:
            try:
                await self._trading_loop()
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        """Stop the trading engine."""
        self.active = False
        logger.info("Trading Engine stopped")

    async def _trading_loop(self):
        """Main trading loop that analyzes market and generates signals."""
        # Get current market conditions
        market_condition = await self._get_market_condition()
        
        # Generate trading signal
        signal = await self._generate_trading_signal(market_condition)
        
        if signal and signal.confidence >= self.config['min_confidence']:
            await self._execute_signal(signal)
        
        await asyncio.sleep(1)  # Avoid excessive CPU usage

    async def _get_market_condition(self) -> MarketCondition:
        """Aggregate current market conditions from all services."""
        # Get market data
        market_snapshot = await self.market_data.get_market_snapshot()
        
        # Get correlation data
        correlation = await self.correlation_analyzer.get_correlation_data(self.symbol)
        
        # Get sentiment data
        sentiment = await self.sentiment_analyzer.get_aggregated_sentiment(self.symbol)
        
        return MarketCondition(
            price=market_snapshot.price,
            btc_correlation=correlation.coefficient,
            market_sentiment=sentiment.overall_sentiment,
            technical_signals={
                'ma_signal': market_snapshot.ma_signal,
                'rsi': market_snapshot.rsi,
                'macd': market_snapshot.macd_signal
            },
            order_book_imbalance=market_snapshot.order_book_imbalance,
            fear_greed_index=sentiment.fear_greed_index
        )

    async def _generate_trading_signal(self, condition: MarketCondition) -> Optional[TradingSignal]:
        """Generate trading signal based on market conditions."""
        # Skip if we're already in a trade
        if self.state_manager.current_state not in [TradingState.READY_TO_BUY, TradingState.READY_TO_SELL]:
            return None

        # Calculate component signals
        technical_signal = self._analyze_technical_signals(condition)
        sentiment_signal = self._analyze_sentiment_signals(condition)
        correlation_signal = self._analyze_correlation_signals(condition)

        # Weight and combine signals
        total_confidence = (
            technical_signal[1] * self.config['technical_weight'] +
            sentiment_signal[1] * self.config['sentiment_weight'] +
            correlation_signal[1] * self.config['correlation_weight']
        )

        # Determine action based on current state
        action = 'BUY' if self.state_manager.current_state == TradingState.READY_TO_BUY else 'SELL'
        
        if total_confidence >= self.config['min_confidence']:
            # Calculate position size based on risk
            quantity = self._calculate_position_size(condition.price)
            
            return TradingSignal(
                action=action,
                confidence=total_confidence,
                price=condition.price,
                quantity=quantity,
                timestamp=datetime.now(),
                reasons={
                    'technical': technical_signal[1],
                    'sentiment': sentiment_signal[1],
                    'correlation': correlation_signal[1]
                }
            )
        
        return None

    def _analyze_technical_signals(self, condition: MarketCondition) -> Tuple[str, float]:
        """Analyze technical indicators."""
        signals = condition.technical_signals
        
        # Simple moving average signal
        ma_bullish = signals['ma_signal'] > 0
        
        # RSI signals
        rsi = signals['rsi']
        rsi_bullish = 30 <= rsi <= 70
        
        # MACD signal
        macd_bullish = signals['macd'] > 0
        
        # Order book analysis
        ob_bullish = condition.order_book_imbalance > 0
        
        # Count bullish signals
        bullish_count = sum([ma_bullish, rsi_bullish, macd_bullish, ob_bullish])
        confidence = bullish_count / 4.0
        
        return ('BUY' if confidence > 0.5 else 'SELL', confidence)

    def _analyze_sentiment_signals(self, condition: MarketCondition) -> Tuple[str, float]:
        """Analyze sentiment indicators."""
        # Combine market sentiment and fear/greed index
        sentiment_score = condition.market_sentiment  # -1.0 to 1.0
        fear_greed_normalized = condition.fear_greed_index / 100.0  # 0.0 to 1.0
        
        # Weight and combine
        combined_sentiment = (sentiment_score + fear_greed_normalized) / 2.0
        confidence = abs(combined_sentiment)
        
        return ('BUY' if combined_sentiment > 0 else 'SELL', confidence)

    def _analyze_correlation_signals(self, condition: MarketCondition) -> Tuple[str, float]:
        """Analyze correlation-based signals."""
        # High positive correlation with BTC might indicate good time to trade
        correlation = abs(condition.btc_correlation)
        
        # Higher correlation gives higher confidence
        confidence = min(correlation, 1.0)
        
        return ('BUY', confidence)  # Direction based on other signals

    def _calculate_position_size(self, current_price: Decimal) -> Decimal:
        """Calculate position size based on risk management rules."""
        # Get account balance from state manager
        balance = self.state_manager.get_available_balance()
        
        # Calculate maximum position size based on risk percentage
        risk_amount = balance * self.config['risk_per_trade']
        
        # Calculate quantity based on current price
        quantity = risk_amount / current_price
        
        # Ensure we don't exceed maximum position size
        max_quantity = self.config['max_position_size'] / current_price
        quantity = min(quantity, max_quantity)
        
        return quantity

    async def _execute_signal(self, signal: TradingSignal):
        """Execute the trading signal through the state manager."""
        try:
            if signal.action == 'BUY':
                # Verify available balance first
                available_balance = await self.state_manager.get_available_balance()
                required_amount = signal.price * signal.quantity
                
                if available_balance < required_amount:
                    logger.error(f"Insufficient balance for BUY order. Required: {required_amount} USDC, Available: {available_balance} USDC")
                    
                    # Try with 50% of available balance if it's enough for minimum order
                    adjusted_quantity = (available_balance * Decimal('0.5')) / signal.price
                    min_order_value = Decimal('5')  # Minimum order value in USDC
                    
                    if available_balance * Decimal('0.5') >= min_order_value:
                        logger.info(f"Retrying with adjusted quantity: {adjusted_quantity}")
                        signal.quantity = adjusted_quantity
                    else:
                        logger.error(f"Available balance too low for minimum order value of {min_order_value} USDC")
                        return
                
                # Calculate stop loss and take profit levels
                stop_loss = signal.price * (1 - self.config['stop_loss_pct'])
                take_profit = signal.price * (1 + self.config['take_profit_pct'])
                
                try:
                    await self.state_manager.place_buy_order(
                        price=signal.price,
                        quantity=signal.quantity,
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )
                except Exception as e:
                    if "insufficient balance" in str(e).lower():
                        logger.error(f"Order failed due to insufficient balance: {e}")
                        # Update account balance and wait for next cycle
                        await self.state_manager.update_balance()
                    else:
                        logger.error(f"Order failed: {e}")
                        raise
                
            else:  # SELL
                await self.state_manager.place_sell_order(
                    price=signal.price,
                    quantity=signal.quantity
                )
            
            logger.info(f"Executed {signal.action} signal: {signal}")
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")

    async def get_trading_summary(self) -> Dict:
        """Get summary of current trading state and recent signals."""
        return {
            'symbol': self.symbol,
            'state': self.state_manager.current_state.name,
            'current_position': self.state_manager.current_position,
            'last_signal': self._last_signal if hasattr(self, '_last_signal') else None,
            'active': self.active
        } 