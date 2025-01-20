# Binance TRUMP/USDC Order Manager

A powerful command-line tool for managing and analyzing TRUMP/USDC trading on Binance. Features advanced price analysis, AI-powered trading recommendations, and comprehensive order management.

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

### Get AI Trading Recommendations
```bash
# Default analysis with DeepSeek R1
python binance_orders.py --token_history --ask-ai

# Use different AI models
python binance_orders.py --token_history --ask-ai --ai-model gpt4o  # GPT-4
python binance_orders.py --token_history --ask-ai --ai-model gpt4-turbo  # GPT-4 Turbo
python binance_orders.py --token_history --ask-ai --ai-model claude3.5-haiku  # Claude-3.5 Haiku
python binance_orders.py --token_history --ask-ai --ai-model claude3.5-sonnet  # Claude-3.5 Sonnet
python binance_orders.py --token_history --ask-ai --ai-model mistral-codestral  # Mistral Codestral

# Get concise buy/sell orders only
python binance_orders.py --token_history --ask-ai --concise

# Analysis with full dataset
python binance_orders.py --token_history --ask-ai --full-data
```

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