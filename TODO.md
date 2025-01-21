# TODO List

## Completed ✅
- Basic order viewing functionality
- Price history with intervals
- Support for different trading pairs
- Table output format
- JSON data export
- AI trading recommendations
- Multiple AI models support
- WebSocket monitoring with auto-sell
- Separate API keys for reading and trading
- Order Monitoring Implementation ✅
  * User data stream connection
  * Order execution status tracking
  * Fill notifications
  * Automatic follow-up orders

## Pending Tasks 📋

1. Fix WebSocket Connection Stability
   - Resolve timeout errors (1011)
   - Fix policy violations (1008)
   - Handle DNS failures
   - Prevent silent drops

2. Optimize AI Trading
   - Add cooldown periods
   - Track confidence patterns
   - Cache recommendations
   - Add price thresholds

3. Add Price Monitoring
   - SELL order monitoring
   - Averaging down
   - Entry tracking
   - Position limits

4. Build Infrastructure
   - Backtesting
   - Performance analysis
   - Portfolio tracking
   - Risk management
   - Testing
   - CI/CD
   - Docker

5. Add Advanced Features
   - Notifications
   - Custom strategies
   - Multi-exchange
   - Advanced orders
   - Analytics

6. Enhance Market Data
   - Complete snapshots
   - Technical indicators
   - Price history
   - Order book metrics

## In Progress 🚧
- Backtesting functionality
- Historical performance analysis
- Portfolio tracking
- Risk management features

## Bugs
- WebSocket connection stability issues
  - Multiple types of connection failures observed:
    1. Keepalive ping timeout errors (Error 1011)
    2. Policy violation/Pong timeout errors (Error 1008)
    3. DNS resolution failures after network interruption
    4. Silent connection drops with no close frame
  - Specific error patterns:
    * "keepalive ping timeout; no close frame received"
    * "policy violation Pong timeout"
    * "nodename nor servname provided, or not known"
    * "Cannot connect to host api.binance.com:443"
  - Connection drops occurring every 15-45 minutes
  - Reconnection attempts failing after network interruption
  - Priority: High
  - Potential fixes needed:
    * Implement proper ping/pong handling
    * Add DNS resolution retry logic
    * Improve keepalive mechanism
    * Handle SSL/TLS connection properly
    * Add connection health monitoring

## Planned 📋
- Email/Telegram notifications
- Custom trading strategies
- Multiple exchange support
- Docker containerization
- Unit tests
- CI/CD pipeline

## WebSocket Integration
- Implement real-time order status monitoring using Binance WebSocket API
- Features to implement:
  * Connect to Binance user data stream
  * Monitor order execution status
  * Send desktop notifications when orders are filled
  * Option to automatically place follow-up orders (e.g., sell order after buy is filled)
  * Real-time price alerts

### Technical Details
```python
# Example WebSocket implementation:
from binance.websockets import BinanceSocketManager
from binance.client import Client

def order_update_callback(msg):
    """Handle order updates"""
    if msg['e'] == 'executionReport':
        if msg['X'] == 'FILLED':  # Order filled
            send_notification(f"Order {msg['i']} filled at {msg['p']}")
            if msg['S'] == 'BUY':  # If it was a buy order
                place_sell_order(msg)  # Place corresponding sell order

def implement_websocket():
    bm = BinanceSocketManager(client)
    # Start user data stream
    bm.start_user_socket(order_update_callback)
    bm.start()
```

### Required Dependencies
- `python-binance` with WebSocket support
- Desktop notification library (platform specific)
- Secure storage for maintaining WebSocket connection

### Security Considerations
- Ensure secure WebSocket connection
- Handle connection drops and reconnection
- Validate all incoming data
- Store user preferences securely

## Other Planned Features
1. Price Alerts
   - Set price targets for notifications
   - Multiple alert conditions (above/below/crossing)

2. Advanced Order Types
   - OCO (One-Cancels-the-Other) orders
   - Trailing stop orders
   - DCA (Dollar Cost Averaging) orders

3. Portfolio Analytics
   - Track P&L over time
   - Position sizing recommendations
   - Risk management calculations

4. Enhanced AI Features
   - Backtesting AI recommendations
   - Custom trading strategies
   - Multiple timeframe analysis

## Priority Order
1. WebSocket Integration
2. Price Alerts
3. Advanced Order Types
4. Portfolio Analytics
5. Enhanced AI Features

## AI Consultation Optimization
- Optimize AI consultation frequency to reduce API costs:
  1. Add cooldown period after rejected recommendations (e.g., wait 5-10 minutes instead of 1)
  2. Track market conditions that led to low confidence and skip AI calls in similar conditions
  3. Implement caching for AI recommendations with similar market conditions
  4. Add price change threshold - only consult AI if price moved significantly
  5. Consider implementing a pre-filter using technical indicators before calling AI

## Critical Issues
- Fix market data not being provided to AI for price analysis
  1. Ensure market_snapshot includes current price, volume, and order book data
  2. Add technical indicators (RSI, MA, MACD) to market data
  3. Include historical price data for better context
  4. Add bid/ask volumes and order book depth 

## Price Monitoring Strategy
- While waiting for SELL order to fill, monitor current market price
- If price drops significantly below our last BUY price:
  - Consider canceling the SELL order
  - Place a new BUY order to average down the position
  - Update the SELL target based on the new average entry price
- Considerations:
  - Need to define what constitutes a "significant" price drop
  - Need to manage risk by limiting the total position size
  - Should consult AI about whether averaging down makes sense given market conditions
  - Need to track multiple entry prices and calculate weighted average
  - Consider implementing a maximum number of averaging attempts 