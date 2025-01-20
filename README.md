# Binance TRUMP/USDC Order Manager

A command-line tool for managing and viewing TRUMP/USDC orders on Binance, with automatic sell order placement.

## Features

- **Price History Analysis**
  - View historical price data with customizable intervals
  - Technical indicators (MA5, MA20, VWAP)
  - Volume analysis and trade counts
  - Price change percentages
  - Export data in JSON format

- **Order Management**
  - View pending buy/sell orders for any trading pair
  - Track order history
  - Monitor order execution status
  - Calculate potential profit/loss
  - Display orders in table format

- **AI Trading Recommendations**
  - Multiple AI models support through OpenRouter:
    - GPT-4 (gpt4o)
    - GPT-4 Turbo
    - GPT-3.5 Turbo
    - Claude-3.5 Haiku
    - Claude-3.5 Sonnet
    - Mistral Codestral
    - DeepSeek R1
  - Technical analysis
  - Buy/Sell order suggestions
  - Price trend predictions
  - Support/Resistance levels

## Scripts

### Main Order Management Script (`binance_orders.py`)
- View pending orders, order history, and price history
- Get AI recommendations for trading
- Uses read-only API key (BINANCE_API_KEY)
- Safe for monitoring - cannot place or modify orders

### WebSocket Monitor (`binance_monitor.py`)
- Real-time monitoring of order status changes using read-only API
- Automatic sell order placement when buy orders are filled using trading API
- Default 5% profit margin for sell orders
- Live account balance updates
- Uses both API keys (read-only for monitoring, trading for placing orders)

### Debug Utility (`binance_sell.py`)
- Command-line utility for testing sell order placement
- Useful for verifying API permissions and order parameters
- Supports custom price and quantity settings
- Uses trading API key (BINANCE_TRADE_API_KEY)
- Requires "Enable Trading" permission

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd binance
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API credentials:
```
# Read-only API key (for monitoring orders and prices)
BINANCE_API_KEY=your_read_only_api_key_here
BINANCE_API_SECRET=your_read_only_api_secret_here

# Write-enabled API key (for placing orders)
BINANCE_TRADE_API_KEY=your_write_enabled_api_key_here
BINANCE_TRADE_API_SECRET=your_write_enabled_api_secret_here

# OpenRouter API key (for AI trading recommendations)
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

To get your Binance API credentials:
1. Log in to your Binance account
2. Go to Profile > API Management
3. Create two API keys:
   - One with "Read Only" permissions for monitoring
   - One with "Enable Trading" permission for placing orders
4. Save your API Keys and Secret Keys securely

To get your OpenRouter API key:
1. Visit https://openrouter.ai/
2. Sign up or log in to your account
3. Go to the Keys section
4. Create a new API key
5. Copy the key and save it securely

Note: Keep your API keys secure and never share them. The `.env` file is included in `.gitignore` for security.

## Usage

### View Order History
```bash
# Show last 2 days of orders (default)
python binance_orders.py --orders_history

# Show last 5 days of orders
python binance_orders.py --orders_history 5 --pair TRUMPUSDC

# Show in table format
python binance_orders.py --orders_history 5 --table
```

### View Pending Orders
```bash
# Show all pending orders
python binance_orders.py --buy_orders
python binance_orders.py --sell_orders

# Show orders for specific trading pair
python binance_orders.py --buy_orders --pair BTCUSDC
```

### Monitor Orders and Auto-Sell
```bash
# Start WebSocket monitor (auto-sells when buy orders fill)
python binance_monitor.py
```

### Manual Sell Order (Debug)
```bash
# Place a sell order with specific parameters
python binance_sell.py --quantity 0.028 --price 40.50

# Place a sell order for different trading pair
python binance_sell.py --symbol BTCUSDC --quantity 0.001 --price 45000.00
```

### Get AI Trading Recommendations
```bash
# Get recommendations with default settings
python binance_orders.py --token_history --ask-ai

# Get concise recommendations
python binance_orders.py --token_history --ask-ai --concise

# Use specific AI model
python binance_orders.py --token_history --ask-ai --ai-model claude3
```

## AI Trading Recommendations Example

The AI provides detailed analysis including:
- Strategic buy/sell orders with price targets
- Technical analysis and trend direction
- Support and resistance levels
- Volume analysis
- Short-term price prediction
- Expected return after fees (0.1% per trade)

Example output:
```
Buy Orders:
- Conservative: 38.00 USDC (Support level)
- Medium: 40.00 USDC (Moving average)
- Aggressive: 41.50 USDC (Resistance test)

Sell Orders:
- Conservative: 45.00 USDC (+5.2% after fees)
- Medium: 48.00 USDC (+11.8% after fees)
- Aggressive: 51.00 USDC (+18.4% after fees)
```

## Security Note

- Never commit your `.env` file or expose your API credentials
- Use read-only API keys for monitoring
- Use separate API keys with trading permissions for order placement
- The `.env` file is included in `.gitignore` for security

## Features

- **Price History Analysis**
  - View historical price data with customizable intervals
  - Technical indicators (MA5, MA20, VWAP)
  - Volume analysis and trade counts
  - Price change percentages
  - Export data in JSON format

- **Order Management**
  - View pending buy/sell orders for any trading pair
  - Track order history
  - Monitor order execution status
  - Calculate potential profit/loss
  - Display orders in table format

- **AI Trading Recommendations**
  - Multiple AI models support through OpenRouter:
    - GPT-4 (gpt4o)
    - GPT-4 Turbo
    - GPT-3.5 Turbo
    - Claude-3.5 Haiku
    - Claude-3.5 Sonnet
    - Mistral Codestral
    - DeepSeek R1
  - Technical analysis
  - Buy/Sell order suggestions
  - Price trend predictions
  - Support/Resistance levels

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd binance
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API credentials:
```
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
OPENROUTER_API_KEY=your_openrouter_api_key
```

To get your Binance API credentials:
1. Log in to your Binance account
2. Go to Profile > API Management
3. Click [Create API]
4. Set API restrictions to "Read Only" if you only need to view data
5. Save your API Key and Secret Key securely

To get your OpenRouter API key:
1. Visit https://openrouter.ai/
2. Sign up or log in to your account
3. Go to the Keys section
4. Create a new API key
5. Copy the key and save it securely

Note: Keep your API keys secure and never share them. The `.env` file is included in `.gitignore` for security.

## Usage Examples

### View Price History
```bash
# Default: Last 100 5-minute intervals of TRUMP/USDC
python binance_orders.py --token_history

# Custom pair and interval
python binance_orders.py --token_history --pair BTCUSDC --interval 15m --limit 50

# Show in table format with details
python binance_orders.py --token_history --table --verbose
```

### Monitor Orders with Auto-Sell (binance_monitor.py)
```bash
# Start WebSocket monitor with default 5% profit target
python binance_monitor.py

# The monitor will:
# 1. Watch for your buy orders being filled
# 2. Automatically place sell orders at 5% higher price
# 3. Show real-time account updates
# 4. Display order status changes
```

### Manual Sell Orders (binance_sell.py)
```bash
# Place a sell order for TRUMP/USDC
python binance_sell.py --quantity 0.028 --price 42.50

# Place a sell order for a different trading pair
python binance_sell.py --symbol BTCUSDC --quantity 0.001 --price 45000.00

# Note: Minimum order value must be at least 1 USDC
# Example: quantity * price >= 1
```

### Get AI Trading Recommendations
```bash
# Default analysis with DeepSeek R1 (last 20 records)
python binance_orders.py --token_history --ask-ai

# Use different AI models (use --list-models to see all available models)
python binance_orders.py --token_history --ask-ai --ai-model gpt4o  # GPT-4
python binance_orders.py --token_history --ask-ai --ai-model gpt4-turbo  # GPT-4 Turbo
python binance_orders.py --token_history --ask-ai --ai-model claude3.5-haiku  # Claude-3.5 Haiku

# Get concise buy/sell orders only
python binance_orders.py --token_history --ask-ai --concise

# Analysis with full dataset (specify limit)
python binance_orders.py --token_history --ask-ai --limit 288  # Analyze full 24h data

# List available AI models with details
python binance_orders.py --list-models
```

### AI Models Information
The tool supports multiple AI models through OpenRouter with different capabilities:

| Model | Context Size | Input Price | Output Price | Image Support |
|-------|--------------|-------------|--------------|---------------|
| GPT-4 | 128K tokens | $2.5/M | $10/M | Yes ($3.613/K) |
| GPT-4 Turbo | 128K tokens | $10/M | $30/M | Yes ($14.45/K) |
| GPT-3.5 | 4K tokens | $1/M | $2/M | No |
| Claude-3.5 Haiku | 200K tokens | $0.8/M | $4/M | No |
| Claude-3.5 Sonnet | 200K tokens | $3/M | $15/M | Yes ($4.8/K) |
| Mistral Codestral | 256K tokens | $0.3/M | $0.9/M | No |
| DeepSeek R1 | 64K tokens | $0.55/M | $2.19/M | No |

Note: Prices are in USD per million tokens for text and per thousand for images.

### Manage Orders
```bash
# View pending buy orders for TRUMP/USDC (default)
python binance_orders.py --buy_orders

# View pending sell orders for TRUMP/USDC (default)
python binance_orders.py --sell_orders

# View orders for other trading pairs
python binance_orders.py --buy_orders --pair BTCUSDC
python binance_orders.py --sell_orders --pair ETHUSDC

# View order history (last 2 days)
python binance_orders.py --orders_history

# View order history for specific period
python binance_orders.py --orders_history 5  # Last 5 days

# Show orders in table format
python binance_orders.py --buy_orders --table
python binance_orders.py --sell_orders --pair BTCUSDC --table
```

### Export Data
```bash
# Export price history as JSON
python binance_orders.py --token_history --json

# Export custom timeframe
python binance_orders.py --token_history --pair BTCUSDC --interval 1h --limit 24 --json
```

## Data Output Formats

### Table Format
Use `--table` for structured output:
```
+---------------------+--------+--------+--------+--------+--------+--------+
| Time                | Open   | High   | Low    | Close  | Change%| Volume |
|---------------------+--------+--------+--------+--------+--------+--------|
| 2024-03-20 10:00:00| 42.50  | 43.20  | 42.30  | 43.10  | +1.41% | 1250.5|
...
```

### JSON Format
Use `--json` for programmatic access:
```json
{
  "metadata": {
    "symbol": "TRUMPUSDC",
    "interval": "5m",
    "records": 100
  },
  "data": [
    {
      "timestamp": "2024-03-20 10:00:00",
      "open": 42.50,
      "high": 43.20,
      "low": 42.30,
      "close": 43.10,
      "volume": 1250.5,
      ...
    }
  ]
}
```

### AI Trading Recommendations Example
Using `--ask-ai` (with Claude-3.5 Sonnet):
```
Trading Recommendations:
================================================================================
1. STRATEGIC BUY ORDERS

Conservative:
- Entry Price: 39.92 USDC
- Rationale: The current price is near the recent low of 35.16 USDC, indicating a potential rebound. The volume is average, suggesting a steady market with potential for a gradual recovery.
- Price Target: 42.00 USDC (5% gain)
- Stop Loss: 38.00 USDC (5% loss)

Medium:
- Entry Price: 38.50 USDC
- Rationale: Strong support level with increasing volume, suggesting accumulation phase.
- Price Target: 41.50 USDC (8% gain)
- Stop Loss: 36.50 USDC (5% loss)

Aggressive:
- Entry Price: 37.20 USDC
- Rationale: Major support zone with historical bounces and high volume.
- Price Target: 43.00 USDC (15% gain)
- Stop Loss: 35.00 USDC (6% loss)

2. STRATEGIC SELL ORDERS

Conservative:
- Entry Price: 41.50 USDC
- Rationale: Near recent resistance with declining volume.
- Price Target: 40.00 USDC (4% gain)
- Stop Loss: 43.00 USDC (4% loss)

Medium:
- Entry Price: 42.50 USDC
- Rationale: Historical resistance level with bearish divergence.
- Price Target: 39.50 USDC (7% gain)
- Stop Loss: 44.50 USDC (5% loss)

Aggressive:
- Entry Price: 44.00 USDC
- Rationale: Major resistance zone with overbought indicators.
- Price Target: 38.00 USDC (14% gain)
- Stop Loss: 46.00 USDC (5% loss)

3. TECHNICAL ANALYSIS
Trend Direction: Bearish with -23.39% change over last period
Support Levels: 38.90 (major), 37.50 (weekly), 36.00 (monthly)
Resistance Levels: 42.50 (immediate), 44.00 (major), 46.00 (yearly high)
Volume Analysis: Average volume 65,240.24, showing accumulation at support levels
Price Patterns: Double bottom forming at 37.50 level
Moving Averages: MA5 below MA20, indicating bearish trend
VWAP Analysis: Price trading below VWAP, suggesting selling pressure

4. SHORT-TERM PREDICTION
Target Price: 41.00 USDC
Confidence Level: 70%
Timeframe: 24-48 hours
Risk Factors: High market volatility, upcoming platform updates
Market Sentiment: Neutral with bearish bias
```

For concise output, use `--ask-ai --concise` to get only the buy/sell orders:
```
BUY ORDERS:
1. Conservative: 38.90 USDC
2. Medium: 40.80 USDC
3. Aggressive: 41.90 USDC

SELL ORDERS:
1. Conservative: 41.50 USDC
2. Medium: 42.50 USDC
3. Aggressive: 43.50 USDC
```

## AI Prompt Structure

The tool sends the following data structure to AI models for analysis:

```
Based on the following cryptocurrency trading data for the last period:
- Current Price: <price> USDC
- Highest Price: <price> USDC
- Lowest Price: <price> USDC
- Price Change: <percentage>%
- Average Volume: <volume>

Historical price data (20 or full dataset intervals):
| Time | Open | Close | High | Low | Change% | Volume | MA5 | MA20 | VWAP |
|------|------|-------|------|-----|---------|--------|-----|------|------|
| ...  | ...  | ...   | ... | ... | ...     | ...    | ... | ...  | ...  |

Note: Include transaction fees (0.1% per trade) in your calculations.

For concise mode (--concise flag), the response format:
BUY ORDERS:
1. Conservative: <price> USDC
2. Medium: <price> USDC
3. Aggressive: <price> USDC

SELL ORDERS: (include potential earnings % after fees)
1. Conservative: <price> USDC (+<percentage>% after fees)
2. Medium: <price> USDC (+<percentage>% after fees)
3. Aggressive: <price> USDC (+<percentage>% after fees)

For full analysis mode (default), the response format:
1. STRATEGIC BUY ORDERS
   For each order (Conservative, Medium, Aggressive):
   - Entry Price: <price> USDC
   - Rationale: <detailed explanation>
   - Price Target: <target> USDC (+<percentage>% after fees)
   - Stop Loss: <stop> USDC (-<percentage>% after fees)

2. STRATEGIC SELL ORDERS
   For each order (Conservative, Medium, Aggressive):
   - Entry Price: <price> USDC
   - Rationale: <detailed explanation>
   - Price Target: <target> USDC (+<percentage>% after fees)
   - Stop Loss: <stop> USDC (-<percentage>% after fees)

3. TECHNICAL ANALYSIS
   Trend Direction: <description>
   Support Levels: <levels with explanations>
   Resistance Levels: <levels with explanations>
   Volume Analysis: <detailed volume analysis>
   Price Patterns: <identified patterns and implications>
   Moving Averages: <MA5 and MA20 analysis>
   VWAP Analysis: <VWAP interpretation>

4. SHORT-TERM PREDICTION
   Target Price: <price> USDC
   Expected Return: <percentage>% after fees
   Confidence Level: <percentage>
   Timeframe: <period>
   Risk Factors: <key risks to consider>
   Market Sentiment: <current market sentiment>
```

## Security Notes

- Never commit your `.env` file
- Use API keys with appropriate permissions (read-only if possible)
- Monitor your API usage when using AI features
- Keep your dependencies updated

## Error Handling

The tool includes comprehensive error handling:
- API connection issues
- Invalid parameters
- Rate limiting
- Data validation

Use `--verbose` flag for detailed error information.

## Contributing

Feel free to submit issues and enhancement requests! 