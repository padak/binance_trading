#!/usr/bin/env python3
"""
Script to list filled spot orders and calculate profit between selected BUY and SELL orders.
"""

import os
from decimal import Decimal
from datetime import datetime, timedelta
from binance.client import Client
from dotenv import load_dotenv
import logging
from tabulate import tabulate

# Configure logging - only show INFO and above
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Only show the message without timestamp and level
)
logger = logging.getLogger(__name__)

def read_env_file(path):
    """Read key-value pairs from .env file"""
    env_vars = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

# Get API keys from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if not os.path.isfile(env_path):
    raise ValueError(f".env file not found at {env_path}")

env_vars = read_env_file(env_path)
API_KEY = env_vars.get('BINANCE_API_KEY')
API_SECRET = env_vars.get('BINANCE_API_SECRET')

if not API_KEY or not API_SECRET:
    raise ValueError("API keys not found in .env file")

class OrderAnalyzer:
    def __init__(self):
        self.api_key = API_KEY
        self.api_secret = API_SECRET
        self.fee_rate = Decimal('0.001')  # 0.1% trading fee
        self.client = Client(api_key=self.api_key, api_secret=self.api_secret)

    def get_filled_orders(self, symbol: str = "TRUMPUSDC", days: int = 30):
        """Get all filled orders for the specified symbol and time period"""
        try:
            start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            trades = self.client.get_my_trades(symbol=symbol)
            
            buy_orders = []
            sell_orders = []
            
            for trade in trades:
                if int(trade['time']) < start_time:
                    continue
                    
                order = {
                    'orderId': trade['orderId'],
                    'time': datetime.fromtimestamp(int(trade['time'])/1000).strftime('%Y-%m-%d %H:%M:%S'),
                    'price': Decimal(trade['price']),
                    'quantity': Decimal(trade['qty']),
                    'commission': Decimal(trade['commission']),
                    'total': Decimal(trade['price']) * Decimal(trade['qty']),
                    'commission_asset': trade['commissionAsset']
                }
                
                if trade['isBuyer']:
                    buy_orders.append(order)
                else:
                    sell_orders.append(order)
            
            return buy_orders, sell_orders
            
        except Exception as e:
            logger.error(f"Error fetching orders: {str(e)}")
            raise

    def print_orders(self, orders, order_type: str):
        """Print orders in a formatted table"""
        if not orders:
            print(f"\nNo {order_type} orders found")
            return
            
        table_data = []
        for i, order in enumerate(orders, 1):
            table_data.append([
                i,  # Index for selection
                order['orderId'],
                order['time'],
                f"{order['price']:.8f}",
                f"{order['quantity']:.8f}",
                f"{order['total']:.8f}",
                f"{order['commission']:.8f} {order['commission_asset']}"
            ])
            
        headers = ['#', 'Order ID', 'Time', 'Price', 'Quantity', 'Total', 'Fee']
        print(f"\n{order_type} Orders:")
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
    def calculate_profit(self, buy_order, sell_order):
        """Calculate profit/loss including fees"""
        # Calculate costs
        buy_cost = buy_order['total']
        buy_fee = buy_order['commission']
        if buy_order['commission_asset'] != 'USDC':
            buy_fee = buy_fee * buy_order['price']
            
        # Calculate revenue
        sell_revenue = sell_order['total']
        sell_fee = sell_order['commission']
        if sell_order['commission_asset'] != 'USDC':
            sell_fee = sell_fee * sell_order['price']
            
        # Calculate total profit/loss
        total_fees = buy_fee + sell_fee
        gross_profit = sell_revenue - buy_cost
        net_profit = gross_profit - total_fees
        roi_percentage = (net_profit / buy_cost) * 100
        
        # Print results
        print("\nProfit Calculation:")
        print(f"Buy Price: {buy_order['price']:.8f} USDC")
        print(f"Sell Price: {sell_order['price']:.8f} USDC")
        print(f"Quantity: {buy_order['quantity']:.8f}")
        print(f"Buy Cost: {buy_cost:.8f} USDC")
        print(f"Sell Revenue: {sell_revenue:.8f} USDC")
        print(f"Buy Fee: {buy_fee:.8f} USDC")
        print(f"Sell Fee: {sell_fee:.8f} USDC")
        print(f"Total Fees: {total_fees:.8f} USDC")
        print(f"Gross Profit: {gross_profit:.8f} USDC")
        print(f"Net Profit: {net_profit:.8f} USDC")
        print(f"ROI: {roi_percentage:.2f}%")

def main():
    try:
        analyzer = OrderAnalyzer()
        
        # Get search method from user
        search_method = input("Search by (1) Time period or (2) Order IDs? Enter 1 or 2: ").strip()
        
        if search_method == "1":
            # Original time-based search
            symbol = input("Enter trading pair (default: TRUMPUSDC): ").strip() or "TRUMPUSDC"
            days = int(input("Enter number of days to look back (default: 30): ").strip() or "30")
            buy_orders, sell_orders = analyzer.get_filled_orders(symbol, days)
            
        elif search_method == "2":
            # Search by Order IDs
            symbol = input("Enter trading pair (default: TRUMPUSDC): ").strip() or "TRUMPUSDC"
            buy_order_id = input("Enter BUY Order ID: ").strip()
            sell_order_id = input("Enter SELL Order ID: ").strip()
            
            # Get all trades and filter by order IDs
            all_orders = analyzer.client.get_my_trades(symbol=symbol)
            
            buy_orders = []
            sell_orders = []
            
            for trade in all_orders:
                if str(trade['orderId']) == buy_order_id or str(trade['orderId']) == sell_order_id:
                    order = {
                        'orderId': trade['orderId'],
                        'time': datetime.fromtimestamp(int(trade['time'])/1000).strftime('%Y-%m-%d %H:%M:%S'),
                        'price': Decimal(trade['price']),
                        'quantity': Decimal(trade['qty']),
                        'commission': Decimal(trade['commission']),
                        'total': Decimal(trade['price']) * Decimal(trade['qty']),
                        'commission_asset': trade['commissionAsset']
                    }
                    
                    if str(trade['orderId']) == buy_order_id and trade['isBuyer']:
                        buy_orders.append(order)
                    elif str(trade['orderId']) == sell_order_id and not trade['isBuyer']:
                        sell_orders.append(order)
            
            if not buy_orders:
                print(f"\nBUY Order ID {buy_order_id} not found")
            if not sell_orders:
                print(f"\nSELL Order ID {sell_order_id} not found")
        else:
            raise ValueError("Invalid search method. Please enter 1 or 2.")
        
        # Print orders
        analyzer.print_orders(buy_orders, "BUY")
        analyzer.print_orders(sell_orders, "SELL")
        
        # Calculate profit if both orders are found
        if buy_orders and sell_orders:
            if search_method == "1":
                # For time-based search, let user select orders
                buy_idx = int(input("\nSelect BUY order number: ").strip()) - 1
                sell_idx = int(input("Select SELL order number: ").strip()) - 1
                
                if 0 <= buy_idx < len(buy_orders) and 0 <= sell_idx < len(sell_orders):
                    analyzer.calculate_profit(buy_orders[buy_idx], sell_orders[sell_idx])
                else:
                    print("\nInvalid order selection")
            else:
                # For Order ID search, calculate directly
                analyzer.calculate_profit(buy_orders[0], sell_orders[0])
        else:
            print("\nNot enough orders to calculate profit")
            
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main() 