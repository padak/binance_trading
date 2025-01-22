# Test Scripts Documentation

## Overview
This document provides detailed information about all test scripts in the system, their purpose, and usage.

## Core Test Scripts

### test_production_cycle.py
- **Purpose**: Runs a complete BUY/SELL cycle in production environment
- **Features**:
  - Real-time market data monitoring
  - AI-driven trading decisions
  - Order placement and monitoring
  - WebSocket integration for order updates
  - Proper cleanup and resource management
- **Usage**:
```bash
python src/test_production_cycle.py [--dry-run]
```

### test_websocket.py
- **Purpose**: Tests WebSocket connections and real-time data streams
- **Features**:
  - Market data WebSocket testing
  - Order updates via WebSocket
  - Connection stability monitoring
- **Usage**:
```bash
python src/test_websocket.py
```

### test_state_manager.py
- **Purpose**: Tests state management functionality
- **Features**:
  - State transitions testing
  - Order tracking
  - Position management
  - Trade recording
- **Usage**:
```bash
python src/test_state_manager.py
```

### test_market_data.py
- **Purpose**: Tests market data service functionality
- **Features**:
  - Price data retrieval
  - Volume analysis
  - Technical indicators
  - Order book analysis
- **Usage**:
```bash
python src/test_market_data.py
```

## Utility Test Scripts

### check_trading_rules.py
- **Purpose**: Verifies compliance with Binance trading rules
- **Features**:
  - Minimum order size validation
  - Price precision checks
  - Quantity precision checks
  - Trading pair restrictions
- **Usage**:
```bash
python src/check_trading_rules.py
```

### test_order.py
- **Purpose**: Tests order placement and management
- **Features**:
  - Order creation
  - Order validation
  - Order status updates
  - Error handling
- **Usage**:
```bash
python src/test_order.py
```

### trade_profit.py
- **Purpose**: Analyzes and calculates trading profits
- **Features**:
  - P/L calculation
  - Trade history analysis
  - Performance metrics
  - Report generation
- **Usage**:
```bash
python src/trade_profit.py
```

### test_apis.py
- **Purpose**: Tests all external API integrations
- **Features**:
  - Binance API connectivity
  - Rate limit handling
  - Error response handling
  - Authentication testing
- **Usage**:
```bash
python src/test_apis.py
```

### test_live_trading.py
- **Purpose**: Tests live trading functionality
- **Features**:
  - Real market order execution
  - Risk management
  - Position tracking
  - Performance monitoring
- **Usage**:
```bash
python src/test_live_trading.py
```

## Running All Tests
To run all tests sequentially:
```bash
for test in src/test_*.py; do python "$test"; done
```

## Test Configuration
All tests use environment variables from `.env` file:
- `BINANCE_API_KEY`: Your Binance API key
- `BINANCE_API_SECRET`: Your Binance API secret
- `TEST_MODE`: Set to "true" for test environment 