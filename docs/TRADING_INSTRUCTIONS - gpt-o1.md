# Trading Bot Implementation Plan

## 1. Overview

We are building an **autonomous trading bot** for the TRUMP/USDC pair. The bot’s logic is straightforward:

1. **Buy** a fixed amount of TRUMP (10 USDC worth) via **limit order** at a price recommended by an AI/strategy module.
2. After the buy is **fully filled**, place a **limit sell** for the exact same TRUMP quantity at an AI-recommended sell price.
3. Once the sell is **fully filled**, repeat the cycle.

### Key Features

- **Quick flips**: The bot will operate on a short time frame, aiming for small, rapid profits.
- **AI-driven thresholds**: We will send market data to an AI module that returns **“buy at PRICE, sell at PRICE”** suggestions.  
  - The AI consultation happens **after each successful SELL**.
- **No stop-loss**: We temporarily skip stop-loss logic. If a sell order never fills, we remain in TRUMP indefinitely.
- **Minimal capital**: We use ~10 USDC for each buy, which is above the 5 USDC min notional limit.
- **Fee awareness**: Binance fees are ~0.1% for each trade. The AI should aim for a margin that yields net profit after fees.

---

## 2. Architecture

```
                          +--------------------------+
                          |      AI Module          |
                          |  (Receive market data,  |
                          |  return buy/sell price) |
                          +-----------+--------------+
                                      |
                                      v
+---------------------+   +---------------------+    +----------------------+
| binance_monitor.py  |   |    Strategy Logic   |    |  binance_orders.py   |
| (WebSocket Client)  |-->|  (Controller Script)|--->| (REST API Functions) |
| - Receives real-time|   | - Maintains states  |    | - place_limit_buy()  |
|   price/order data  |   | - Calls AI after sell|    | - place_limit_sell() |
+---------------------+   | - Buys & sells w/10 U |    | - check_order_state()|
                          | - Watches for fills  |    +----------------------+
                          +-----------+-----------+
                                      |
                                      v
                             +-----------------+
                             |  State/Logging  |
                             |  (in-memory +   |
                             |   re-init on   |
                             |   restart)     |
                             +-----------------+
```

### 2.1 `binance_monitor.py`
- **Responsibilities**:
  - Connect to the Binance WebSocket for TRUMP/USDC market data and user-data streams (to detect fills).
  - Maintain a lightweight in-memory queue/structure of the latest trades or ticker price.
  - Send relevant events to the Strategy Logic (e.g., price updates, order fill confirmations).

### 2.2 `binance_orders.py`
- **Responsibilities**:
  - Provide **wrapper functions** around Binance REST endpoints:
    - `place_limit_buy(symbol, quantity, price)`
    - `place_limit_sell(symbol, quantity, price)`
    - `get_order_status(symbol, order_id)`
    - `cancel_order(symbol, order_id)` (optional for future logic)
  - Return order IDs and statuses that the Strategy Logic can track.
  - On startup (or when reconnected), fetch **active orders** to recover state if the bot is restarted.

### 2.3 Strategy Logic (Controller Script)
- **Responsibilities**:
  1. **Initialize**:
     - Check if we have an **open position** or **open orders** from a previous run.  
       - If open BUY order exists, wait for fill or cancel it.  
       - If we already hold TRUMP, we move to the SELL logic.  
       - If open SELL order exists, wait for fill or cancel, etc.
  2. **Run Loop**:
     - If in **USDC** (no open position):
       1. Query **AI module** for recommended thresholds (`buy_price`, `sell_price`) if none exist yet.
       2. Place a **limit BUY** at `buy_price` for 10 USDC worth of TRUMP.
       3. Monitor fill events from `binance_monitor.py`.
         - If partially filled, keep track of filled quantity. If fully filled, move to SELL step.
     - If in **TRUMP** (we hold TRUMP from a previous buy):
       1. Use the previously decided `sell_price` or (optionally) re-check with AI if you want dynamic updates.
       2. Place a **limit SELL** at `sell_price` for the entire TRUMP quantity we hold.
       3. Monitor fill events until fully filled.
         - Once filled, log the trade outcome and **consult AI** again for new thresholds.
         - Return to the BUY step.
  3. **Record-Keeping**:
     - Store the buy and sell events (timestamp, price, quantity, fees, etc.) in a data structure (and optionally on disk).
  4. **Error Handling**:
     - If the WebSocket or internet fails, attempt reconnection or fallback to REST.
     - On restart, resync with open orders to ensure no duplicated trades.

### 2.4 AI Module
- **Responsibilities**:
  - **Analyze** relevant market data from the last period (price, volume, volatility, etc.).
  - **Return** recommended `buy_price` and `sell_price`.
  - Called **after each SELL** (or more frequently if desired).
- **Data Provided**:
  - Historical or real-time JSON (like the example) with open/high/low/close (OHLC), volume, trades, VWAP, etc.
  - Possibly live order-book data from `binance_monitor.py`.
- **Integration**:
  - Could be a separate microservice or local Python script. 
  - Example: `ai_module.get_thresholds(historical_data) -> (buy_price, sell_price)`.

---

## 3. Detailed Steps

1. **Bot Initialization**:
   1. Load config (API keys, symbol, etc.).
   2. Connect to Binance WebSocket via `binance_monitor.py`.
   3. Query `binance_orders.py` to see if there are **any open orders**:
      - If there’s an open BUY, wait for fill or decide if you want to cancel and re-place it.
      - If we already hold TRUMP (check balances or open SELL), proceed to SELL logic.

2. **BUY Logic**:
   1. If we have **0 TRUMP** and no open BUY order:
      - Ask AI: `buy_price, sell_price = ai_module.get_thresholds(market_data)`.
      - Place `limit BUY` for 10 USDC worth of TRUMP at `buy_price`.
      - Wait until the order is **fully filled** (watch fill events from `binance_monitor.py`).
        - If partially filled for a long time and you want to be more aggressive, you can:
          - Cancel the remaining portion and re-place a new order. (Optional strategy)
      - Once filled, store `fill_price`. Switch to SELL logic.

3. **SELL Logic**:
   1. We now hold some TRUMP quantity (e.g., ~X TRUMP).
   2. If we have no open SELL order, place a `limit SELL` at the previously determined `sell_price`.
   3. Wait for fill:
      - If it’s partially filled, monitor the rest.  
      - Once fully filled, we get back ~10 + margin USDC (minus fees).
   4. Log the transaction outcome, including:
      - Buy fill price, sell fill price, net profit (USDC), fees paid.
   5. **Consult AI** for next buy threshold (or you can wait until just before the next BUY event). 
   6. Cycle repeats.

4. **Data & Logging**:
   - Maintain a small in-memory list/dict for each trade:  
     ```
     trades = [
       {
         "buy_price": 38.85,
         "buy_time": "2025-01-21 10:30:00",
         "sell_price": 39.67,
         "sell_time": "2025-01-21 11:00:00",
         "quantity": 0.25,  # TRUMP
         "profit_usdc": 0.12,
         "fees_usdc": 0.02
       },
       ...
     ]
     ```
   - (Optional) Also store the data in a JSON or CSV file for permanent record. 
   - This is crucial if you want your AI model to improve based on actual results.

5. **AI Consultation Frequency**:
   - **After each SELL**: The script calls the AI with the most recent historical data (15m intervals or real-time).
   - The cost of AI call is $0.005, which is minor but worth noting in your net profit calculations.

6. **Error Handling & Recovery**:
   - **WebSocket issues**: Implement a “heartbeat” every few seconds. If no data arrives for N seconds, reconnect.
   - **On restart**: 
     - Use `binance_orders.py` to detect any open orders.
     - Use `binance_orders.py` or direct API calls to see if we hold any TRUMP (balance check).
     - Set state accordingly so we don’t place extra BUY/SELL orders by mistake.
   - **Partial fills**: Decide how long we wait before adjusting or canceling the limit order.

---

## 4. Example Code Structure

### `controller.py` (Main)

```python
import time
from binance_monitor import start_websocket, get_latest_price, get_fill_events
from binance_orders import place_limit_buy, place_limit_sell, get_open_orders, get_balance
from ai_module import get_thresholds

def main():
    # 1. Startup
    start_websocket()  # Start listening to market data
    symbol = "TRUMPUSDC"
    
    # 2. State initialization
    open_orders = get_open_orders(symbol)
    # Determine if we hold TRUMP
    trump_balance = get_balance("TRUMP")
    
    # 3. Main loop
    while True:
        if trump_balance < 0.001:  # Means we effectively hold no TRUMP
            # Check if we have pending BUY order
            if not any(o for o in open_orders if o["side"] == "BUY"):
                # a) Consult AI for thresholds
                market_data = gather_market_data()  # however you do it
                buy_price, sell_price = get_thresholds(market_data)
                
                # b) Place limit BUY
                quantity = calculate_trump_quantity(10, buy_price)
                buy_order_id = place_limit_buy(symbol, quantity, buy_price)
                
        else:
            # We hold TRUMP, check if we have pending SELL
            if not any(o for o in open_orders if o["side"] == "SELL"):
                # Place SELL order at last known sell_price
                sell_order_id = place_limit_sell(symbol, trump_balance, last_sell_price)
        
        # 4. Check fill events
        fill_events = get_fill_events()
        for event in fill_events:
            handle_fill_event(event, symbol)
        
        # 5. Sleep a bit
        time.sleep(1)

if __name__ == "__main__":
    main()
```

### `binance_monitor.py` (WebSocket Feeds)

```python
import threading
import websocket
import json

LATEST_PRICE = None
FILL_EVENTS_QUEUE = []

def on_message(ws, message):
    global LATEST_PRICE, FILL_EVENTS_QUEUE
    data = json.loads(message)
    # If message is price update, update LATEST_PRICE
    # If message is trade fill, append to FILL_EVENTS_QUEUE

def start_websocket():
    # Connect to Binance WebSocket
    ws = websocket.WebSocketApp(
        "wss://stream.binance.com:9443/ws/trumpusdc@trade",
        on_message=on_message
    )
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()

def get_latest_price():
    return LATEST_PRICE

def get_fill_events():
    """Pop fill events for processing in main loop."""
    global FILL_EVENTS_QUEUE
    events = list(FILL_EVENTS_QUEUE)
    FILL_EVENTS_QUEUE = []
    return events
```

### `binance_orders.py` (API Functions)

```python
import requests

API_KEY = "YOUR_BINANCE_API_KEY"
API_SECRET = "YOUR_BINANCE_SECRET_KEY"

def place_limit_buy(symbol, quantity, price):
    # Use Binance REST endpoint
    # Return order_id
    pass

def place_limit_sell(symbol, quantity, price):
    # ...
    pass

def get_open_orders(symbol):
    # ...
    pass

def get_balance(asset):
    # ...
    pass

def get_order_status(symbol, order_id):
    # ...
    pass
```

### `ai_module.py` (AI Logic)

```python
def get_thresholds(market_data):
    # Perform advanced analysis on JSON data
    # Return (buy_price, sell_price) dynamically
    # Example: naive approach -> buy slightly below current price, sell slightly above
    pass
```

---

## 5. Additional Considerations

1. **Fees**:  
   - The AI should target a margin that covers at least ~0.2% total (0.1% on each side) plus your target profit.
2. **Partial Fills**:  
   - Decide if partial fills are acceptable or if the bot should cancel and re-place.  
   - A simpler approach: **let partial fills accumulate** until filled, then proceed.
3. **Scalability**:  
   - If successful, you can scale your capital.  
   - Re-check minimum notional for larger or smaller trades.
4. **Risk Management**:  
   - Without a stop-loss, be prepared to hold TRUMP if the market goes down.  
   - Next iteration: implement time-based or price-based exit.
5. **Testing & Paper Trading**:  
   - Use a **testnet** or paper trading mode first to ensure logic is correct.  
   - Confirm correct handling of order statuses, fills, and reconnections.

---

## 6. Deployment & Future Steps

- **Deployment**:
  - Run as a long-lived Python process on a stable server or VPS with good connectivity.
  - Implement logs for debugging.
- **Future Enhancements**:
  - Add a stop-loss or time-based forced exit.
  - Integrate a small database (SQLite, PostgreSQL) to store all trades automatically.
  - Expand AI logic with deeper ML models and more real-time order book data.
  - Introduce a scheduled job to retrain the model using the newly collected trade logs.

---
