# Test Production Cycle Documentation

This document explains how `test_production_cycle.py` executes a single BUY/SELL cycle in production, with specific focus on how BUY/SELL prices are determined using AI consultation.

## Overview

The script executes one complete trading cycle for TRUMPUSDC with the following characteristics:
- Maximum position size: 10 USDC
- Minimum required AI confidence: 0.8 (80%)
- Minimum profit requirement: 1%
- Target profit: 5%

## Step-by-Step Process

### 1. Initialization Phase
```python
market_data = MarketDataService(symbol="TRUMPUSDC")
await market_data.start(api_key=api_key, api_secret=api_secret)
state_manager = StateManager(symbol="TRUMPUSDC")
await state_manager.start(api_key=api_key, api_secret=api_secret)
```
- Connects to Binance WebSocket for real-time TRUMPUSDC data
- Initializes state manager with Binance client for orders
- Shows initial USDC balance

### 2. BUY Decision Process
```python
while engine.active and state_manager.current_state == TradingState.READY_TO_BUY:
    await engine._trading_loop()
```
The trading loop collects and sends to AI:
- **Market Data**:
  - Current price and order book depth
  - Technical indicators (MA5, MA20, VWAP)
  - Order book imbalance
- **Historical Context**:
  - 24h price history (high, low, volume)
  - Average price and volatility
- **Sentiment Data**:
  - Twitter and news sentiment
  - Buy/sell ratio
  - Large order activity

#### AI Consultation for BUY
```json
{
    "action": "buy",
    "base_price": suggested entry price,
    "price_range": [min_price, max_price],
    "confidence": 0.0 to 1.0,
    "reasoning": "detailed explanation"
}
```
- Only executes BUY if AI confidence > 0.8
- Places limit order at AI's suggested base_price
- Monitors order until filled

### 3. SELL Decision Process
```python
if entry_price and current_price > entry_price * (1 + config['min_profit_pct']):
    logger.info(f"Current price {current_price} USDC is profitable")
    await engine._trading_loop()
```

The script only considers selling when:
1. Current price is above entry_price + 1% (minimum profit)
2. Then consults AI with fresh market data

#### AI Consultation for SELL
- Provides AI with:
  - Current market conditions
  - Entry price and current profit
  - Updated sentiment and correlation data
- AI returns:
  ```json
  {
      "action": "sell",
      "base_price": suggested exit price,
      "price_range": [min_price, max_price],
      "confidence": 0.0 to 1.0,
      "reasoning": "detailed explanation"
  }
  ```
- Places sell order only if:
  - AI confidence > 0.8
  - Suggested price ensures minimum 1% profit

### 4. Trade Completion
```python
final_balance = await state_manager.get_available_balance()
logger.info(f"Final USDC balance: {final_balance}")
```
- Shows trade summary with:
  - Buy price
  - Sell price
  - Profit/loss
  - Final balance

## Safety Features

1. **Balance Protection**:
   - Verifies USDC balance before BUY
   - Adjusts order size if needed
   - Maximum position size: 10 USDC

2. **Profit Protection**:
   - No stop-loss (never sells at a loss)
   - Minimum 1% profit requirement
   - Target 5% profit

3. **Risk Management**:
   - High confidence requirement (0.8)
   - Considers trading fees (0.1%)
   - Uses limit orders only

## Example AI Reasoning

For BUY decisions, AI considers:
```
1. Price trends and volatility patterns over the last 24 hours
2. Current order book depth and imbalance
3. Technical indicators (MA5, MA20, VWAP)
4. Market sentiment from recent large orders
5. Trading fees (0.1% per trade)
6. Historical support/resistance levels
```

For SELL decisions, AI additionally considers:
```
1. Current profit percentage
2. Price momentum
3. Updated market sentiment
4. Order book pressure
5. Recent trade volume
```

## Running the Script
```bash
python src/test_production_cycle.py
```

The script will run until one complete BUY/SELL cycle is finished or an error occurs, with detailed logging at each step. 