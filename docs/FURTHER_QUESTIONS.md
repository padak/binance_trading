
# User's Answers for Trading Bot Design

## Trading Frequency / Time Horizon
**Q:** How often do you want to be placing orders? Are you aiming for very quick (intra-minute) flips or more laid-back trades (every few hours/days)?  
**A:** I aim for quick flips.

---

## Order Type Preference
**Q:** Do you plan to use limit orders (you specify the exact price at which you want to buy/sell) or market orders (immediate fill at the current best market price)?  
**A:** If you can identify what is the current best market price, let’s place orders real-time. But to me, it seems better to use limit order and specify expected market price and wait a bit. Let’s always sell the same amount as we bought recently.

---

## Monitoring and Execution
**Q:** You mention you already have `binance_monitor.py` for websockets. Do you plan on storing that data somewhere (like an in-memory queue or a local database), or do you plan to feed it into your logic “live”? How fast do you need to react to market data?  
**A:** I would store data in memory. If the system failed, when started, it should read the status of active orders to not start BUYing if there is a pending BUY order. 1-second reaction is enough.

---

## AI Strategy Integration
**Q:** Is the AI going to generate just price thresholds (i.e., “buy at 0.053, sell at 0.056”)? Or do you want the AI to handle more sophisticated logic, like confidence levels, volatility detection, etc.?  
**A:** To place a BUY order and then SELL order, we need just “buy at 0.053, sell at 0.056.” But to generate such commands as perfectly as possible, it would be great if the AI will also perform advanced analysis.

---

## Error Handling & Connectivity
**Q:** What happens if Binance websockets disconnect? Do you have a fallback (like REST requests to fetch the latest price)?  
**A:** Let’s assume Binance websockets are durable and the only issue will be my internet connectivity. So detect if websocket is still alive and try to keep it working if possible.

---

## Regulatory or Bot Constraints
**Q:** Since you’re dealing with a small amount of funds (10 USDC), are you aware of minimum trade sizes for TRUMP/USDC on Binance (or whichever exchange you’re using)? Is 10 USDC definitely above that threshold?  
**A:** Yes, the minimum volume is 5 USDC.

---

## AI Inputs
**Q:** What specific market data should the AI analyze?  
**A:** This is an example of JSON data. We can provide it also in table format:

```json
{
  "metadata": {
    "symbol": "TRUMPUSDC",
    "interval": "15m",
    "records": 3,
    "period_start": "2025-01-21 10:30:00",
    "period_end": "2025-01-21 11:00:00"
  },
  "summary": {
    "price_change": 2.110682110682111,
    "highest_price": 39.7,
    "lowest_price": 37.9,
    "total_volume": 107975.173,
    "total_trades": 9900,
    "average_price": 39.2,
    "average_volume": 35991.72433333333
  },
  "data": [
    {
      "timestamp": "2025-01-21 10:30:00",
      "open": 38.3,
      "high": 39.32,
      "low": 37.9,
      "close": 38.85,
      "volume": 50159.579,
      "quote_volume": 1941483.56139,
      "trades": 4775,
      "price_change": 1.4360313315927005,
      "MA5": null,
      "MA20": null,
      "VWAP": 38.7061374934985,
      "volume_change": null
    },
    {
      "timestamp": "2025-01-21 10:45:00",
      "open": 38.8,
      "high": 39.56,
      "low": 38.29,
      "close": 39.08,
      "volume": 31422.026,
      "quote_volume": 1226965.95391,
      "trades": 3114,
      "price_change": 0.7216494845360855,
      "MA5": null,
      "MA20": null,
      "VWAP": 39.047958075968744,
      "volume_change": -37.35588171503592
    },
    {
      "timestamp": "2025-01-21 11:00:00",
      "open": 39.02,
      "high": 39.7,
      "low": 38.65,
      "close": 39.67,
      "volume": 26393.568,
      "quote_volume": 1038705.37305,
      "trades": 2011,
      "price_change": 1.6658124038954343,
      "MA5": null,
      "MA20": null,
      "VWAP": 39.354488678832666,
      "volume_change": -16.002971928035457
    }
  ]
}
```

---

## Frequency of AI Consultation
**Q:** How often should the AI recalculate thresholds?  
**A:** After each successful SELL. The average cost of AI consultancy is $0.005.

---

## Profit Margin Definition
**Q:** Is the 0.1 USDC profit target after fees?  
**A:** This was just an example. Try to find a good margin using AI. I don’t want to have the margin defined as “X%” in the script. Be smart!

---

## TRUMP/USDC Specifics
**Q:** Is TRUMP a stablecoin or a volatile asset? This affects how aggressively you can set margins.  
**A:** Try to identify based on historical data. You’ll get the token pair and you can fetch data about the market.
