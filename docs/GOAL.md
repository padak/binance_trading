I’d like to create a controller for an autonomous trading script. The goal is to have a simple initial version that places a BUY order, and only if the BUY order is fulfilled, it will place a SELL order. Once the SELL order is fulfilled, it will create a new BUY order. To determine the optimal thresholds for BUY and SELL, we want to consult with an AI strategy. We already have an OpenRouter implementation for this purpose.

To speed up transactions, I think lowering the margin is a good approach. However, we don’t want to lose money! Note that the fees are 0.1% for each transaction.

We’ll be trading the TRUMP/USDC token pair, and in all cases, we’ll be buying TRUMP with a total value of 10 USDC. Once the BUY order is filled, we’ll place a SELL order for a slightly higher price to generate a small margin. How much? At least enough to get 10.1 USDC back to cover fees and leave a small profit.

The core question is:

1. What is the market price of the TRUMP coin to determine a low BUY price?
2. How much should the SELL price be to secure a profit while avoiding excessive waiting times?

We already have two scripts:

- binance_monitor.py, which receives live messages from the Binance WebSocket.
- binance_orders.py, which manages market actions.

Since we’re operating with only 10 USDC, I don’t want to implement a STOP LOSS strategy for now (perhaps later).

Could you help me design the architecture for this system? Let me know if you need more details, and feel free to propose any additional features or considerations.
