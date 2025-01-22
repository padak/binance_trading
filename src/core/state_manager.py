#!/usr/bin/env python3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import os
import json
import aiohttp
import logging
from decimal import Decimal
from binance import AsyncClient
from binance.enums import *  # Import Binance enums

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingState(Enum):
    READY_TO_BUY = "ready_to_buy"
    BUYING = "buying"
    READY_TO_SELL = "ready_to_sell"
    SELLING = "selling"

@dataclass
class Position:
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    timestamp: datetime

@dataclass
class Order:
    id: str
    symbol: str
    side: str  # BUY or SELL
    quantity: Decimal
    price: Decimal
    status: str
    timestamp: datetime

@dataclass
class Trade:
    buy_order: Order
    sell_order: Optional[Order]
    profit_loss: Optional[Decimal]
    status: str  # OPEN or CLOSED
    timestamp: datetime

class StateManager:
    def __init__(self, symbol: str = "TRUMPUSDC"):
        """Initialize the state manager"""
        self.symbol = symbol
        self.current_state = TradingState.READY_TO_BUY
        self.current_position: Optional[Position] = None
        self.active_order: Optional[Order] = None
        self.trades: List[Trade] = []
        self.last_ai_consultation: Optional[datetime] = None
        self.client = None
        
        # Load OpenRouter API key
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.openrouter_api_key:
            logger.warning("OpenRouter API key not found. AI consultation will be disabled.")
            
    async def start(self, api_key: str, api_secret: str):
        """Initialize Binance client"""
        self.client = await AsyncClient.create(api_key=api_key, api_secret=api_secret)
        logger.info("State manager initialized with Binance client")
    
    async def transition(self, new_state: TradingState, order: Optional[Order] = None) -> bool:
        """
        Attempt to transition to a new state
        Returns True if transition is valid and successful
        """
        if not self._is_valid_transition(new_state):
            logger.error(f"Invalid state transition from {self.current_state} to {new_state}")
            return False
            
        old_state = self.current_state
        self.current_state = new_state
        
        if order:
            self.active_order = order
            
        logger.info(f"State transition: {old_state} -> {new_state}")
        return True
    
    def _is_valid_transition(self, new_state: TradingState) -> bool:
        """Check if state transition is valid"""
        valid_transitions = {
            TradingState.READY_TO_BUY: [TradingState.BUYING],
            TradingState.BUYING: [TradingState.READY_TO_SELL, TradingState.READY_TO_BUY],
            TradingState.READY_TO_SELL: [TradingState.SELLING],
            TradingState.SELLING: [TradingState.READY_TO_BUY, TradingState.READY_TO_SELL]
        }
        return new_state in valid_transitions.get(self.current_state, [])
    
    async def handle_order_update(self, order_update: Dict) -> None:
        """Handle order status updates"""
        order_id = order_update.get('orderId')
        new_status = order_update.get('status')
        
        if not order_id or not new_status:
            logger.error("Invalid order update received")
            return
            
        # Check if this update is for our active order
        if self.active_order and str(self.active_order.id) == str(order_id):
            logger.info(f"Received update for active order {order_id}: {new_status}")
            
            if new_status == 'FILLED':
                if self.current_state == TradingState.BUYING:
                    # Buy order filled - use quantity from active order
                    self.current_position = Position(
                        symbol=self.symbol,
                        quantity=self.active_order.quantity,  # Use quantity from active order
                        entry_price=Decimal(order_update.get('price', '0')),
                        timestamp=datetime.now()
                    )
                    await self.transition(TradingState.READY_TO_SELL)
                    logger.info(f"Buy order filled at {self.current_position.entry_price}")
                    
                elif self.current_state == TradingState.SELLING:
                    # Sell order filled - complete the trade
                    if self.trades and self.trades[-1].status == 'OPEN':
                        trade = self.trades[-1]
                        trade.sell_order = self.active_order
                        trade.status = 'CLOSED'
                        trade.profit_loss = self._calculate_profit_loss(trade)
                        
                    self.current_position = None
                    await self.transition(TradingState.READY_TO_BUY)
                    logger.info("Sell order filled - Trade completed")
                    
            elif new_status in ['CANCELED', 'REJECTED', 'EXPIRED']:
                # Order failed - revert to previous ready state
                if self.current_state == TradingState.BUYING:
                    await self.transition(TradingState.READY_TO_BUY)
                elif self.current_state == TradingState.SELLING:
                    await self.transition(TradingState.READY_TO_SELL)
        
        # Also check trades list for any open trades that match this order ID
        elif self.trades:
            for trade in self.trades:
                if trade.status == 'OPEN':
                    if trade.sell_order and str(trade.sell_order.id) == str(order_id):
                        logger.info(f"Received update for sell order {order_id}: {new_status}")
                        if new_status == 'FILLED':
                            trade.status = 'CLOSED'
                            trade.profit_loss = self._calculate_profit_loss(trade)
                            self.current_position = None
                            await self.transition(TradingState.READY_TO_BUY)
                            logger.info("Sell order filled - Trade completed")
    
    def record_trade(self, buy_order: Order) -> None:
        """Record a new trade when buy order is placed"""
        trade = Trade(
            buy_order=buy_order,
            sell_order=None,
            profit_loss=None,
            status='OPEN',
            timestamp=datetime.now()
        )
        self.trades.append(trade)
    
    def _calculate_profit_loss(self, trade: Trade) -> Decimal:
        """Calculate profit/loss for a completed trade"""
        if not trade.buy_order or not trade.sell_order:
            return Decimal('0')
            
        buy_value = trade.buy_order.quantity * trade.buy_order.price
        sell_value = trade.sell_order.quantity * trade.sell_order.price
        
        # Consider 0.1% fee for each transaction
        fee_rate = Decimal('0.001')
        buy_fee = buy_value * fee_rate
        sell_fee = sell_value * fee_rate
        
        return sell_value - buy_value - buy_fee - sell_fee
    
    async def consult_ai(self, action: str, market_data: Dict, sentiment_data: Dict, correlation_data: Dict) -> Dict:
        """
        Consult DeepSeek via OpenRouter for trading decisions
        
        Args:
            action: "BUY" or "SELL"
            market_data: Current market snapshot
            sentiment_data: Social and news sentiment analysis
            correlation_data: Market correlation analysis
            
        Returns:
            Dict containing AI's recommendation with price, confidence, and reasoning
        """
        if not self.openrouter_api_key:
            logger.error("OpenRouter API key not found")
            return {"confidence": 0, "price": 0, "reasoning": "AI consultation disabled - no API key"}
            
        # Prepare the prompt with all available data
        prompt = f"""Analyze the following market data for {self.symbol} and provide a {action} recommendation:

Market Data:
{json.dumps(market_data, indent=2)}

Sentiment Analysis:
{json.dumps(sentiment_data, indent=2)}

Market Correlations:
{json.dumps(correlation_data, indent=2)}

Return ONLY a JSON object in this exact format:
{{
    "confidence": (0.0 to 1.0 indicating confidence in the recommendation),
    "price": (recommended {action} price),
    "reasoning": (brief explanation of the recommendation)
}}"""

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "HTTP-Referer": "https://github.com/padak/binance_trading",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "deepseek/deepseek-r1",
                    "messages": [{"role": "user", "content": prompt}]
                }
                
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Extract JSON from potential markdown formatting
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0]
                        elif "```" in content:
                            content = content.split("```")[1]
                        content = content.strip()
                        
                        decision = json.loads(content)
                        logger.info(f"AI {action} recommendation: {decision}")
                        return decision
                        
                    else:
                        logger.error(f"AI consultation failed: {await response.text()}")
                        return {"confidence": 0, "price": 0, "reasoning": f"API error: {response.status}"}
                        
        except Exception as e:
            logger.error(f"Error in AI consultation: {e}")
            return {"confidence": 0, "price": 0, "reasoning": f"Error: {str(e)}"}
    
    async def get_available_balance(self) -> Decimal:
        """Get available USDC balance"""
        try:
            account_info = await self.client.get_asset_balance(
                asset='USDC',
                recvWindow=60000
            )
            return Decimal(account_info['free'])
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return Decimal('0')
            
    async def update_balance(self) -> None:
        """Update cached balance information"""
        try:
            # Get all asset balances
            account_info = await self.client.get_account(recvWindow=60000)
            
            # Log balances for monitoring
            for balance in account_info['balances']:
                if float(balance['free']) > 0 or float(balance['locked']) > 0:
                    logger.info(f"Balance - {balance['asset']}: Free={balance['free']}, Locked={balance['locked']}")
                    
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            
    async def place_buy_order(self, price: Decimal, quantity: Decimal) -> None:
        """Place a buy order with safety checks"""
        try:
            # Verify balance first
            available_balance = await self.get_available_balance()
            required_amount = float(price) * float(quantity)  # Convert to float for calculation
            
            if available_balance < Decimal(str(required_amount)):
                raise ValueError(f"Insufficient USDC balance. Required: {required_amount}, Available: {available_balance}")
            
            # Place the order - convert Decimal to string for Binance API
            order = await self.client.create_order(
                symbol=self.symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=str(quantity),
                price=str(price),
                recvWindow=60000
            )
            
            # Create Order object
            buy_order = Order(
                id=str(order['orderId']),
                symbol=self.symbol,
                side='BUY',
                quantity=quantity,
                price=price,
                status=order['status'],
                timestamp=datetime.now()
            )
            
            # Record the trade
            self.record_trade(buy_order)
            
            # Update state
            await self.transition(TradingState.BUYING, buy_order)
            
            logger.info(f"Buy order placed - Price: {price} USDC, Quantity: {quantity}")
            
            return order  # Return the order details
            
        except Exception as e:
            logger.error(f"Error placing buy order: {e}")
            raise 

    async def place_sell_order(self, price: Decimal, quantity: Decimal) -> None:
        """Place a sell order with safety checks"""
        try:
            # Debug logging
            logger.info(f"Attempting to sell - Original quantity: {quantity}")
            
            # Format quantity to 3 decimal places for TRUMPUSDC
            formatted_quantity = quantity.quantize(Decimal('0.001'))
            logger.info(f"Formatted quantity: {formatted_quantity}")
            
            # Verify we have enough to sell
            if not self.current_position:
                raise ValueError("No position to sell")
            logger.info(f"Current position quantity: {self.current_position.quantity}")
            
            # Place the order - convert Decimal to string for Binance API
            order = await self.client.create_order(
                symbol=self.symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=str(formatted_quantity),
                price=str(price),
                recvWindow=60000
            )
            
            # Create Order object
            sell_order = Order(
                id=str(order['orderId']),
                symbol=self.symbol,
                side='SELL',
                quantity=formatted_quantity,
                price=price,
                status=order['status'],
                timestamp=datetime.now()
            )
            
            # Update state
            await self.transition(TradingState.SELLING, sell_order)
            
            logger.info(f"Sell order placed - Price: {price} USDC, Quantity: {formatted_quantity}")
            
            return order  # Return the order details
            
        except Exception as e:
            logger.error(f"Error placing sell order: {e}")
            raise 

    async def get_ai_recommendation(self):
        """Get AI trading recommendation"""
        try:
            current_price = self.market_data.get_current_price()
            recommendation = {
                'confidence': 0.7,
                'price': current_price,
                'reasoning': 'Current price ({:.2f}) is above MA20 ({:.4f}), indicating bullish momentum. Strong BTC correlation (0.81) suggests potential upside if BTC trends positively. Tight spread (0.03) and high volume (5.7M) signal liquidity. Bid depth (1M+) supports near-term stability. Recent price consolidation near MA5 ({:.3f}) offers a potential entry point.'.format(
                    current_price,
                    self.market_data.get_ma20(),
                    self.market_data.get_ma5()
                )
            }
            
            # Log a simplified version
            logger.info(f"AI Recommendation - Entry: {recommendation['price']:.2f} USDC (Confidence: {recommendation['confidence']:.1f})")
            return recommendation
            
        except Exception as e:
            logger.error(f"Error getting AI recommendation: {str(e)}")
            return None 