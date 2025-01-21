# Sentiment Analysis System

## Overview
The sentiment analysis system provides comprehensive market sentiment data by integrating multiple data sources:
- Twitter social sentiment
- News articles analysis
- Crypto Fear & Greed Index

## Components

### 1. Social Sentiment (Twitter)
Analyzes recent tweets about specific crypto tokens to gauge market sentiment.

#### Features:
- Real-time tweet analysis
- Sentiment classification (Bullish/Bearish/Neutral)
- Rate limit handling with automatic retries
- Sample tweet collection

#### Example Output:
```json
{
    "mention_count": 10,
    "sentiment_scores": {
        "bullish_ratio": 0.6,
        "bearish_ratio": 0.0,
        "neutral_ratio": 0.4
    },
    "sample_tweets": ["..."]
}
```

### 2. News Sentiment
Analyzes recent news articles to understand market narrative and sentiment.

#### Features:
- 24-hour news coverage
- Top headlines extraction
- Sentiment analysis with confidence scores
- Key topic identification

#### Example Output:
```json
{
    "article_count": 100,
    "top_headlines": ["..."],
    "sentiment_summary": {
        "sentiment": "positive",
        "confidence": 0.8,
        "key_topics": ["market growth", "adoption"]
    }
}
```

### 3. Fear & Greed Index
Provides market-wide sentiment indicator based on multiple factors.

#### Features:
- Daily index value (0-100)
- Sentiment classification
- Timestamp tracking

#### Classifications:
- 0-24: Extreme Fear
- 25-44: Fear
- 45-55: Neutral
- 56-75: Greed
- 76-100: Extreme Greed

#### Example Output:
```json
{
    "value": 76,
    "classification": "Extreme Greed",
    "timestamp": "2025-01-20T12:00:00"
}
```

## Integration

### Required Environment Variables
```bash
# Twitter API v2
TWITTER_BEARER_TOKEN=your_twitter_token

# News API
NEWS_API_KEY=your_newsapi_key

# OpenRouter API (for AI analysis)
OPENROUTER_API_KEY=your_openrouter_key
```

### Usage Example
```python
from services.sentiment_analyzer import SentimentAnalyzer

# Initialize analyzer
analyzer = SentimentAnalyzer()

# Get comprehensive sentiment data
sentiment_data = await analyzer.get_sentiment_data("TRUMP")
```

## AI Analysis
The system uses DeepSeek via OpenRouter for advanced sentiment analysis:

1. **Tweet Analysis**:
   - Classifies each tweet as bullish, bearish, or neutral
   - Calculates sentiment ratios
   - Provides aggregated sentiment metrics

2. **News Analysis**:
   - Analyzes article content and headlines
   - Determines overall sentiment with confidence score
   - Extracts key topics and themes

## Rate Limits and Optimization

### Twitter API
- Limited to 10 tweets per request
- Implements retry mechanism for rate limits
- Automatic waiting on 429 responses

### News API
- 100 articles per request
- Daily request limits based on plan
- Sorted by popularity for relevance

### Fear & Greed Index
- No rate limits
- Updates daily
- Free public API

## Error Handling
- Graceful degradation on API failures
- Default neutral values when data unavailable
- Detailed error logging
- Automatic retries for transient failures

## Future Improvements
1. Data caching for rate limit optimization
2. Additional sentiment sources (Reddit, Telegram)
3. Historical sentiment tracking
4. Correlation analysis with price movements
5. Sentiment-based trading signals

## Testing
Use the test script to verify API integrations:
```bash
python src/test_apis.py
```

This will test all components and display detailed results including:
- Twitter sentiment analysis
- News coverage and headlines
- Current Fear & Greed Index 