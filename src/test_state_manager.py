#!/usr/bin/env python3
import os
import asyncio
from dotenv import load_dotenv
from decimal import Decimal
from datetime import datetime
from core.state_manager import StateManager, TradingState, Order
from services.market_data import MarketDataService
import json

async def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize services
    market_data = MarketDataService(symbol="TRUMPUSDC")
    state_manager = StateManager(symbol="TRUMPUSDC")
    
    # Start market data service
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    market_data.start(api_key=api_key, api_secret=api_secret)
    
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
        
        # Get market data and consult AI
        print("\nConsulting AI for sell price...")
        market_snapshot = market_data.get_market_snapshot()
        ai_advice = await state_manager.consult_ai(market_snapshot)
        print("\nAI Recommendation:")
        print(json.dumps(ai_advice, indent=2))
        
        # Simulate sell order
        if ai_advice:
            sell_price = Decimal(str(ai_advice.get('base_price', '41.00')))
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
        
    except KeyboardInterrupt:
        print("\nStopping test...")
    finally:
        market_data.stop()
        print("Test completed.")

if __name__ == "__main__":
    asyncio.run(main()) 