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
  - View pending buy/sell orders
  - Track order history
  - Monitor order execution status
  - Calculate potential profit/loss

- **AI Trading Recommendations**
  - Multiple AI models support:
    - GPT-4 (OpenAI)
    - GPT-4 Turbo
    - GPT-3.5 Turbo
    - GPT-4 OpenRouter
    - GPT-4-32k OpenRouter (Mini)
    - Claude-3 Opus
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
OPENAI_API_KEY=your_openai_api_key
```

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
# Default analysis with GPT-4-32k OpenRouter
python binance_orders.py --token_history --gpt

# Use different AI models
python binance_orders.py --token_history --gpt --gpt-model gpt4  # OpenAI GPT-4
python binance_orders.py --token_history --gpt --gpt-model gpt4-turbo  # GPT-4 Turbo
python binance_orders.py --token_history --gpt --gpt-model gpt4o  # OpenRouter GPT-4
python binance_orders.py --token_history --gpt --gpt-model o1  # Claude-3 Opus

# Get concise buy/sell orders only
python binance_orders.py --token_history --gpt --concise

# Analysis with full dataset
python binance_orders.py --token_history --gpt --full-data
```

### Manage Orders
```bash
# View pending buy orders
python binance_orders.py --buy_orders

# View pending sell orders
python binance_orders.py --sell_orders

# View order history (last 2 days)
python binance_orders.py --orders_history

# View order history for specific period
python binance_orders.py --orders_history 5  # Last 5 days
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