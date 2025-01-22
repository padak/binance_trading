# Binance Trading System

## Overview
A sophisticated cryptocurrency trading system built for Binance, featuring real-time market data analysis and AI-driven trading decisions. The system focuses on the TRUMP/USDC trading pair with automated trade execution and risk management.

## Core Components

### [Trading Engine](docs/TRADING_ENGINE.md)
Core trading component that:
- Places and monitors orders
- Manages positions
- Handles API interactions
- Implements safety checks and error handling

### [Market Data Service](docs/MARKET_DATA_SERVICE.md)
Real-time market data collection and analysis:
- WebSocket price streams
- Order book monitoring
- Volume tracking
- Technical indicators

### [State Manager](docs/STATE_MANAGER.md)
Trading state and position management:
- Order state tracking
- Position management
- Trade recording
- Balance monitoring

### [Test Scripts](docs/TEST_SCRIPTS.md)
Comprehensive test suite including:
- Production cycle testing
- WebSocket connectivity
- Order management
- Trading rules verification
- Profit calculation

## Getting Started

### Prerequisites
- Python 3.8+
- Binance API keys
- OpenRouter API key (for AI recommendations)

### Environment Setup
1. Clone the repository
2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env`:
```
BINANCE_TRADE_API_KEY=your_binance_api_key
BINANCE_TRADE_API_SECRET=your_binance_api_secret
OPENROUTER_API_KEY=your_openrouter_api_key
```

### Running Tests
Start with basic functionality tests:
```bash
python src/test_apis.py              # Test API connections
python src/test_market_data.py       # Test market data service
python src/test_websocket.py         # Test WebSocket connections
python src/check_trading_rules.py    # Verify trading rules
```

Then proceed to trading tests:
```bash
python src/test_production_cycle.py --dry-run  # Test full trading cycle without real orders
```

## Architecture
The system operates with several interconnected components:

1. Core Services
   - Trading Engine: Order execution and management
   - Market Data Service: Real-time data collection
   - State Manager: Trading state and position tracking

2. Testing & Utilities
   - Production cycle testing
   - WebSocket connectivity
   - Order management
   - Profit calculation

## Documentation
- [Trading Engine](docs/TRADING_ENGINE.md)
- [Market Data Service](docs/MARKET_DATA_SERVICE.md)
- [State Manager](docs/STATE_MANAGER.md)
- [Test Scripts](docs/TEST_SCRIPTS.md)

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details. 