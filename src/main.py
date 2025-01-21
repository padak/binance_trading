"""
Main application script for the Binance Trading System.

This script:
1. Loads configuration from environment
2. Initializes all services
3. Starts the trading engine
4. Handles graceful shutdown
"""

import asyncio
import logging
import os
import signal
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime, timedelta

from dotenv import load_dotenv

from core.trading_engine import TradingEngine
from core.state_manager import StateManager
from services.market_data import MarketDataService
from services.sentiment_analyzer import SentimentAnalyzer
from services.correlation_analyzer import CorrelationAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingApplication:
    def __init__(self, symbol: str = "TRUMPUSDC", config: Optional[Dict] = None):
        """Initialize the trading application."""
        self.symbol = symbol
        self.config = config or {}
        self.services = {}
        self.engine = None
        self.is_running = False
        
        # Cache for API data
        self.sentiment_cache = {
            'data': None,
            'last_update': None
        }
        self.correlation_cache = {
            'data': None,
            'last_update': None
        }
        
        # Update intervals
        self.UPDATE_INTERVALS = {
            'market_data': 1,      # 1 minute
            'sentiment': 30,       # 30 minutes
            'correlation': 15,     # 15 minutes
            'summary': 5          # 5 minutes
        }
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        logger.info(f"Trading Application initialized for {symbol}")

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}. Starting graceful shutdown...")
        self.is_running = False

    async def _initialize_services(self):
        """Initialize all trading services."""
        try:
            # Load environment variables
            load_dotenv()
            
            # Initialize services
            self.services['market_data'] = MarketDataService(
                symbol=self.symbol,
                api_key=os.getenv('BINANCE_API_KEY'),
                api_secret=os.getenv('BINANCE_API_SECRET')
            )
            
            self.services['sentiment_analyzer'] = SentimentAnalyzer(
                twitter_token=os.getenv('TWITTER_BEARER_TOKEN'),
                news_api_key=os.getenv('NEWS_API_KEY')
            )
            
            self.services['correlation_analyzer'] = CorrelationAnalyzer(
                api_key=os.getenv('BINANCE_API_KEY'),
                api_secret=os.getenv('BINANCE_API_SECRET')
            )
            
            self.services['state_manager'] = StateManager(
                symbol=self.symbol,
                api_key=os.getenv('BINANCE_API_KEY'),
                api_secret=os.getenv('BINANCE_API_SECRET')
            )
            
            # Initialize trading engine
            self.engine = TradingEngine(
                symbol=self.symbol,
                market_data=self.services['market_data'],
                sentiment_analyzer=self.services['sentiment_analyzer'],
                correlation_analyzer=self.services['correlation_analyzer'],
                state_manager=self.services['state_manager'],
                config={
                    'min_confidence': 0.7,
                    'max_position_size': Decimal('10'),
                    'risk_per_trade': Decimal('0.1'),
                    'technical_weight': 0.4,
                    'sentiment_weight': 0.3,
                    'correlation_weight': 0.3,
                    'stop_loss_pct': Decimal('0.02'),
                    'take_profit_pct': Decimal('0.05')
                }
            )
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise

    async def _get_sentiment_data(self):
        """Get sentiment data with caching."""
        now = datetime.now()
        if (not self.sentiment_cache['data'] or 
            not self.sentiment_cache['last_update'] or 
            now - self.sentiment_cache['last_update'] > timedelta(minutes=self.UPDATE_INTERVALS['sentiment'])):
            
            logger.info("Fetching fresh sentiment data...")
            self.sentiment_cache['data'] = await self.services['sentiment_analyzer'].get_sentiment_data(self.symbol)
            self.sentiment_cache['last_update'] = now
            
        return self.sentiment_cache['data']

    async def _get_correlation_data(self):
        """Get correlation data with caching."""
        now = datetime.now()
        if (not self.correlation_cache['data'] or 
            not self.correlation_cache['last_update'] or 
            now - self.correlation_cache['last_update'] > timedelta(minutes=self.UPDATE_INTERVALS['correlation'])):
            
            logger.info("Fetching fresh correlation data...")
            self.correlation_cache['data'] = await self.services['correlation_analyzer'].get_correlation_data(self.symbol)
            self.correlation_cache['last_update'] = now
            
        return self.correlation_cache['data']

    async def start(self):
        """Start the trading application."""
        try:
            logger.info("Starting trading application...")
            
            # Initialize services
            await self._initialize_services()
            
            # Start trading engine
            self.is_running = True
            await self.engine.start()
            
            last_summary_time = datetime.now()
            
            # Keep the application running
            while self.is_running:
                try:
                    now = datetime.now()
                    
                    # Update market data every minute
                    await self.services['market_data'].update()
                    
                    # Update sentiment and correlation periodically
                    sentiment_data = await self._get_sentiment_data()
                    correlation_data = await self._get_correlation_data()
                    
                    # Log trading summary every 5 minutes
                    if now - last_summary_time > timedelta(minutes=self.UPDATE_INTERVALS['summary']):
                        summary = await self.engine.get_trading_summary()
                        logger.info(f"Trading Summary: {summary}")
                        logger.info(f"Current Sentiment: {sentiment_data}")
                        logger.info(f"Current Correlation: {correlation_data}")
                        last_summary_time = now
                    
                    await asyncio.sleep(60)  # Main loop interval
                    
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Critical error in trading application: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the trading application."""
        logger.info("Stopping trading application...")
        
        # Stop trading engine
        if self.engine:
            await self.engine.stop()
        
        # Clean up services
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'stop'):
                    await service.stop()
                logger.info(f"Stopped {service_name}")
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {e}")
        
        self.is_running = False
        logger.info("Trading application stopped")

async def main():
    """Main entry point."""
    app = TradingApplication()
    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Application error: {e}")
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main()) 