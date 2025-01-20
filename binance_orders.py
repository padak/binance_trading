import os
import argparse
from datetime import datetime, timedelta
from binance.client import Client
from dotenv import load_dotenv
from decimal import Decimal
from tabulate import tabulate
import numpy as np
import pandas as pd
import requests
import json

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Valid intervals for Binance API
VALID_INTERVALS = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']

# Available GPT models
GPT_MODELS = {
    'gpt4': 'gpt-4',
    'gpt4-turbo': 'gpt-4-turbo-preview',
    'gpt3.5': 'gpt-3.5-turbo',
    'gpt4o': 'openai/gpt-4',
    'gpt4o-mini': 'openai/gpt-4-32k',
    'o1': 'anthropic/claude-3-opus'
}

class BinanceOrderManager:
    def __init__(self, api_key=None, api_secret=None, verbose=False, table_format=False):
        self.api_key = api_key or API_KEY
        self.api_secret = api_secret or API_SECRET
        self.verbose = verbose
        self.table_format = table_format
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API keys are not set. Please set them in the .env file.")
        
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key is not set. Please set OPENAI_API_KEY in the .env file.")
        
        self.client = Client(api_key=self.api_key, api_secret=self.api_secret)

    def calculate_indicators(self, df):
        """Calculate technical indicators for the dataset"""
        # Calculate price change percentage
        df['price_change'] = ((df['close'] - df['open']) / df['open']) * 100
        
        # Calculate moving averages
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        
        # Calculate VWAP (Volume Weighted Average Price)
        df['vwap'] = (df['quote_volume'] / df['volume']).fillna(df['close'])
        
        # Calculate volume change percentage
        df['volume_change'] = df['volume'].pct_change() * 100
        
        return df

    def get_trading_recommendation(self, history_data, full_data=False, gpt_model='gpt4', concise=False):
        """Get trading recommendations from ChatGPT based on historical data
        Args:
            history_data: DataFrame with historical price data
            full_data: If True, sends complete dataset to GPT. If False, sends last 20 records.
            gpt_model: GPT model to use (gpt4, gpt4-turbo, gpt3.5)
            concise: If True, returns only buy/sell orders without analysis"""
        try:
            # Prepare the prompt with historical data analysis
            latest_price = history_data.iloc[-1]['close']
            highest_price = history_data['high'].max()
            lowest_price = history_data['low'].min()
            avg_volume = history_data['volume'].mean()
            price_change = ((latest_price - history_data.iloc[0]['close']) / history_data.iloc[0]['close']) * 100

            prompt = f"""Based on the following cryptocurrency trading data for the last period:
- Current Price: {latest_price:.2f} USDC
- Highest Price: {highest_price:.2f} USDC
- Lowest Price: {lowest_price:.2f} USDC
- Price Change: {price_change:.2f}%
- Average Volume: {avg_volume:.2f}

Historical price data ({len(history_data) if full_data else 20} intervals):
"""
            # Format data as a table
            table_data = []
            data_to_process = history_data if full_data else history_data.tail(20)
            
            for _, row in data_to_process.iterrows():
                price_change = ((row['close'] - row['open']) / row['open']) * 100
                table_data.append([
                    row['timestamp'].strftime('%Y-%m-%d %H:%M'),
                    f"{row['open']:.2f}",
                    f"{row['close']:.2f}",
                    f"{row['high']:.2f}",
                    f"{row['low']:.2f}",
                    f"{price_change:.2f}%",
                    f"{row['volume']:.2f}",
                    f"{row['MA5']:.2f}" if not pd.isna(row['MA5']) else "N/A",
                    f"{row['MA20']:.2f}" if not pd.isna(row['MA20']) else "N/A",
                    f"{row['vwap']:.2f}"
                ])

            # Create table with headers
            headers = ['Time', 'Open', 'Close', 'High', 'Low', 'Change%', 'Volume', 'MA5', 'MA20', 'VWAP']
            table_format = tabulate(table_data, headers=headers, tablefmt='pipe')
            
            prompt += table_format

            if concise:
                prompt += """\n\nProvide only buy and sell orders in the following format:
BUY ORDERS:
1. Conservative: <price> USDC
2. Medium: <price> USDC
3. Aggressive: <price> USDC

SELL ORDERS:
1. Conservative: <price> USDC
2. Medium: <price> USDC
3. Aggressive: <price> USDC"""
            else:
                prompt += """\n\nBased on this comprehensive historical data, please provide:
1. Three strategic buy orders (conservative, medium, aggressive) with price targets and rationale
2. Three strategic sell orders (conservative, medium, aggressive) with price targets and rationale
3. Technical analysis including:
   - Trend direction and strength
   - Key support and resistance levels
   - Volume analysis
   - Price action patterns
4. Short-term price prediction with confidence level

Please format the response in a clear, structured way with specific price targets and detailed explanations."""

            # Call ChatGPT API
            if gpt_model not in GPT_MODELS:
                raise ValueError(f"Invalid GPT model. Must be one of: {', '.join(GPT_MODELS.keys())}")

            headers = {
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': GPT_MODELS[gpt_model],
                'messages': [
                    {'role': 'system', 'content': 'You are a cryptocurrency trading expert analyzing market data and providing strategic trading recommendations.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                recommendation = response.json()['choices'][0]['message']['content']
                print("\nTrading Recommendations:")
                print("=" * 80)
                print(recommendation)
                print("=" * 80)
            else:
                print(f"Error getting recommendations: {response.text}")
                
        except Exception as e:
            print(f"Error getting trading recommendations: {e}")
            if self.verbose:
                print("Full error details:", str(e))

    def get_token_history(self, symbol="TRUMPUSDC", interval='5m', limit=100, gpt_analysis=False, full_data=False, json_output=False, gpt_model='gpt4', concise=False):
        try:
            if self.verbose:
                print(f"Fetching {symbol} price history for last {limit} {interval} intervals")
            
            # Validate interval
            if interval not in VALID_INTERVALS:
                raise ValueError(f"Invalid interval. Must be one of: {', '.join(VALID_INTERVALS)}")
            
            # Get klines (candlestick) data
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            if not klines:
                print(f"No price history found for {symbol}")
                return
            
            # Convert to pandas DataFrame for easier manipulation
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
                'taker_buy_quote_volume', 'ignored'
            ])
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Calculate indicators
            df = self.calculate_indicators(df)
            
            if json_output:
                # Convert DataFrame to JSON format
                json_data = {
                    'metadata': {
                        'symbol': symbol,
                        'interval': interval,
                        'records': int(len(df)),
                        'period_start': df['timestamp'].iloc[0].strftime('%Y-%m-%d %H:%M:%S'),
                        'period_end': df['timestamp'].iloc[-1].strftime('%Y-%m-%d %H:%M:%S'),
                    },
                    'summary': {
                        'price_change': float(((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100)),
                        'highest_price': float(df['high'].max()),
                        'lowest_price': float(df['low'].min()),
                        'total_volume': float(df['volume'].sum()),
                        'total_trades': int(df['trades'].sum()),
                        'average_price': float(df['close'].mean()),
                        'average_volume': float(df['volume'].mean())
                    },
                    'data': []
                }
                
                # Convert each row to a dictionary with explicit type conversion
                for _, row in df.iterrows():
                    json_data['data'].append({
                        'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': float(row['volume']),
                        'quote_volume': float(row['quote_volume']),
                        'trades': int(row['trades']),
                        'price_change': float(row['price_change']),
                        'MA5': None if pd.isna(row['MA5']) else float(row['MA5']),
                        'MA20': None if pd.isna(row['MA20']) else float(row['MA20']),
                        'VWAP': float(row['vwap']),
                        'volume_change': None if pd.isna(row['volume_change']) else float(row['volume_change'])
                    })
                
                # Print JSON output
                print(json.dumps(json_data, indent=2))
                return
            
            # Get trading recommendations if requested
            if gpt_analysis:
                if self.verbose:
                    print(f"Getting GPT analysis using {gpt_model} model {'with full data' if full_data else 'with last 20 records'}")
                self.get_trading_recommendation(df, full_data=full_data, gpt_model=gpt_model, concise=concise)
            
            # Prepare data for display
            table_data = []
            for _, row in df.iterrows():
                table_data.append([
                    row['timestamp'].strftime('%Y-%m-%d %H:%M'),
                    f"{row['open']:.4f}",
                    f"{row['high']:.4f}",
                    f"{row['low']:.4f}",
                    f"{row['close']:.4f}",
                    f"{row['price_change']:.2f}%",
                    f"{row['volume']:.2f}",
                    f"{row['quote_volume']:.2f}",
                    f"{row['trades']}",
                    f"{row['MA5']:.4f}" if not pd.isna(row['MA5']) else "N/A",
                    f"{row['MA20']:.4f}" if not pd.isna(row['MA20']) else "N/A",
                    f"{row['vwap']:.4f}",
                    f"{row['volume_change']:.2f}%" if not pd.isna(row['volume_change']) else "N/A"
                ])
            
            # Print results in table format
            headers = [
                'Time', 'Open', 'High', 'Low', 'Close', 'Change%',
                'Volume', 'Quote Vol', 'Trades', 'MA5', 'MA20',
                'VWAP', 'Vol Change%'
            ]
            
            print(f"\n{symbol} Price History ({interval} intervals)")
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            
            # Print summary statistics
            latest = df.iloc[-1]
            earliest = df.iloc[0]
            price_change = ((latest['close'] - earliest['close']) / earliest['close']) * 100
            print(f"\nSummary:")
            print(f"Period: {earliest['timestamp'].strftime('%Y-%m-%d %H:%M')} to {latest['timestamp'].strftime('%Y-%m-%d %H:%M')}")
            print(f"Price Change: {price_change:.2f}%")
            print(f"Highest Price: {df['high'].max():.4f}")
            print(f"Lowest Price: {df['low'].min():.4f}")
            print(f"Total Volume: {df['volume'].sum():.2f}")
            print(f"Total Trades: {df['trades'].sum()}")
                
        except Exception as e:
            print(f"Error fetching token history: {e}")
            if self.verbose:
                print("Full error details:", str(e))

    def get_current_price(self, symbol):
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            if self.verbose:
                print(f"Error getting price for {symbol}: {e}")
            return None

    def print_order_details(self, order, current_price=None):
        try:
            symbol = order['symbol']
            price = float(order['price']) if order['price'] != '0' else 0
            quantity = float(order['origQty'])
            executed = float(order['executedQty'])
            remaining = quantity - executed
            
            # Calculate total order value
            total_value = price * quantity if price > 0 else 0
            executed_value = price * executed if price > 0 else 0
            remaining_value = price * remaining if price > 0 else 0
            
            # Get current market price if not provided and it's a trading pair
            if current_price is None and 'USDC' in symbol:
                current_price = self.get_current_price(symbol)
            market_value = current_price * remaining if current_price else None
            
            # Calculate potential profit/loss for limit orders
            profit_loss = None
            if current_price and order['type'] == 'LIMIT':
                if order['side'] == 'BUY':
                    profit_loss = ((current_price - price) / price) * 100
                else:  # SELL
                    profit_loss = ((price - current_price) / current_price) * 100

            # Format strings
            current_price_str = f"{current_price:.8f}" if current_price else "N/A"
            market_value_str = f"{market_value:.2f} USDC" if market_value else "N/A"
            profit_loss_str = f"{profit_loss:.2f}%" if profit_loss is not None else "N/A"
            order_time = datetime.fromtimestamp(order['time'] / 1000)
            price_str = f"{price:.8f}" if price > 0 else "MARKET"

            # Adjust output based on order type
            if symbol == "USDCEUR" or symbol == "USDCUSDT":
                print(f"""
                Type: Fiat Purchase
                Currency: {symbol}
                Amount: {quantity:.2f}
                Status: {order['status']}
                Time: {order_time}
                """)
            else:
                print(f"""
                Pair: {symbol}
                Type: {order['type']}
                Side: {order['side']}
                Price: {price_str}
                Current Market Price: {current_price_str}
                Amount: {quantity:.8f}
                Filled: {executed:.8f}
                Remaining: {remaining:.8f}
                Status: {order['status']}
                Order ID: {order['orderId']}
                Time: {order_time}
                
                Order Value (Total): {total_value:.2f} USDC
                Executed Value: {executed_value:.2f} USDC
                Remaining Value: {remaining_value:.2f} USDC
                Current Market Value: {market_value_str}
                Potential Profit/Loss: {profit_loss_str}
                """)
        except Exception as e:
            if self.verbose:
                print(f"Error printing order details: {e}")
                print(f"Order data: {order}")

    def format_order_for_table(self, order, current_price=None):
        try:
            symbol = order['symbol']
            price = float(order['price']) if order['price'] != '0' else 0
            quantity = float(order['origQty'])
            executed = float(order['executedQty'])
            remaining = quantity - executed
            
            # Calculate total order value
            total_value = price * quantity if price > 0 else 0
            executed_value = price * executed if price > 0 else 0
            remaining_value = price * remaining if price > 0 else 0
            
            # Get current market price if not provided and it's a trading pair
            if current_price is None and 'USDC' in symbol:
                current_price = self.get_current_price(symbol)
            market_value = current_price * remaining if current_price else None
            
            # Calculate potential profit/loss for limit orders
            profit_loss = None
            if current_price and order['type'] == 'LIMIT':
                if order['side'] == 'BUY':
                    profit_loss = ((current_price - price) / price) * 100
                else:  # SELL
                    profit_loss = ((price - current_price) / current_price) * 100

            order_time = datetime.fromtimestamp(order['time'] / 1000)
            
            if symbol == "USDCEUR" or symbol == "USDCUSDT":
                return [
                    order_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'FIAT',
                    symbol,
                    'BUY',
                    'N/A',
                    'N/A',
                    f"{quantity:.2f}",
                    f"{quantity:.2f}",
                    '0',
                    order['status'],
                    'N/A',
                    'N/A'
                ]
            else:
                return [
                    order_time.strftime('%Y-%m-%d %H:%M:%S'),
                    order['type'],
                    symbol,
                    order['side'],
                    f"{price:.8f}" if price > 0 else "MARKET",
                    f"{current_price:.8f}" if current_price else "N/A",
                    f"{quantity:.8f}",
                    f"{executed:.8f}",
                    f"{remaining:.8f}",
                    order['status'],
                    f"{total_value:.2f}",
                    f"{profit_loss:.2f}%" if profit_loss is not None else "N/A"
                ]
        except Exception as e:
            if self.verbose:
                print(f"Error formatting order for table: {e}")
                print(f"Order data: {order}")
            return None

    def print_orders_table(self, orders):
        headers = [
            'Time',
            'Type',
            'Pair',
            'Side',
            'Price',
            'Current Price',
            'Amount',
            'Filled',
            'Remaining',
            'Status',
            'Total Value',
            'Profit/Loss'
        ]
        
        table_data = []
        for order in orders:
            row = self.format_order_for_table(order)
            if row:
                table_data.append(row)
        
        if table_data:
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            print("No orders to display")

    def get_pending_orders(self, side=None):
        try:
            if self.verbose:
                print("Fetching pending orders...")
            
            # Get TRUMP/USDC orders
            trump_orders = self.client.get_open_orders(symbol="TRUMPUSDC")
            
            # Filter by side if specified
            filtered_orders = [order for order in trump_orders if not side or order['side'] == side.upper()]
            
            if not filtered_orders:
                print(f"No pending {'buy' if side == 'BUY' else 'sell' if side == 'SELL' else ''} orders for TRUMP/USDC")
            else:
                print(f"Open TRUMP/USDC {'buy' if side == 'BUY' else 'sell' if side == 'SELL' else ''} orders:")
                if self.table_format:
                    self.print_orders_table(filtered_orders)
                else:
                    for order in filtered_orders:
                        self.print_order_details(order)
                
        except Exception as e:
            print(f"Error loading orders: {e}")

    def get_order_history(self, days=2):
        try:
            # Calculate start time
            start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            if self.verbose:
                print(f"Fetching order history since {datetime.fromtimestamp(start_time/1000)}")
            
            all_orders = []
            
            # Try to get TRUMP/USDC trading history using my trades
            try:
                if self.verbose:
                    print("Fetching TRUMP/USDC trades...")
                
                # Try my trades first
                trades = self.client.get_my_trades(symbol="TRUMPUSDC", limit=1000)
                if trades:
                    for trade in trades:
                        order = {
                            'symbol': trade['symbol'],
                            'orderId': trade['orderId'],
                            'price': trade['price'],
                            'origQty': trade['qty'],
                            'executedQty': trade['qty'],
                            'type': 'MARKET' if trade['isBuyer'] else 'LIMIT',
                            'side': 'BUY' if trade['isBuyer'] else 'SELL',
                            'status': 'FILLED',
                            'time': trade['time']
                        }
                        all_orders.append(order)
                    if self.verbose:
                        print(f"Found {len(trades)} TRUMP/USDC trades")
                
                # Also get current open orders
                open_orders = self.client.get_open_orders(symbol="TRUMPUSDC")
                if open_orders:
                    all_orders.extend(open_orders)
                    if self.verbose:
                        print(f"Found {len(open_orders)} open TRUMP/USDC orders")
                
            except Exception as e:
                if self.verbose:
                    print(f"Error fetching TRUMP/USDC trades: {e}")
            
            # Try to get USDC fiat purchase history
            try:
                if self.verbose:
                    print("Fetching fiat purchase history...")
                
                # Try both EUR and USDT pairs for fiat
                for fiat_pair in ['EUR', 'USDT']:
                    try:
                        trades = self.client.get_my_trades(symbol=f"USDC{fiat_pair}", limit=1000)
                        if trades:
                            for trade in trades:
                                order = {
                                    'symbol': f"USDC{fiat_pair}",
                                    'orderId': trade['orderId'],
                                    'price': trade['price'],
                                    'origQty': trade['qty'],
                                    'executedQty': trade['qty'],
                                    'type': 'FIAT',
                                    'side': 'BUY' if trade['isBuyer'] else 'SELL',
                                    'status': 'FILLED',
                                    'time': trade['time']
                                }
                                all_orders.append(order)
                    except Exception as e:
                        if self.verbose:
                            print(f"Error fetching USDC{fiat_pair} trades: {e}")
                            
            except Exception as e:
                if self.verbose:
                    print(f"Error fetching fiat orders: {e}")
            
            # Filter orders by time
            all_orders = [order for order in all_orders if int(order['time']) >= start_time]
            
            if not all_orders:
                print("No orders found in the specified time period.")
                if self.verbose:
                    print("Try increasing the number of days or check if you have any trades")
                return
            
            # Sort orders by time
            all_orders.sort(key=lambda x: x['time'], reverse=True)
            
            print(f"\nFound {len(all_orders)} orders in the last {days} days:")
            if self.table_format:
                self.print_orders_table(all_orders)
            else:
                for order in all_orders:
                    self.print_order_details(order)
                    print("-" * 80)  # Separator between orders
                
        except Exception as e:
            print(f"Error in order history: {e}")
            if self.verbose:
                print("Full error details:", str(e))

def main():
    parser = argparse.ArgumentParser(
        description='Binance Order Management Tool',
        epilog="""
Examples:
  # Show pending buy orders
  python binance_orders.py --buy_orders

  # Show pending sell orders
  python binance_orders.py --sell_orders

  # Show order history for last 5 days
  python binance_orders.py --orders_history 5

  # Show TRUMP/USDC price history (last 100 intervals of 5min)
  python binance_orders.py --token_history

  # Show BTC/USDC price history with custom parameters
  python binance_orders.py --token_history --pair BTCUSDC --interval 15m --limit 50

  # Get GPT trading recommendations (last 20 intervals)
  python binance_orders.py --token_history --gpt

  # Get GPT analysis with full dataset using GPT-4 Turbo
  python binance_orders.py --token_history --gpt --full-data --gpt-model gpt4-turbo

  # Get concise buy/sell orders only using different models
  python binance_orders.py --token_history --gpt --concise --gpt-model gpt4o
  python binance_orders.py --token_history --gpt --concise --gpt-model o1

  # Export price history as JSON
  python binance_orders.py --token_history --json

  # Export custom data range as JSON
  python binance_orders.py --token_history --pair BTCUSDC --interval 1h --limit 24 --json

  # Show all data in table format with verbose output
  python binance_orders.py --token_history --table --verbose
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--sell_orders', action='store_true', help='Show only pending sell orders')
    group.add_argument('--buy_orders', action='store_true', help='Show only pending buy orders')
    group.add_argument('--orders_history', type=int, nargs='?', const=2, metavar='DAYS',
                      help='Show order history for the last X days (default: 2)')
    group.add_argument('--token_history', action='store_true',
                      help='Show token price history')
    
    # New parameters
    parser.add_argument('--pair', type=str, default="TRUMPUSDC",
                      help='Trading pair symbol (default: TRUMPUSDC)')
    parser.add_argument('--interval', type=str, default="5m",
                      help=f'Time interval (default: 5m). Valid intervals: {", ".join(VALID_INTERVALS)}')
    parser.add_argument('--limit', type=int, default=100,
                      help='Number of historical records to fetch (default: 100)')
    parser.add_argument('--gpt', action='store_true',
                      help='Get trading recommendations from GPT')
    parser.add_argument('--full-data', action='store_true',
                      help='Send full dataset to GPT instead of last 20 records (only works with --gpt)')
    parser.add_argument('--json', action='store_true',
                      help='Export data in JSON format')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Show detailed processing information')
    parser.add_argument('--table', action='store_true',
                      help='Display results in table format')
    parser.add_argument('--gpt-model', type=str, choices=list(GPT_MODELS.keys()), default='gpt4o-mini',
                      help='GPT model to use for analysis (default: gpt4o-mini)')
    parser.add_argument('--concise', action='store_true',
                      help='Show only buy/sell orders without detailed analysis')

    args = parser.parse_args()

    try:
        manager = BinanceOrderManager(verbose=args.verbose, table_format=args.table)
        
        if args.sell_orders:
            manager.get_pending_orders(side='SELL')
        elif args.buy_orders:
            manager.get_pending_orders(side='BUY')
        elif args.orders_history is not None:
            manager.get_order_history(days=args.orders_history)
        elif args.token_history:
            manager.get_token_history(
                symbol=args.pair,
                interval=args.interval,
                limit=args.limit,
                gpt_analysis=args.gpt,
                full_data=args.full_data,
                json_output=args.json,
                gpt_model=args.gpt_model,
                concise=args.concise
            )
        else:
            parser.print_help()
            
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main() 