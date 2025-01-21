# Market Correlation Analysis

## Overview
The Correlation Analyzer provides insights into market relationships and trends by analyzing:
- BTC price correlation
- Market dominance metrics
- Stablecoin flows
- Overall market trends

## Features

### 1. BTC Correlation Analysis
Calculates correlation between any token and BTC price movements.

#### Metrics:
- Correlation coefficient (-1 to 1)
- Correlation strength (weak/moderate/strong)
- 24h timeframe analysis using 5-minute candles

#### Example Output:
```json
{
    "coefficient": 0.85,
    "timeframe": "24h",
    "strength": "strong"
}
```

### 2. Market Dominance
Tracks Bitcoin's market dominance and its impact on the market.

#### Features:
- Real-time BTC dominance percentage
- Historical dominance tracking
- Market cap analysis

#### Example Output:
```json
{
    "btc_dominance": 52.4,
    "timestamp": "2025-01-20T12:00:00"
}
```

### 3. Stablecoin Flow Analysis
Monitors stablecoin movements for market sentiment indicators.

#### Tracked Pairs:
- USDC/USDT
- BUSD/USDT

#### Metrics:
- 24h volume
- Net flow (inflow/outflow)
- Large transaction tracking

#### Example Output:
```json
{
    "USDCUSDT": {
        "volume_24h": 1000000.0,
        "net_flow_24h": 50000.0
    }
}
```

### 4. Market Trends
Analyzes overall market trends and momentum.

#### Features:
- Top gainers/losers tracking
- Volume leader analysis
- Market momentum indicators

#### Example Output:
```json
{
    "top_gainers": [
        {"symbol": "TOKEN1", "change": 15.5}
    ],
    "top_losers": [
        {"symbol": "TOKEN2", "change": -10.2}
    ],
    "volume_leaders": [
        {"symbol": "BTC", "volume": 1000000000}
    ]
}
```

## Integration

### Usage Example
```python
from services.correlation_analyzer import CorrelationAnalyzer

# Initialize with Binance client
analyzer = CorrelationAnalyzer(client)

# Get comprehensive correlation data
data = await analyzer.get_correlation_data("TRUMPUSDC")
```

## Technical Details

### BTC Correlation Calculation
- Uses 5-minute candles for granular analysis
- Pearson correlation coefficient
- Rolling 24-hour window
- Numpy-based calculations for efficiency

### Market Dominance
- CoinGecko API integration
- Real-time market cap tracking
- Automatic updates

### Stablecoin Analysis
- Tracks top stablecoin pairs
- Volume-weighted analysis
- Large transaction detection (>1000 USDC)

### Market Trend Analysis
- Top 10 pairs by volume
- Percentage change tracking
- Volume profile analysis

## Error Handling
- Graceful fallbacks for API failures
- Default values for missing data
- Comprehensive error logging
- Automatic retries for transient errors

## Dependencies
- numpy: For correlation calculations
- aiohttp: For async API requests
- python-binance: For market data

## Future Improvements
1. Multi-timeframe correlation analysis
2. Machine learning-based trend prediction
3. Cross-exchange correlation analysis
4. Advanced market manipulation detection
5. Historical correlation patterns 