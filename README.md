# Binance Trading System

## Overview
A sophisticated cryptocurrency trading system built for Binance, featuring real-time market data analysis, sentiment analysis, and correlation tracking. The system combines technical analysis with AI-driven decision making for optimal trading strategies.

## Core Services

### [Trading Engine](docs/TRADING_ENGINE.md)
Core decision-making component that:
- Coordinates all services
- Generates trading signals
- Manages risk and position sizing
- Executes trades automatically

### [Market Data Service](docs/MARKET_DATA.md)
Real-time market data and analysis including:
- Price and volume tracking
- Order book analysis
- Technical indicators (MA, VWAP, RSI)
- Market manipulation detection

### [Sentiment Analysis](docs/SENTIMENT_ANALYSIS.md)
Multi-source sentiment analysis featuring:
- Social media sentiment (Twitter)
- News sentiment analysis
- Fear & Greed Index tracking
- AI-powered sentiment classification

### [Market Correlation Analysis](docs/CORRELATION_ANALYZER.md)
Market relationship tracking including:
- BTC price correlation
- Market dominance metrics
- Stablecoin flow analysis
- Overall market trends

## Getting Started

### Prerequisites
- Python 3.8+
- Binance API keys
- Twitter API keys
- News API key

### Environment Setup
1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Set up environment variables in `.env`:
```
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
TWITTER_BEARER_TOKEN=your_twitter_token
NEWS_API_KEY=your_news_api_key
```

### Running Tests
Verify service functionality:
```bash
python src/test_apis.py              # Test API integrations
python src/test_market_data.py       # Test market data service
python src/test_state_manager.py     # Test trading state management
python src/test_trading_engine.py    # Test trading engine
```

## Architecture
The system operates with several interconnected services coordinated by the Trading Engine:

1. Trading Engine (Core)
   - Signal generation and execution
   - Risk management
   - Position sizing
   - Service coordination

2. Support Services
   - Market Data Service: Real-time data collection and analysis
   - Sentiment Analyzer: Multi-source sentiment analysis
   - Correlation Analyzer: Market relationship tracking
   - State Manager: Trading state and position management

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details. 