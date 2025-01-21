#!/usr/bin/env python3
import os
import asyncio
import time
from dotenv import load_dotenv
from decimal import Decimal
from datetime import datetime
from core.state_manager import StateManager, TradingState, Order
from services.market_data import MarketDataService
import json
import logging

# Set logging level to WARNING to reduce verbosity
logging.getLogger().setLevel(logging.WARNING)

async def run_test():
    """Main test logic separated from WebSocket initialization"""
    state_manager = StateManager(symbol="TRUMPUSDC")
    
    try:
        print("\nStarting State Manager Test...")
        print("\nInitial State:", state_manager.current_state)
        
        # Simulate a buy order placement
        buy_order = Order(
            id="123",
            symbol="TRUMPUSDC",
            side="BUY",
            quantity=Decimal("0.25"),
            price=Decimal("40.00"),
            status="NEW",
            timestamp=datetime.now()
        )
        
        # Transition to BUYING state
        print("\nPlacing buy order...")
        await state_manager.transition(TradingState.BUYING, buy_order)
        print("Current State:", state_manager.current_state)
        
        # Record the trade
        state_manager.record_trade(buy_order)
        print("Trade recorded. Open trades:", len(state_manager.trades))
        
        # Simulate order fill
        print("\nSimulating buy order fill...")
        await state_manager.handle_order_update({
            'orderId': "123",
            'status': 'FILLED',
            'quantity': "0.25",
            'price': "40.00"
        })
        print("Current State:", state_manager.current_state)
        
        # Create mock market data for AI consultation
        print("\nConsulting AI for sell price...")
        mock_market_data = {
            'price': 40.25,
            'volume': 1000000,
            'best_bid': 40.20,
            'best_ask': 40.30,
            'ma5': 40.15,
            'ma20': 39.95
        }
        
        mock_correlation_data = {
            'btc_correlation': 0.8
        }
        
        # Consult AI
        ai_advice = await state_manager.consult_ai(
            "SELL",
            mock_market_data,
            None,  # Skip sentiment data
            mock_correlation_data
        )
        
        print("\nAI Recommendation:")
        print(json.dumps(ai_advice, indent=2))
        
        # Simulate sell order
        if ai_advice and ai_advice.get('price', 0) > 0:
            sell_price = Decimal(str(ai_advice['price']))
        else:
            sell_price = Decimal('41.00')  # Default 2.5% profit target
            
        sell_order = Order(
            id="124",
            symbol="TRUMPUSDC",
            side="SELL",
            quantity=Decimal("0.25"),
            price=sell_price,
            status="NEW",
            timestamp=datetime.now()
        )
        
        # Transition to SELLING state
        print("\nPlacing sell order...")
        await state_manager.transition(TradingState.SELLING, sell_order)
        print("Current State:", state_manager.current_state)
        
        # Simulate sell order fill
        print("\nSimulating sell order fill...")
        await state_manager.handle_order_update({
            'orderId': "124",
            'status': 'FILLED',
            'quantity': "0.25",
            'price': str(sell_price)
        })
        print("Current State:", state_manager.current_state)
        
        # Print trade results
        if state_manager.trades:
            last_trade = state_manager.trades[-1]
            print("\nTrade Summary:")
            print(f"Buy Price: {last_trade.buy_order.price}")
            print(f"Sell Price: {last_trade.sell_order.price}")
            print(f"Profit/Loss: {last_trade.profit_loss} USDC")
            print(f"Status: {last_trade.status}")
            
    except Exception as e:
        print("\nError during test:", e)
    finally:
        print("\nTest completed.")

def main():
    # Load environment variables
    load_dotenv()
    
    # Run the async test
    asyncio.run(run_test())

if __name__ == "__main__":
    main() 