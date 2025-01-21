#!/usr/bin/env python3
import os
import asyncio
from dotenv import load_dotenv
from services.market_data import MarketDataService

async def print_market_data(snapshot):
    """Print formatted market data"""
    print("\n=== TRUMP/USDC Market Data ===")
    print(f"\nCurrent Price: {snapshot.get('price', 'N/A')} USDC")
    
    print("\nOrder Book:")
    print(f"Best Bid: {snapshot.get('best_bid', 'N/A')} USDC")
    print(f"Best Ask: {snapshot.get('best_ask', 'N/A')} USDC")
    print(f"Bid Volume: {snapshot.get('bid_volume', 0):.2f}")
    print(f"Ask Volume: {snapshot.get('ask_volume', 0):.2f}")
    
    print("\nTechnical Indicators:")
    print(f"MA5: {snapshot.get('ma5', 'N/A')}")
    print(f"MA20: {snapshot.get('ma20', 'N/A')}")
    print(f"VWAP: {snapshot.get('vwap', 'N/A')}")
    
    print("\nLiquidity Metrics:")
    print(f"Spread: {snapshot.get('spread', 'N/A')}")
    print(f"Bid Depth: {snapshot.get('bid_depth', 'N/A')}")
    print(f"Ask Depth: {snapshot.get('ask_depth', 'N/A')}")
    print(f"Cancel Rate: {snapshot.get('cancel_rate', 'N/A')}")

async def main():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("Error: Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file")
        return
    
    # Initialize market data service
    market_data = MarketDataService("TRUMPUSDC")
    
    try:
        # Start the service
        await market_data.start(api_key, api_secret)
        
        # Wait for initial data collection
        print("Waiting for initial data collection...")
        await asyncio.sleep(5)
        
        # Get and print market snapshot
        snapshot = await market_data.get_market_snapshot()
        await print_market_data(snapshot)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        await market_data.stop()
        print("\nService stopped.")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 