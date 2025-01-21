"""
Test script for the Trading Engine.

This script tests:
1. Signal generation
2. Market condition aggregation
3. Trading strategy execution
4. Risk management
5. Integration with all services
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime

from core.trading_engine import TradingEngine, MarketCondition, TradingSignal
from core.state_manager import StateManager, TradingState
from services.market_data import MarketDataService
from services.sentiment_analyzer import SentimentAnalyzer
from services.correlation_analyzer import CorrelationAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockMarketData:
    async def get_market_snapshot(self):
        return type('MarketSnapshot', (), {
            'price': Decimal('40.0'),
            'ma_signal': 0.5,
            'rsi': 55.0,
            'macd_signal': 0.3,
            'order_book_imbalance': 0.2
        })

class MockSentimentAnalyzer:
    async def get_aggregated_sentiment(self, symbol):
        return type('Sentiment', (), {
            'overall_sentiment': 0.6,
            'fear_greed_index': 65
        })

class MockCorrelationAnalyzer:
    async def get_correlation_data(self, symbol):
        return type('Correlation', (), {
            'coefficient': 0.8
        })

class MockStateManager:
    def __init__(self):
        self.current_state = TradingState.READY_TO_BUY
        self.current_position = None
        self.orders = []

    def get_available_balance(self):
        return Decimal('10000.0')

    async def place_buy_order(self, price, quantity, stop_loss, take_profit):
        self.orders.append({
            'type': 'BUY',
            'price': price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        })
        logger.info(f"Mock buy order placed: {price=}, {quantity=}")
        return True

    async def place_sell_order(self, price, quantity):
        self.orders.append({
            'type': 'SELL',
            'price': price,
            'quantity': quantity
        })
        logger.info(f"Mock sell order placed: {price=}, {quantity=}")
        return True

async def test_trading_engine():
    """Test the trading engine's core functionality."""
    try:
        # Initialize mock services
        market_data = MockMarketData()
        sentiment_analyzer = MockSentimentAnalyzer()
        correlation_analyzer = MockCorrelationAnalyzer()
        state_manager = MockStateManager()

        # Initialize trading engine
        engine = TradingEngine(
            symbol="TRUMPUSDC",
            market_data=market_data,
            sentiment_analyzer=sentiment_analyzer,
            correlation_analyzer=correlation_analyzer,
            state_manager=state_manager,
            config={
                'min_confidence': 0.6,
                'max_position_size': Decimal('1000'),
                'risk_per_trade': Decimal('0.02'),
                'technical_weight': 0.4,
                'sentiment_weight': 0.3,
                'correlation_weight': 0.3,
                'stop_loss_pct': Decimal('0.02'),
                'take_profit_pct': Decimal('0.05')
            }
        )

        # Test 1: Market Condition Aggregation
        logger.info("Testing market condition aggregation...")
        market_condition = await engine._get_market_condition()
        assert isinstance(market_condition, MarketCondition)
        assert market_condition.price == Decimal('40.0')
        logger.info("✓ Market condition aggregation test passed")

        # Test 2: Signal Generation
        logger.info("Testing signal generation...")
        signal = await engine._generate_trading_signal(market_condition)
        assert isinstance(signal, TradingSignal)
        assert signal.action in ['BUY', 'SELL']
        assert 0 <= signal.confidence <= 1
        logger.info("✓ Signal generation test passed")

        # Test 3: Position Sizing
        logger.info("Testing position sizing...")
        position_size = engine._calculate_position_size(Decimal('40.0'))
        assert position_size <= Decimal('1000') / Decimal('40.0')  # Max position check
        logger.info("✓ Position sizing test passed")

        # Test 4: Signal Execution
        logger.info("Testing signal execution...")
        await engine._execute_signal(signal)
        assert len(state_manager.orders) > 0
        last_order = state_manager.orders[-1]
        assert last_order['type'] in ['BUY', 'SELL']
        logger.info("✓ Signal execution test passed")

        # Test 5: Trading Summary
        logger.info("Testing trading summary...")
        summary = await engine.get_trading_summary()
        assert summary['symbol'] == "TRUMPUSDC"
        assert summary['state'] == state_manager.current_state.name
        logger.info("✓ Trading summary test passed")

        # Test 6: Strategy Components
        logger.info("Testing strategy components...")
        technical = engine._analyze_technical_signals(market_condition)
        sentiment = engine._analyze_sentiment_signals(market_condition)
        correlation = engine._analyze_correlation_signals(market_condition)
        
        assert isinstance(technical, tuple) and len(technical) == 2
        assert isinstance(sentiment, tuple) and len(sentiment) == 2
        assert isinstance(correlation, tuple) and len(correlation) == 2
        logger.info("✓ Strategy components test passed")

        logger.info("All tests passed successfully!")

    except AssertionError as e:
        logger.error(f"Test failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during testing: {e}")
        raise

async def main():
    """Run all tests."""
    try:
        await test_trading_engine()
    except Exception as e:
        logger.error(f"Testing failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 