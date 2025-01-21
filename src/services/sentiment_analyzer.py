#!/usr/bin/env python3
from typing import Dict, List
import aiohttp
import os
import json
import logging
from datetime import datetime, timedelta
import requests
import asyncio

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self, client=None):
        """Initialize sentiment analyzer with optional Binance client"""
        self.client = client
        self.twitter_api = None
        self.news_api = None
        
        # Load API keys
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.news_api_key = os.getenv('NEWS_API_KEY')
        
        if not self.twitter_bearer_token:
            logger.warning("Twitter Bearer Token not found. Twitter analysis will be disabled.")
        if not self.news_api_key:
            logger.warning("News API Key not found. News analysis will be disabled.")
        
        self.fear_greed_api = "https://api.alternative.me/fng/"
        
    async def get_sentiment_data(self, symbol: str) -> Dict:
        """Get comprehensive sentiment analysis"""
        try:
            return {
                "social_sentiment": await self._get_social_sentiment(symbol),
                "news_sentiment": await self._get_news_sentiment(symbol),
                "market_mood": await self._get_fear_greed_index()
            }
        except Exception as e:
            logger.error(f"Error getting sentiment data: {e}")
            return {}
            
    async def _get_social_sentiment(self, symbol: str) -> Dict:
        """Get Twitter sentiment for symbol"""
        if not self.twitter_bearer_token:
            logger.error("Twitter Bearer Token not found")
            return {}
            
        try:
            async with aiohttp.ClientSession() as session:
                # Search last 24h of tweets with reduced results
                query = f"({symbol} crypto) -is:retweet lang:en"
                
                # Twitter API v2 endpoint with reduced parameters
                url = "https://api.twitter.com/2/tweets/search/recent"
                params = {
                    "query": query,
                    "max_results": 10,  # Reduced from 100 to avoid rate limits
                    "tweet.fields": "created_at",  # Reduced fields
                }
                
                headers = {
                    "Authorization": f"Bearer {self.twitter_bearer_token}",
                    "Content-Type": "application/json"
                }
                
                # Add rate limit handling
                for attempt in range(3):  # Try up to 3 times
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            tweets = data.get('data', [])
                            logger.info(f"Found {len(tweets)} tweets about {symbol}")
                            
                            if tweets:
                                sentiment = await self._analyze_tweets(tweets)
                                return {
                                    "mention_count": len(tweets),
                                    "sentiment_scores": sentiment,
                                    "sample_tweets": [t['text'] for t in tweets[:3]]
                                }
                            break
                        elif response.status == 429:  # Rate limit exceeded
                            wait_time = int(response.headers.get('x-rate-limit-reset', 60))
                            logger.warning(f"Rate limit hit, waiting {wait_time} seconds...")
                            await asyncio.sleep(min(wait_time, 60))  # Wait but not more than 60 seconds
                            continue
                        else:
                            error_data = await response.text()
                            logger.error(f"Twitter API error: {error_data}")
                            break
            return {}
        except Exception as e:
            logger.error(f"Error getting Twitter sentiment: {e}")
            return {}
            
    async def _get_news_sentiment(self, symbol: str) -> Dict:
        """Get news sentiment from NewsAPI"""
        if not self.news_api_key:
            return {}
            
        try:
            async with aiohttp.ClientSession() as session:
                # Get crypto news from last 24h
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                url = f"https://newsapi.org/v2/everything?q={symbol} crypto&from={yesterday}&sortBy=popularity&apiKey={self.news_api_key}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = data.get('articles', [])
                        return {
                            "article_count": len(articles),
                            "top_headlines": [a['title'] for a in articles[:3]],
                            "sentiment_summary": await self._analyze_news(articles)
                        }
            return {}
        except Exception as e:
            logger.error(f"Error getting news sentiment: {e}")
            return {}
            
    async def _get_fear_greed_index(self) -> Dict:
        """Get Fear & Greed Index"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.fear_greed_api) as response:
                    if response.status == 200:
                        data = await response.json()
                        latest = data['data'][0]
                        return {
                            "value": int(latest['value']),
                            "classification": latest['value_classification'],
                            "timestamp": latest['timestamp']
                        }
            return {}
        except Exception as e:
            logger.error(f"Error getting Fear & Greed Index: {e}")
            return {}
            
    async def _analyze_tweets(self, tweets: List[Dict]) -> Dict:
        """Analyze sentiment of tweets using OpenRouter"""
        if not tweets:
            return {"bullish_ratio": 0, "bearish_ratio": 0, "neutral_ratio": 1}
            
        try:
            # Batch tweets for analysis
            text = "\n".join([tweet.get('text', '') for tweet in tweets])
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    "HTTP-Referer": "https://github.com/padak/binance_trading",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "deepseek/deepseek-r1",
                    "messages": [{
                        "role": "user",
                        "content": f"""Analyze the sentiment of these crypto-related tweets about {len(tweets)} tweets.
                        Classify each tweet as bullish, bearish, or neutral.
                        Return ONLY a JSON object in this exact format:
                        {{
                            "bullish_ratio": (number of bullish tweets / total tweets),
                            "bearish_ratio": (number of bearish tweets / total tweets),
                            "neutral_ratio": (number of neutral tweets / total tweets)
                        }}
                        
                        Tweets to analyze:
                        {text}"""
                    }]
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
                        return json.loads(content)
            return {"bullish_ratio": 0, "bearish_ratio": 0, "neutral_ratio": 1}
        except Exception as e:
            logger.error(f"Error analyzing tweets: {e}")
            return {"bullish_ratio": 0, "bearish_ratio": 0, "neutral_ratio": 1}
            
    async def _analyze_news(self, articles: List[Dict]) -> Dict:
        """Analyze sentiment of news articles"""
        if not articles:
            return {"sentiment": "neutral", "confidence": 0, "key_topics": []}
            
        try:
            # Extract titles and descriptions
            texts = [f"{a.get('title', '')} {a.get('description', '')}" for a in articles[:5]]  # Analyze top 5 articles
            text = "\n".join(texts)
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    "HTTP-Referer": "https://github.com/padak/binance_trading",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "deepseek/deepseek-r1",
                    "messages": [{
                        "role": "user",
                        "content": f"""Analyze the sentiment of these crypto news articles.
                        Return ONLY a JSON object in this exact format:
                        {{
                            "sentiment": "positive" or "negative" or "neutral",
                            "confidence": (0.0 to 1.0),
                            "key_topics": [list of main topics]
                        }}
                        
                        Articles to analyze:
                        {text}"""
                    }]
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
                        return json.loads(content)
            return {"sentiment": "neutral", "confidence": 0, "key_topics": []}
        except Exception as e:
            logger.error(f"Error analyzing news: {e}")
            return {"sentiment": "neutral", "confidence": 0, "key_topics": []} 