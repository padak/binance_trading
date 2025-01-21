#!/usr/bin/env python3
"""Simple script to check trading rules for TRUMPUSDC pair"""

import asyncio
import os
from binance import AsyncClient
from dotenv import load_dotenv

async def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize client
    client = await AsyncClient.create(
        os.getenv("BINANCE_TRADE_API_KEY"),
        os.getenv("BINANCE_TRADE_API_SECRET")
    )
    
    try:
        # Get exchange info
        exchange_info = await client.get_exchange_info()
        
        # Find TRUMPUSDC symbol info
        for symbol in exchange_info['symbols']:
            if symbol['symbol'] == 'TRUMPUSDC':
                print('\nTrading rules for TRUMPUSDC:')
                print('Status:', symbol['status'])
                print('\nFilters:')
                for f in symbol['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        print('\nLOT_SIZE Filter:')
                        print('  Minimum Quantity:', f['minQty'])
                        print('  Maximum Quantity:', f['maxQty'])
                        print('  Step Size:', f['stepSize'])
                    elif f['filterType'] == 'PRICE_FILTER':
                        print('\nPRICE_FILTER:')
                        print('  Minimum Price:', f['minPrice'])
                        print('  Maximum Price:', f['maxPrice'])
                        print('  Tick Size:', f['tickSize'])
                    elif f['filterType'] == 'MIN_NOTIONAL':
                        print('\nMIN_NOTIONAL:')
                        print('  Minimum Order Value:', f['minNotional'], 'USDC')
                break
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(main()) 