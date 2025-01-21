# Market Data Service

## Overview
The Market Data Service provides real-time market data and technical analysis by integrating:
- Real-time price feeds
- Order book analysis
- Technical indicators
- Market manipulation detection

## Components

### 1. Price and Volume Data
Tracks real-time market data through WebSocket connections.

#### Features:
- Real-time price updates
- Volume tracking
- Trade history
- Candlestick data

#### Data Structures:
```python
@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int
    vwap: Optional[float]
```

### 2. Order Book Analysis
Maintains and analyzes the order book for market insights.

#### Features:
- Real-time order book updates
- Depth analysis
- Imbalance calculation
- Spoofing detection

#### Metrics:
- Bid/Ask spread
- Order book depth
- Volume imbalance
- Cancellation rates

### 3. Technical Indicators
Calculates various technical analysis indicators.

#### Available Indicators:
- Moving Averages (MA5, MA20)
- VWAP (Volume Weighted Average Price)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)

#### Example Output:
```json
{
    "technical_indicators": {
        "ma5": 40.15,
        "ma20": 39.95,
        "vwap": 40.10,
        "rsi": 65.5,
        "macd": {
            "macd": 0.25,
            "signal": 0.15,
            "histogram": 0.10
        }
    }
}
```

### 4. Market Manipulation Detection
Monitors for potential market manipulation activities.

#### Detection Features:
- Spoofing detection
- Abnormal volume detection
- Price-volume divergence
- Large order tracking

## Integration

### Initialization
```python
from services.market_data import MarketDataService

# Initialize service
service = MarketDataService(symbol="TRUMPUSDC")

# Start data collection
service.start(api_key, api_secret)
```

### Market Snapshot
```python
# Get comprehensive market data
snapshot = await service.get_market_snapshot()
```

### Entry Price Calculation
```python
# Get optimal entry prices
entry_levels = service.get_optimal_entry_levels(usdc_amount=1000)
```

## WebSocket Integration

### Available Streams:
1. Trade Stream
   - Real-time trade execution data
   - Price updates
   - Volume tracking

2. Order Book Stream
   - Bid/Ask updates
   - Depth maintenance
   - Real-time imbalance calculation

### Handlers:
```python
def _handle_ticker(self, msg: dict):
    """Process ticker updates"""
    # Price updates
    # Indicator updates

def _handle_depth(self, msg: dict):
    """Process order book updates"""
    # Order book maintenance
    # Manipulation detection
```

## Technical Details

### Candlestick Management
- Rolling window of 1000 candles
- Real-time VWAP calculation
- Volume profile analysis

### Order Book Management
- Maximum depth of 50 levels
- Cancel rate tracking
- Spoofing detection
- Liquidity analysis

### Technical Indicators
- RSI (14 periods)
- MACD (12, 26, 9)
- Moving averages (5, 20 periods)
- Custom indicator framework

## Error Handling
- WebSocket reconnection logic
- Data validation
- Error logging
- Graceful degradation

## Dependencies
- python-binance: For Binance API integration
- numpy: For calculations
- pandas: For data management
- websockets: For real-time data

## Future Improvements
1. Additional technical indicators
2. Enhanced manipulation detection
3. Machine learning integration
4. Cross-exchange arbitrage
5. Advanced order book analysis 