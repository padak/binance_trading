#!/usr/bin/env python3
import os
import time
from dotenv import load_dotenv
from services.market_data import MarketDataService

def main():
    # Load environment variables
    load_dotenv()
    
    # Get API keys from environment
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("Error: Please set BINANCE_API_KEY and BINANCE_API_SECRET in your .env file")
        return
    
    # Initialize market data service
    market_data = MarketDataService(symbol="TRUMPUSDC")
    
    try:
        # Start the service
        print("\nStarting Market Data Service for TRUMP/USDC...")
        market_data.start(api_key=api_key, api_secret=api_secret)
        
        # Main loop to display data
        while True:
            snapshot = market_data.get_market_snapshot()
            
            # Clear screen (Unix/Linux/MacOS)
            os.system('clear')
            
            print("\n=== TRUMP/USDC Market Data ===")
            print(f"\nTimestamp: {snapshot['metadata']['timestamp']}")
            
            # Current price and indicators
            print("\n--- Price & Indicators ---")
            print(f"Current Price: {snapshot['market_state']['current_price']}")
            indicators = snapshot['market_state']['technical_indicators']
            print(f"MA5: {indicators['ma5']}")
            print(f"MA20: {indicators['ma20']}")
            print(f"VWAP: {indicators['vwap']}")
            
            # Order book information
            print("\n--- Order Book ---")
            volume = snapshot['market_state']['volume_profile']
            print(f"Bid Volume: {volume['bid_volume']:.2f}")
            print(f"Ask Volume: {volume['ask_volume']:.2f}")
            print(f"Imbalance: {snapshot['market_state']['order_book_imbalance']:.4f}")
            
            # Entry prices
            print("\n--- Suggested Entry Prices ---")
            entry_prices = market_data.get_optimal_entry_levels(10)  # 10 USDC
            for i, price in enumerate(entry_prices, 1):
                print(f"Level {i}: {price:.2f} USDC")
            
            print("\nPress Ctrl+C to exit")
            time.sleep(1)  # Update every second
            
    except KeyboardInterrupt:
        print("\nStopping Market Data Service...")
    finally:
        market_data.stop()
        print("Service stopped.")

if __name__ == "__main__":
    main() 