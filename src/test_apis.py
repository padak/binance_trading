#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
from services.sentiment_analyzer import SentimentAnalyzer
from datetime import datetime

async def test_apis():
    print("\nTesting API Integrations...")
    
    # Initialize sentiment analyzer
    analyzer = SentimentAnalyzer()
    symbol = "TRUMP"  # Test with TRUMP token
    
    print("\n1. Testing Twitter API...")
    social_data = await analyzer._get_social_sentiment(symbol)
    if social_data:
        print("✅ Twitter API working!")
        print(f"Found {social_data.get('mention_count', 0)} tweets about {symbol}")
        
        if 'sentiment_scores' in social_data:
            scores = social_data['sentiment_scores']
            print("\nSentiment Analysis:")
            print(f"Bullish: {scores.get('bullish_ratio', 0)*100:.1f}%")
            print(f"Bearish: {scores.get('bearish_ratio', 0)*100:.1f}%")
            print(f"Neutral: {scores.get('neutral_ratio', 0)*100:.1f}%")
            
        if 'sample_tweets' in social_data:
            print("\nSample Tweets:")
            for tweet in social_data['sample_tweets']:
                print(f"- {tweet[:100]}...")
    else:
        print("❌ Twitter API failed or no data found")
        
    print("\n2. Testing News API...")
    news_data = await analyzer._get_news_sentiment(symbol)
    if news_data:
        print("✅ News API working!")
        print(f"Found {news_data.get('article_count', 0)} articles about {symbol}")
        if 'top_headlines' in news_data:
            print("\nTop Headlines:")
            for headline in news_data['top_headlines']:
                print(f"- {headline}")
    else:
        print("❌ News API failed or no data found")
        
    print("\n3. Testing Fear & Greed Index...")
    fear_greed = await analyzer._get_fear_greed_index()
    if fear_greed:
        print("✅ Fear & Greed API working!")
        print(f"Current Value: {fear_greed.get('value', 'N/A')}")
        print(f"Classification: {fear_greed.get('classification', 'N/A')}")
    else:
        print("❌ Fear & Greed API failed")
        
    print("\nAPI Testing Complete!")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the async test
    asyncio.run(test_apis()) 