### Implementation Plan: Autonomous Trading Bot for TRUMP/USDC

---

#### **1. System Architecture**
```plaintext
+-------------------+       +---------------------+       +-------------------+
| Binance WebSocket | ----> | Market Data Pipeline| ----> | State Manager     |
| (binance_monitor) |       | (In-Memory Storage) |       | (BUY/SELL/IDLE)   |
+-------------------+       +---------------------+       +-------------------+
                                |                               |
                                v                               v
                        +-------------------+           +-------------------+
                        | AI Strategy Module| <-------- | Order Execution   |
                        | (OpenRouter)      |           | (binance_orders)  |
                        +-------------------+           +-------------------+
                                |                               |
                                v                               v
                        +-------------------+           +-------------------+
                        | Profit Calculator |           | Error Handler     |
                        | (Fee-aware Logic) |           | (Reconnect/Retry) |
                        +-------------------+           +-------------------+
```

---

#### **2. Components**

##### **2.1 Market Data Pipeline (`binance_monitor.py`)**
- **Input**: TRUMP/USDC real-time data via Binance WebSocket.
- **Storage**: Keep in-memory data structures:
  - Latest `order book` (bids/asks).
  - Last 15-minute candles (price, volume, VWAP, volatility).
  - Recent trades (for volume trends).
- **Triggers**:
  - Update data every 1 second (aligned with reaction time).
  - On disconnect, attempt reconnection + fetch latest data via REST as backup.

##### **2.2 State Manager**
- **States**:
  - `BUY`: Waiting to buy TRUMP with 10 USDC.
  - `SELL`: Waiting to sell TRUMP after a successful buy.
  - `IDLE`: Error state or awaiting restart.
- **Persistence**:
  - On startup, check Binance API for active orders to avoid duplicates.
  - Store current state in-memory (no database needed for simplicity).

##### **2.3 AI Strategy Module**
- **Inputs** (sent to OpenRouter):
  ```json
  {
    "current_price": 39.67,
    "bid_ask_spread": 0.05,  // Current spread
    "recent_volatility": 1.665,  // From last candle's price_change
    "vwap": 39.35,             // Volume-weighted average price
    "order_book_imbalance": -0.02,  // (Bid Volume - Ask Volume) / Total
    "volume_trend": "declining"  // From last 3 candles' volume_change
  }
  ```
- **Outputs**:
  - `buy_price`: Limit price for BUY order.
  - `sell_price`: Limit price for SELL order (must exceed fees + profit).

##### **2.4 Order Execution (`binance_orders.py`)**
- **Actions**:
  - Place/cancel limit orders.
  - Ensure order size matches 10 USDC (buy) or full TRUMP amount (sell).
- **Validation**:
  - Reject AI suggestions if `sell_price < (buy_cost * 1.002)` (0.2% profit after fees).

##### **2.5 Profit Calculator**
- **Formula**:
  ```
  min_sell_price = (buy_cost * (1 + fee)) / (1 - fee)
  fee = 0.1% per trade
  Example: Buy at 39.67 → min_sell_price = 39.67 * 1.001 / 0.999 ≈ 39.83
  ```
- **Role**: Ensure AI’s `sell_price` meets this threshold.

##### **2.6 Error Handler**
- **Tasks**:
  - Monitor WebSocket connectivity (ping every 10 seconds).
  - Retry failed orders up to 3 times.
  - Fallback to REST API if WebSocket dies.

---

#### **3. Workflow**
1. **Startup**:
   - Check for open orders via Binance API.
   - Resume from last state (e.g., if a BUY order is pending, wait for fill).

2. **BUY Phase**:
   - AI analyzes latest data → suggests `buy_price`.
   - Place limit BUY order for 10 USDC worth of TRUMP at `buy_price`.
   - On fill, transition to `SELL` state.

3. **SELL Phase**:
   - Calculate `min_sell_price` based on buy cost + fees.
   - AI suggests `sell_price` ≥ `min_sell_price`.
   - Place limit SELL order for all TRUMP acquired.
   - On fill, cycle back to `BUY` state.

---

#### **4. AI Strategy Details**
- **Training Data**: Use historical TRUMP/USDC data to infer:
  - Optimal profit margins based on volatility (higher volatility → wider spreads).
  - Order book imbalances (e.g., high bid volume → bullish → raise sell price).
- **Sample Prompt to OpenRouter**:
  ```
  Given the current price of TRUMP/USDC is 39.67, bid-ask spread 0.05, 
  recent volatility 1.6%, and declining volume, suggest buy/sell prices 
  to maximize profit with a 0.1% fee per trade. Respond in JSON format:
  { "buy_price": x, "sell_price": y }
  ```

---

#### **5. Risk Mitigation**
- **Liquidity Check**: Ensure BUY/SELL prices are within top 5 order book levels.
- **Timeouts**: Cancel orders if unfilled after 2 minutes (adjustable).
- **Logging**: Record all trades, AI decisions, and errors for review.

---

#### **6. Next Steps**
1. Finalize AI input parameters (e.g., add RSI or MACD if needed).
2. Implement fee-aware profit validation in `ProfitCalculator`.
3. Test with Binance testnet API before live deployment.

---

### **Final Questions**
1. Should the AI factor in **time-of-day** patterns (e.g., higher volatility during specific hours)?
2. Do you need a manual override (e.g., force cancel all orders via CLI)?

Let me know if you want the code scaffold for any component!