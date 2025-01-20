import os
import argparse
from datetime import datetime, timedelta
from binance.client import Client
from dotenv import load_dotenv
from decimal import Decimal
from tabulate import tabulate

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

class BinanceOrderManager:
    def __init__(self, api_key=None, api_secret=None, verbose=False, table_format=False):
        self.api_key = api_key or API_KEY
        self.api_secret = api_secret or API_SECRET
        self.verbose = verbose
        self.table_format = table_format
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API keys are not set. Please set them in the .env file.")
        
        self.client = Client(api_key=self.api_key, api_secret=self.api_secret)

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
    parser = argparse.ArgumentParser(description='Binance Order Management Tool for TRUMP/USDC and USDC purchases')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--sell_orders', action='store_true', help='Show only pending sell orders')
    group.add_argument('--buy_orders', action='store_true', help='Show only pending buy orders')
    group.add_argument('--orders_history', type=int, nargs='?', const=2, metavar='DAYS',
                      help='Show order history for the last X days (default: 2)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed processing information')
    parser.add_argument('--table', action='store_true', help='Display results in table format')

    args = parser.parse_args()

    try:
        manager = BinanceOrderManager(verbose=args.verbose, table_format=args.table)
        
        if args.sell_orders:
            manager.get_pending_orders(side='SELL')
        elif args.buy_orders:
            manager.get_pending_orders(side='BUY')
        elif args.orders_history is not None:
            manager.get_order_history(days=args.orders_history)
        else:
            parser.print_help()
            
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main() 