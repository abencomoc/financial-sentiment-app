import streamlit as st
import requests
from datetime import datetime
import pandas as pd
from typing import Dict, List
import os
import plotly.express as px

NEWS_API_URL = "https://newsapi.org/v2/everything"
FINANCIAL_DOMAINS = "finance.yahoo.com,bloomberg.com,reuters.com,ft.com,wsj.com,cnbc.com,marketwatch.com,investing.com,seekingalpha.com,fool.com,businessinsider.com,forbes.com,barrons.com,economist.com,money.cnn.com,morningstar.com,tradingview.com,zacks.com,benzinga.com,finviz.com,nasdaq.com,nyse.com,londonstockexchange.com,moodys.com,spglobal.com,fitchratings.com"

FINBERT_API_URL = os.getenv('FINBERT_API_URL') # "http://localhost:8000"
# Get API key from environment variable for security
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

def get_news_articles(company: str, date: str) -> List[Dict]:
    """
    Fetch news articles for a specific company and date from NewsAPI
    """
    try:
        # Format the date for NewsAPI (which requires ISO format)
        formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")
        
        params = {
            'q': company,
            'searchIn': 'title,description',
            'from': formatted_date,
            'to': formatted_date,
            'sortBy': 'publishedAt',
            'apiKey': NEWS_API_KEY,
            "domains": FINANCIAL_DOMAINS,
            'language': 'en'
        }
        
        response = requests.get(NEWS_API_URL, params=params)
        
        if response.status_code == 200:
            articles = response.json().get('articles', [])
            return [
                {
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'url': article.get('url', ''),
                    'source': article.get('source', {}).get('name', ''),
                    'published_at': article.get('publishedAt', '')
                }
                for article in articles
                if article.get('description')  # Only include articles with descriptions
            ]
        else:
            st.error(f"Error fetching news: {response.status_code}")
            return []
            
    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")
        return []

def analyze_sentiment(text: str) -> Dict:
    """
    Get sentiment analysis from FinBERT API
    """
    try:
        response = requests.post(
            FINBERT_API_URL,
            json={"text": text}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API error: {response.status_code}"}
            
    except Exception as e:
        return {"error": f"Request error: {str(e)}"}

def calculate_overall_sentiment(sentiments: List[Dict]) -> Dict:
    """
    Calculate overall sentiment from individual article sentiments
    """
    if not sentiments:
        return {
            "overall_sentiment": "neutral",
            "overall_score": 0.0,
            "total_articles": 0
        }
    
    # Count sentiments
    sentiment_counts = {
        "positive": 0,
        "negative": 0,
        "neutral": 0
    }
    
    total_score = 0.0
    valid_sentiments = 0
    
    for sentiment in sentiments:
        if "error" not in sentiment:
            label = sentiment.get("sentiment", "neutral")
            score = sentiment.get("score", 0.0)
            sentiment_counts[label] += 1
            total_score += score
            valid_sentiments += 1
    
    # Determine overall sentiment
    if valid_sentiments > 0:
        dominant_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0]
        average_score = total_score / valid_sentiments
    else:
        dominant_sentiment = "neutral"
        average_score = 0.0
    
    return {
        "overall_sentiment": dominant_sentiment,
        "overall_score": average_score,
        "total_articles": valid_sentiments,
        "sentiment_distribution": sentiment_counts
    }

def main():
    st.set_page_config(
        page_title="Company Sentiment Analysis",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📰 Company News Sentiment Analysis")
    st.write("Analyze sentiment of news articles for a specific company and date.")
    
    # Input section
    col1, col2 = st.columns(2)
    with col1:
        company = st.text_input("Enter company name (e.g., Apple, Meta, Amazon):", "Meta")
    with col2:
        date = st.date_input(
            "Select date:",
            datetime.now()
        )
    
    if st.button("Analyze Sentiment"):
        if company and date:
            formatted_date = date.strftime("%Y-%m-%d")
            
            with st.spinner('Fetching and analyzing news articles...'):
                # Get news articles
                articles = get_news_articles(company, formatted_date)
                
                if not articles:
                    st.warning("No articles found for the selected date and company.")
                    return
                
                # Analyze sentiment for each article
                sentiments = []
                article_results = []
                
                for article in articles:
                    sentiment = analyze_sentiment(article['description'])
                    sentiments.append(sentiment)
                    article_results.append({**article, "sentiment": sentiment})
                
                # Calculate overall sentiment
                overall_results = calculate_overall_sentiment(sentiments)
                
                # Display results
                st.header("Analysis Results")
                
                # Display metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Articles", overall_results["total_articles"])
                with col2:
                    st.metric(
                        "Overall Sentiment",
                        overall_results["overall_sentiment"]
                    )
                with col3:
                    st.metric("Average Score", f"{overall_results['overall_score']:.2f}")
                
                # Display sentiment distribution pie chart
                sentiment_dist = overall_results["sentiment_distribution"]
                fig = px.pie(
                    values=list(sentiment_dist.values()),
                    names=list(sentiment_dist.keys()),
                    title="Sentiment Distribution",
                    color=list(sentiment_dist.keys()),
                    color_discrete_map={
                        "positive": "green",
                        "negative": "red",
                        "neutral": "gray"
                    }
                )
                st.plotly_chart(fig)
                
                # Display article details
                st.subheader("Article Details")
                for article in article_results:
                    with st.expander(f"{article['title']}"):
                        st.write(f"**Source:** {article['source']}")
                        st.write(f"**Published:** {article['published_at']}")
                        st.write(f"**Sentiment:** {article['sentiment'].get('sentiment', 'N/A')} "
                               f"(Score: {article['sentiment'].get('score', 0):.2f})")
                        st.write("**Description:**")
                        st.write(article['description'])
                        st.write(f"[Read full article]({article['url']})")
        else:
            st.warning("Please enter both company name and date.")

if __name__ == "__main__":
    main()
