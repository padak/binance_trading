#!/usr/bin/env python3
from typing import Dict, List
import numpy as np
from datetime import datetime, timedelta
import logging
import aiohttp

logger = logging.getLogger(__name__)

class CorrelationAnalyzer:
    def __init__(self, client):
        self.client = client
        self.btc_symbol = "BTCUSDT"
        self.stablecoin_pairs = ["USDCUSDT", "BUSDUSDT"]
        
    async def get_correlation_data(self, symbol: str) -> Dict:
        """Get comprehensive correlation analysis"""
        try:
            return {
                "btc_correlation": await self._calculate_btc_correlation(symbol),
                "market_dominance": await self._get_btc_dominance(),
                "stablecoin_flows": await self._analyze_stablecoin_flows(),
                "market_trends": await self._analyze_market_trends()
            }
        except Exception as e:
            logger.error(f"Error getting correlation data: {e}")
            return {}
            
    async def _calculate_btc_correlation(self, symbol: str) -> Dict:
        """Calculate correlation with BTC"""
        try:
            # Get 24h of klines for both assets
            interval = '5m'  # 5-minute candles
            start_time = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
            
            # Get BTC klines
            btc_klines = await self.client.get_klines(
                symbol=self.btc_symbol,
                interval=interval,
                startTime=start_time
            )
            
            # Get target symbol klines
            symbol_klines = await self.client.get_klines(
                symbol=symbol,
                interval=interval,
                startTime=start_time
            )
            
            # Extract close prices
            btc_prices = [float(k[4]) for k in btc_klines]
            symbol_prices = [float(k[4]) for k in symbol_klines]
            
            # Calculate correlation
            correlation = np.corrcoef(btc_prices, symbol_prices)[0, 1]
            
            return {
                "coefficient": round(correlation, 2),
                "timeframe": "24h",
                "strength": self._interpret_correlation(correlation)
            }
        except Exception as e:
            logger.error(f"Error calculating BTC correlation: {e}")
            return {}
            
    async def _get_btc_dominance(self) -> Dict:
        """Get BTC market dominance metrics"""
        try:
            # Get global market data from CoinGecko
            async with aiohttp.ClientSession() as session:
                url = "https://api.coingecko.com/api/v3/global"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        dominance = data['data']['market_cap_percentage']['btc']
                        return {
                            "btc_dominance": round(dominance, 2),
                            "timestamp": datetime.now().isoformat()
                        }
            return {}
        except Exception as e:
            logger.error(f"Error getting BTC dominance: {e}")
            return {}
            
    async def _analyze_stablecoin_flows(self) -> Dict:
        """Analyze stablecoin flows"""
        try:
            flows = {}
            for pair in self.stablecoin_pairs:
                # Get 24h volume
                ticker = await self.client.get_ticker(symbol=pair)
                volume = float(ticker['volume'])
                price = float(ticker['lastPrice'])
                
                # Get net flow (positive = inflow, negative = outflow)
                trades = await self.client.get_recent_trades(symbol=pair, limit=1000)
                buy_volume = sum(float(t['qty']) for t in trades if t['isBuyerMaker'])
                sell_volume = sum(float(t['qty']) for t in trades if not t['isBuyerMaker'])
                net_flow = (buy_volume - sell_volume) * price
                
                flows[pair] = {
                    "volume_24h": volume,
                    "net_flow_24h": round(net_flow, 2)
                }
                
            return flows
        except Exception as e:
            logger.error(f"Error analyzing stablecoin flows: {e}")
            return {}
            
    async def _analyze_market_trends(self) -> Dict:
        """Analyze overall market trends"""
        try:
            # Get top 10 trading pairs by volume
            tickers = await self.client.get_ticker()
            sorted_tickers = sorted(tickers, key=lambda x: float(x['volume']), reverse=True)[:10]
            
            trends = {
                "top_gainers": [],
                "top_losers": [],
                "volume_leaders": []
            }
            
            for ticker in sorted_tickers:
                price_change = float(ticker['priceChangePercent'])
                volume = float(ticker['volume'])
                
                if price_change > 0:
                    trends['top_gainers'].append({
                        "symbol": ticker['symbol'],
                        "change": price_change
                    })
                else:
                    trends['top_losers'].append({
                        "symbol": ticker['symbol'],
                        "change": price_change
                    })
                    
                trends['volume_leaders'].append({
                    "symbol": ticker['symbol'],
                    "volume": volume
                })
                
            return trends
        except Exception as e:
            logger.error(f"Error analyzing market trends: {e}")
            return {}
            
    def _interpret_correlation(self, coefficient: float) -> str:
        """Interpret correlation coefficient"""
        abs_coef = abs(coefficient)
        if abs_coef > 0.7:
            return "strong"
        elif abs_coef > 0.4:
            return "moderate"
        else:
            return "weak" 