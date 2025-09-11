# src/page/dashboard/_sentiment.py (updated version)
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk import download
from datetime import datetime, timedelta

download('vader_lexicon', quiet=True)

class NewSentiment:
    def __init__(self):
        self.sid = SentimentIntensityAnalyzer()
        self.news_api_key = "dade78fd12f844a9890b5f791ee931f4"
        print(f"Initialized NewSentiment with API Key: {self.news_api_key[:10]}...")

    def fetch_news(self, ticker):
        company_map = {
            "AAPL": "Apple", "TSLA": "Tesla", "GOOGL": "Google", "MSFT": "Microsoft", "AMZN": "Amazon",
            "RELIANCE": "Reliance Industries", "TCS": "Tata Consultancy Services", "INFY": "Infosys",
            "HDFCBANK": "HDFC Bank", "ICICIBANK": "ICICI Bank"
        }
        company_name = company_map.get(ticker.upper(), ticker.upper())
        query = f"{company_name}"  # Simplified query

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "apiKey": self.news_api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "from": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")  # Extended to 30 days
        }
        print(f"Fetching news for ticker '{ticker}' with query: '{query}'")
        try:
            response = requests.get(url, params=params, timeout=10)
            print(f"API Response Status Code: {response.status_code}")
            if response.status_code != 200:
                print(f"API Error: {response.text}")
                return []
            data = response.json()
            print(f"Total Results Available: {data.get('totalResults', 0)}")
            articles = data.get("articles", [])
            titles = [article["title"] for article in articles if article.get("title")]
            print(f"Fetched {len(titles)} articles: {titles[:2]}...")
            return titles
        except requests.exceptions.RequestException as e:
            print(f"News API Request Error: {e}")
            return []

    def analyze_sentiment(self, text):
        score = self.sid.polarity_scores(text)
        compound = score["compound"]
        sentiment = "neutral"
        if compound >= 0.05:
            sentiment = "positive"
        elif compound <= -0.05:
            sentiment = "negative"
        print(f"Analyzed '{text[:50]}...': {sentiment} (score: {compound:.2f})")
        return sentiment, compound

    def get_sentiment_data(self, ticker):
        print(f"Starting sentiment analysis for {ticker}...")
        news_texts = self.fetch_news(ticker)
        if not news_texts:
            print("No news texts fetched. Returning empty list.")
            return []
        sentiments = []
        for text in news_texts[:5]:
            sentiment, score = self.analyze_sentiment(text)
            sentiments.append({"text": text, "sentiment": sentiment, "score": score, "source": "News"})
        print(f"Generated {len(sentiments)} sentiment entries.")
        return sentiments

if __name__ == "__main__":
    analyzer = NewSentiment()
    test_tickers = ["AAPL", "RELIANCE", "TCS"]
    for ticker in test_tickers:
        data = analyzer.get_sentiment_data(ticker)
        print(f"\nTest Results for {ticker}:")
        for item in data:
            print(f"- {item['text'][:50]}... | {item['sentiment']} ({item['score']:.2f})")