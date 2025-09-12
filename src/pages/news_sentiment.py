# src/pages/new_sentiment.py
import requests
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt, QSize
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk import download
from datetime import datetime, timedelta

download('vader_lexicon', quiet=True)

class NewSentiment:
    def __init__(self):
        self.sid = SentimentIntensityAnalyzer()
        self.news_api_key = "dade78fd12f844a9890b5f791ee931f4"

    def fetch_news(self, ticker):
        company_map = {
            "RELIANCE": "Reliance Industries",
            "TCS": "Tata Consultancy Services",
            "INFY": "Infosys",
            "HDFCBANK": "HDFC Bank",
            "ICICIBANK": "ICICI Bank",
            "NIFTY": "NIFTY 50"
        }
        company_name = company_map.get(ticker.upper(), ticker.upper())
        query = f"{company_name}"

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "apiKey": self.news_api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "from": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                return []
            data = response.json()
            articles = data.get("articles", [])
            titles = [article["title"] for article in articles if article.get("title")]
            return titles
        except requests.exceptions.RequestException:
            return []

    def analyze_sentiment(self, text):
        score = self.sid.polarity_scores(text)
        compound = score["compound"]
        sentiment = "neutral"
        if compound >= 0.05:
            sentiment = "positive"
        elif compound <= -0.05:
            sentiment = "negative"
        return sentiment, compound

    def get_sentiment_data(self, ticker):
        news_texts = self.fetch_news(ticker)
        if not news_texts:
            return []
        sentiments = []
        for text in news_texts[:5]:
            sentiment, score = self.analyze_sentiment(text)
            sentiments.append({"text": text, "sentiment": sentiment, "score": score, "source": "News", "ticker": ticker})
        return sentiments

    def get_reddit_data(self, ticker):  # Placeholder for Reddit API
        return [
            {"text": f"Reddit post about {ticker} growth", "sentiment": "positive", "score": 0.15, "source": "Reddit", "ticker": ticker},
            {"text": f"Reddit discussion on {ticker} decline", "sentiment": "negative", "score": -0.12, "source": "Reddit", "ticker": ticker}
        ]

class SentimentPage(QWidget):
    def __init__(self):
        super().__init__()
        self.analyzer = NewSentiment()
        self.init_ui()

    def init_ui(self):
        # Set window background
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1B2026"))
        self.setPalette(palette)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Creative title with gradient and shadow
        title_label = QLabel("News & Sentiment Analysis")
        title_font = QFont("Segoe UI", 20, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #DDE8F5, stop: 1 #A3BFFA);
                text-shadow: 2px 2px 4px #000000;
                padding: 10px;
                border-radius: 10px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #2B323A, stop: 1 #1E252D);
            }
        """)
        layout.addWidget(title_label)

        # Button layout with creative styling
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.trending_button = QPushButton("Trending News")
        self.trending_button.setFixedHeight(40)
        self.trending_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #1e90ff, stop: 1 #63b3ff);
                color: white; border-radius: 10px; padding: 0 15px;
                border: 2px solid #DDE8F5;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #63b3ff, stop: 1 #1e90ff);
                border: 2px solid #A3BFFA;
            }
        """)
        self.trending_button.clicked.connect(self.show_trending_news)
        button_layout.addWidget(self.trending_button)

        self.reddit_button = QPushButton("Reddit Responses")
        self.reddit_button.setFixedHeight(40)
        self.reddit_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ff6347, stop: 1 #ff8c69);
                color: white; border-radius: 10px; padding: 0 15px;
                border: 2px solid #DDE8F5;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ff8c69, stop: 1 #ff6347);
                border: 2px solid #A3BFFA;
            }
        """)
        self.reddit_button.clicked.connect(self.show_reddit_responses)
        button_layout.addWidget(self.reddit_button)

        layout.addLayout(button_layout)

        # Table with responsive design
        self.table = QTableWidget()
        self.table.setColumnCount(5)  # Includes Ticker, News Title, Sentiment, Score, Source
        self.table.setHorizontalHeaderLabels(["Ticker", "News Title", "Sentiment", "Score", "Source"])
        # Optimized column widths to fit content and reduce empty space
        self.table.setColumnWidth(0, 70)  # Ticker
        self.table.setColumnWidth(1, 450)  # News Title (adjusted to fit better)
        self.table.setColumnWidth(2, 90)   # Sentiment
        self.table.setColumnWidth(3, 70)   # Score
        self.table.setColumnWidth(4, 50)   # Source
        self.table.horizontalHeader().setStretchLastSection(False)  # Disable stretch to control layout
        self.table.setWordWrap(True)  # Enable word wrap for all cells
        self.table.verticalHeader().setVisible(False)  # Hide row numbers for cleaner look
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1B2026;
                color: #DDE8F5;
                border: 2px solid #2B323A;
                border-radius: 5px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2B323A;
            }
            QHeaderView::section {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #2B323A, stop: 1 #1E252D);
                color: #DDE8F5;
                padding: 5px;
                border: 1px solid #2B323A;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.table)

        # Make layout responsive
        self.setLayout(layout)
        self.setMinimumSize(QSize(800, 500))  # Minimum size to ensure readability
        self.resize(900, 600)  # Adjusted to fit content better

    def show_trending_news(self):
        self.table.clearContents()
        self.table.setRowCount(0)
        test_tickers = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "NIFTY"]
        all_data = []
        for ticker in test_tickers:
            data = self.analyzer.get_sentiment_data(ticker)
            all_data.extend(data)
        if not all_data:
            QMessageBox.warning(self, "No Data", "Failed to fetch news. Check API key or network.")
        self._update_table(all_data)

    def show_reddit_responses(self):
        self.table.clearContents()
        self.table.setRowCount(0)
        test_tickers = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "NIFTY"]
        all_data = []
        for ticker in test_tickers:
            data = self.analyzer.get_reddit_data(ticker)
            all_data.extend(data)
        self._update_table(all_data)

    def _update_table(self, data):
        self.table.setRowCount(len(data))
        for i, item in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(item["ticker"]))
            item_widget = QTableWidgetItem(item["text"])
            item_widget.setFlags(item_widget.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Disable editing
            self.table.setItem(i, 1, item_widget)
            self.table.setItem(i, 2, QTableWidgetItem(item["sentiment"]))
            self.table.setItem(i, 3, QTableWidgetItem(f"{item['score']:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(item["source"]))

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = SentimentPage()
    window.setWindowTitle("News & Sentiment")
    window.show()
    sys.exit(app.exec())