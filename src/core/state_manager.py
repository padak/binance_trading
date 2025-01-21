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
        from binance import AsyncClient
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
            
        if self.active_order and str(self.active_order.id) == str(order_id):
            if new_status == 'FILLED':
                if self.current_state == TradingState.BUYING:
                    # Buy order filled
                    self.current_position = Position(
                        symbol=self.symbol,
                        quantity=Decimal(order_update.get('quantity', '0')),
                        entry_price=Decimal(order_update.get('price', '0')),
                        timestamp=datetime.now()
                    )
                    await self.transition(TradingState.READY_TO_SELL)
                    
                elif self.current_state == TradingState.SELLING:
                    # Sell order filled - complete the trade
                    if self.trades and self.trades[-1].status == 'OPEN':
                        trade = self.trades[-1]
                        trade.sell_order = self.active_order
                        trade.status = 'CLOSED'
                        trade.profit_loss = self._calculate_profit_loss(trade)
                        
                    self.current_position = None
                    await self.transition(TradingState.READY_TO_BUY)
                    
            elif new_status in ['CANCELED', 'REJECTED', 'EXPIRED']:
                # Order failed - revert to previous ready state
                if self.current_state == TradingState.BUYING:
                    await self.transition(TradingState.READY_TO_BUY)
                elif self.current_state == TradingState.SELLING:
                    await self.transition(TradingState.READY_TO_SELL)
    
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
    
    async def consult_ai(self, market_data: Dict) -> Dict:
        """
        Consult DeepSeek via OpenRouter for trading decisions
        """
        if not self.openrouter_api_key:
            logger.error("OpenRouter API key not found")
            return {}
            
        # Prepare the prompt with market data
        prompt = self._prepare_ai_prompt(market_data)
        logger.info(f"Sending prompt to AI: {prompt}")
        
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
                logger.info(f"Request headers: {headers}")
                logger.info(f"Request payload: {payload}")
                
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    response_text = await response.text()
                    logger.info(f"Response status: {response.status}")
                    logger.info(f"Response body: {response_text}")
                    
                    if response.status == 200:
                        result = await response.json()
                        parsed_result = self._parse_ai_response(result)
                        logger.info(f"Parsed AI response: {parsed_result}")
                        return parsed_result
                    else:
                        logger.error(f"AI consultation failed: {response_text}")
                        return {}
                        
        except Exception as e:
            logger.error(f"Error during AI consultation: {str(e)}")
            return {}
    
    def _prepare_ai_prompt(self, market_data: Dict) -> str:
        """Prepare prompt for AI consultation with enhanced market context"""
        return f"""
        Analyze the following market data for {self.symbol} and suggest optimal buy/sell prices.
        Current state: {self.current_state.value}
        
        Market Data:
        {json.dumps(market_data, indent=2)}
        
        Historical Context:
        - Price History (last 24h):
          * High: {market_data.get('historical', {}).get('24h_high', 'N/A')}
          * Low: {market_data.get('historical', {}).get('24h_low', 'N/A')}
          * Volume: {market_data.get('historical', {}).get('24h_volume', 'N/A')}
        - Recent Trades (last 100):
          * Average Price: {market_data.get('historical', {}).get('avg_price', 'N/A')}
          * Price Volatility: {market_data.get('historical', {}).get('volatility', 'N/A')}
        - Market Sentiment:
          * Buy/Sell Ratio: {market_data.get('sentiment', {}).get('buy_sell_ratio', 'N/A')}
          * Large Orders (>1000 USDC): {market_data.get('sentiment', {}).get('large_orders', 'N/A')}
        
        Consider:
        1. Price trends and volatility patterns over the last 24 hours
        2. Current order book depth and imbalance
        3. Technical indicators (MA5, MA20, VWAP)
        4. Market sentiment from recent large orders
        5. Trading fees (0.1% per trade)
        6. Historical support/resistance levels
        
        Respond in JSON format with:
        {{
            "action": "buy" or "sell",
            "base_price": suggested base price,
            "price_range": [min_price, max_price],
            "confidence": 0.0 to 1.0,
            "reasoning": "detailed explanation including historical context"
        }}
        """
    
    def _parse_ai_response(self, response: Dict) -> Dict:
        """Parse and validate AI response"""
        try:
            content = response['choices'][0]['message']['content']
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]  # Remove ```json
            if content.endswith('```'):
                content = content[:-3]  # Remove ```
            content = content.strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return {} 

    async def get_available_balance(self) -> Decimal:
        """Get available USDC balance"""
        try:
            account_info = await self.client.get_asset_balance(asset='USDC')
            return Decimal(account_info['free'])
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return Decimal('0')
            
    async def update_balance(self) -> None:
        """Update cached balance information"""
        try:
            # Get all asset balances
            account_info = await self.client.get_account()
            
            # Log balances for monitoring
            for balance in account_info['balances']:
                if float(balance['free']) > 0 or float(balance['locked']) > 0:
                    logger.info(f"Balance - {balance['asset']}: Free={balance['free']}, Locked={balance['locked']}")
                    
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            
    async def place_buy_order(self, price: Decimal, quantity: Decimal, 
                            stop_loss: Decimal, take_profit: Decimal) -> None:
        """Place a buy order with safety checks"""
        try:
            # Verify balance first
            available_balance = await self.get_available_balance()
            required_amount = price * quantity
            
            if available_balance < required_amount:
                raise ValueError(f"Insufficient USDC balance. Required: {required_amount}, Available: {available_balance}")
            
            # Place the order
            order = await self.client.create_order(
                symbol=self.symbol,
                side='BUY',
                type='LIMIT',
                timeInForce='GTC',
                quantity=str(quantity),
                price=str(price)
            )
            
            # Record the order and update state
            await self.handle_order_update({
                'orderId': order['orderId'],
                'status': 'NEW',
                'price': str(price),
                'quantity': str(quantity)
            })
            
            logger.info(f"Buy order placed - Price: {price} USDC, Quantity: {quantity}")
            
        except Exception as e:
            logger.error(f"Error placing buy order: {e}")
            raise 