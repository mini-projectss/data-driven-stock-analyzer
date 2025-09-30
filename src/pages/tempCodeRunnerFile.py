import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QLineEdit, QHeaderView, QSizePolicy, QApplication
)
from PyQt6.QtGui import QFont, QPalette, QColor, QDesktopServices
from PyQt6.QtCore import Qt, QSize, QUrl, QThread, pyqtSignal
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk import download
from datetime import datetime, timedelta

download('vader_lexicon', quiet=True)

# --- Worker thread to fetch news without freezing UI ---
class NewsWorker(QThread):
    result_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, tickers):
        super().__init__()
        self.tickers = tickers
        self.analyzer = SentimentAnalyzer()

    def run(self):
        all_data = []
        try:
            for ticker in self.tickers:
                all_data.extend(self.analyzer.get_sentiment_data(ticker))
            self.result_ready.emit(all_data)
        except Exception as e:
            self.error_occurred.emit(str(e))

# --- Sentiment Analysis ---
class SentimentAnalyzer:
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
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": company_name,
            "apiKey": self.news_api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "from": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            articles = data.get("articles", [])
            return [{"title": a["title"], "url": a["url"]} for a in articles if a.get("title") and a.get("url")]
        except Exception:
            return []

    def analyze_sentiment(self, text):
        score = self.sid.polarity_scores(text)["compound"]
        if score >= 0.05:
            return "positive", score
        elif score <= -0.05:
            return "negative", score
        return "neutral", score

    def get_sentiment_data(self, ticker):
        articles = self.fetch_news(ticker)
        result = []
        for a in articles[:5]:
            sentiment, score = self.analyze_sentiment(a["title"])
            result.append({
                "text": a["title"],
                "sentiment": sentiment,
                "score": score,
                "source": "News",
                "ticker": ticker.upper(),
                "url": a["url"]
            })
        return result


# --- Sentiment Page ---
class SentimentPage(QWidget):
    def __init__(self):
        super().__init__()
        self.analyzer = SentimentAnalyzer()
        self.init_ui()

    def init_ui(self):
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#101418"))
        self.setPalette(pal)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title = QLabel("📊 Market News & Sentiment Dashboard")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #E2E8F0;")
        main_layout.addWidget(title)

        # Search
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter ticker (e.g., RELIANCE, TCS, INFY)")
        self.search_input.setMinimumHeight(36)
        self.search_input.setStyleSheet("padding: 6px; font-size: 14px;")
        search_layout.addWidget(self.search_input)

        self.search_button = QPushButton("🔍 Search")
        self.search_button.setStyleSheet(self.button_style())
        self.search_button.clicked.connect(self.search_ticker_news)
        search_layout.addWidget(self.search_button)
        main_layout.addLayout(search_layout)

        # Trending
        self.trending_button = QPushButton("🔥 Trending News")
        self.trending_button.setStyleSheet(self.button_style())
        self.trending_button.clicked.connect(self.show_trending_news)
        main_layout.addWidget(self.trending_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Ticker", "Headline", "Sentiment", "Score", "Source"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellClicked.connect(self.open_article)
        main_layout.addWidget(self.table)

        # Loading
        self.loading_label = QLabel("⏳ Fetching news...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel { background-color: rgba(0,0,0,160); color:white;
                    font-size:18px; font-weight:bold; border-radius:8px; padding:12px;}
        """)
        self.loading_label.hide()
        main_layout.addWidget(self.loading_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setMinimumSize(QSize(950, 600))

        # Load trending initially
        self.show_trending_news()

    def button_style(self):
        return """
            QPushButton { background-color: #2563eb; color:white; border-radius:10px; padding:6px 12px; font-weight:bold; }
            QPushButton:hover { background-color: #3b82f6; }
            QPushButton:pressed { background-color: #1d4ed8; }
        """

    def show_loading(self, text="⏳ Fetching news..."):
        self.loading_label.setText(text)
        self.loading_label.show()
        QApplication.processEvents()

    def hide_loading(self):
        self.loading_label.hide()

    def search_ticker_news(self):
        ticker = self.search_input.text().strip()
        if not ticker:
            QMessageBox.warning(self, "Input Required", "Enter a ticker symbol.")
            return
        self.fetch_news_async([ticker])

    def show_trending_news(self):
        tickers = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "NIFTY"]
        self.fetch_news_async(tickers)

    def fetch_news_async(self, tickers):
        self.show_loading("Fetching news...")
        self.table.clearContents()
        self.table.setRowCount(0)
        self.worker = NewsWorker(tickers)
        self.worker.result_ready.connect(self._update_table)
        self.worker.error_occurred.connect(lambda e: QMessageBox.warning(self, "Error", e))
        self.worker.finished.connect(self.hide_loading)
        self.worker.start()

    def _update_table(self, data):
        self.table.setRowCount(len(data))
        for i, item in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(item["ticker"]))
            text_item = QTableWidgetItem(item["text"])
            text_item.setFlags(text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if item.get("url"):
                text_item.setData(Qt.ItemDataRole.UserRole, item["url"])
            self.table.setItem(i, 1, text_item)

            sentiment_item = QTableWidgetItem(item["sentiment"].capitalize())
            color_map = {"positive": "#22c55e", "negative": "#ef4444", "neutral": "#eab308"}
            sentiment_item.setForeground(QColor(color_map.get(item["sentiment"], "#eab308")))
            self.table.setItem(i, 2, sentiment_item)

            self.table.setItem(i, 3, QTableWidgetItem(f"{item['score']:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(item["source"]))

    def open_article(self, row, column):
        if column == 1:
            item = self.table.item(row, column)
            if item:
                url = item.data(Qt.ItemDataRole.UserRole)
                if url:
                    QDesktopServices.openUrl(QUrl(url))
