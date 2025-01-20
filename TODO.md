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

## In Progress 🚧
- Backtesting functionality
- Historical performance analysis
- Portfolio tracking
- Risk management features

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