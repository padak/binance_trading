# Binance TRUMP/USDC Order Manager

A command-line tool for managing and viewing TRUMP/USDC orders on Binance.

## Features

- View pending buy/sell orders
- View order history
- View TRUMP token price history
- Display results in table format
- Detailed verbose mode for debugging

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

4. Create a `.env` file with your Binance API credentials:
```
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

## Usage

### View Order History
```bash
# Show last 2 days of orders (default)
python binance_orders.py --orders_history

# Show last 5 days of orders
python binance_orders.py --orders_history 5

# Show in table format
python binance_orders.py --orders_history 5 --table
```

### View Pending Orders
```bash
# Show all pending orders
python binance_orders.py --buy_orders
python binance_orders.py --sell_orders
```

### View Token Price History
```bash
# Show last 2 days of price history
python binance_orders.py --token_history

# Show last 5 days of price history
python binance_orders.py --token_history 5
```

### Additional Options
```bash
# Show detailed processing information
python binance_orders.py --orders_history 5 --verbose

# Show help
python binance_orders.py --help
```

## Security Note

Never commit your `.env` file or expose your API credentials. The `.env` file is included in `.gitignore` for security. 