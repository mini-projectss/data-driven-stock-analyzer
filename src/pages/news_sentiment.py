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

# --- Ticker Lists & Configuration ---
# A practical list of top Indian stocks for demonstrative mass fetching
TOP_20_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "BHARTIARTL", "HINDUNILVR", "ITC",
    "SBIN", "KOTAKBANK", "LT", "AXISBANK", "BAJFINANCE", "ASIANPAINT", "MARUTI", "WIPRO",
    "SUNPHARMA", "TITAN", "ADANIENT", "NESTLEIND"
]

# User-provided massive list (All tickers cleaned of .BO suffix)
USER_CUSTOM_STOCKS = [
    "360ONE", "3MINDIA", "AADHARHFC", "AARTIIND", "AAVAS", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ABREL", "ABSLAMC", "ACC", "ACE", "ACMESOLAR", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", "ADANIPOWER", "AEGISLOG", "AFCONS", "AFFLE", "AIAENG", "AIIL", "AJANTPHARM", "AKUMS", "ALIVUS", "ALKEM", "ALKYLAMINE", "ALOKINDS", "AMBER", "AMBUJACEM", "ANANDRATHI", "ANANTRAJ", "ANGELONE", "APARINDS", "APLAPOLLO", "APLLTD", "APOLLOHOSP", "APOLLOTYRE", "APTUS", "ARE&M", "ASAHIINDIA", "ASHOKLEY", "ASIANPAINT", "ASTERDM", "ASTRAL", "ASTRAZEN", "ATGL", "ATUL", "AUBANK", "AUROPHARMA", "AWL", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJAJHFL", "BAJAJHLDNG", "BAJFINANCE", "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BANKINDIA", "BASF", "BATAINDIA", "BAYERCROP", "BBTC", "BDL", "BEL", "BEML", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHARTIHEXA", "BHEL", "BIKAJI", "BIOCON", "BLS", "BLUEDART", "BLUESTARCO", "BOSCHLTD", "BPCL", "BRIGADE", "BRITANNIA", "BSOFT", "CAMPUS", "CAMS", "CANBK", "CANFINHOME", "CAPLIPOINT", "CARBORUNIV", "CASTROLIND", "CCL", "CEATLTD", "CENTRALBK", "CENTURYPLY", "CERA", "CESC", "CGCL", "CGPOWER", "CHALET", "CHAMBLFERT", "CHENNPETRO", "CHOLAFIN", "CHOLAHLDNG", "CIPLA", "CLEAN", "COALINDIA", "COCHINSHIP", "COFORGE", "COHANCE", "COLPAL", "CONCOR", "CONCORDBIO", "COROMANDEL", "CRAFTSMAN", "CREDITACC", "CRISIL", "CROMPTON", "CUB", "CUMMINSIND", "CYIENT", "DABUR", "DALBHARAT", "DATAPATTNS", "DBREALTY", "DCMSHRIRAM", "DEEPAKFERT", "DEEPAKNTR", "DELHIVERY", "DEVYANI", "DIVISLAB", "DIXON", "DLF", "DMART", "DOMS", "DRREDDY", "ECLERX", "EICHERMOT", "EIDPARRY", "EIHOTEL", "ELECON", "ELGIEQUIP", "EMAMILTD", "EMCURE", "ENDURANCE", "ENGINERSIN", "ERIS", "ESCORTS", "ETERNAL", "EXIDEIND", "FACT", "FEDERALBNK", "FINCABLES", "FINPIPE", "FIRSTCRY", "FIVESTAR", "FLUOROCHEM", "FORTIS", "FSL", "GAIL", "GESHIP", "GICRE", "GILLETTE", "GLAND", "GLAXO", "GLENMARK", "GMDCLTD", "GMRAIRPORT", "GNFC", "GODFRYPHLP", "GODIGIT", "GODREJAGRO", "GODREJCP", "GODREJIND", "GODREJPROP", "GPIL", "GPPL", "GRANULES", "GRAPHITE", "GRASIM", "GRAVITA", "GRSE", "GSPL", "GUJGASLTD", "HAL", "HAPPSTMNDS", "HAVELLS", "HBLENGINE", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEG", "HEROMOTOCO", "HFCL", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "HINDZINC", "HOMEFIRST", "HONASA", "HONAUT", "HSCL", "HUDCO", "HYUNDAI", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDBI", "IDEA", "IDFCFIRSTB", "IEX", "IFCI", "IGIL", "IGL", "IIFL", "IKS", "INDGN", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIANB", "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY", "INOXINDIA", "INOXWIND", "INTELLECT", "IOB", "IOC", "IPCALAB", "IRB", "IRCON", "IRCTC", "IREDA", "IRFC", "ITC", "ITI", "J&KBANK", "JBCHEPHARM", "JBMA", "JINDALSAW", "JINDALSTEL", "JIOFIN", "JKCEMENT", "JKTYRE", "JMFINANCIL", "JPPOWER", "JSL", "JSWENERGY", "JSWHL", "JSWINFRA", "JSWSTEEL", "JUBLFOOD", "JUBLINGREA", "JUBLPHARMA", "JUSTDIAL", "JWL", "JYOTHYLAB", "JYOTICNC", "KAJARIACER", "KALYANKJIL", "KANSAINER", "KARURVYSYA", "KAYNES", "KEC", "KEI", "KFINTECH", "KIMS", "KIRLOSBROS", "KIRLOSENG", "KNRCON", "KOTAKBANK", "KPIL", "KPITTECH", "KPRMILL", "LALPATHLAB", "LATENTVIEW", "LAURUSLABS", "LEMONTREE", "LICHSGFIN", "LICI", "LINDEINDIA", "LLOYDSME", "LODHA", "LT", "LTF", "LTFOODS", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MAHABANK", "MAHSEAMLES", "MANAPPURAM", "MANKIND", "MANYAVAR", "MAPMYINDIA", "MARICO", "MARUTI", "MASTEK", "MAXHEALTH", "MAZDOCK", "MCX", "MEDANTA", "METROPOLIS", "MFSL", "MGL", "MINDACORP", "MMTC", "MOTHERSON", "MOTILALOFS", "MPHASIS", "MRF", "MRPL", "MSUMI", "MUTHOOTFIN", "NAM-INDIA", "NATCOPHARM", "NATIONALUM", "NAUKRI", "NAVA", "NAVINFLUOR", "NBCC", "NCC", "NESTLEIND", "NETWEB", "NETWORK18", "NEULANDLAB", "NEWGEN", "NH", "NHPC", "NIACL", "NIVABUPA", "NLCINDIA", "NMDC", "NSLNISP", "NTPC", "NTPCGREEN", "NUVAMA", "NYKAA", "OBEROIRLTY", "OFSS", "OIL", "OLAELEC", "OLECTRA", "ONGC", "PAGEIND", "PATANJALI", "PAYTM", "PCBL", "PEL", "PERSISTENT", "PETRONET", "PFC", "PFIZER", "PGEL", "PHOENIXLTD", "PIDILITIND", "PIIND", "PNB", "PNBHOUSING", "PNCINFRA", "POLICYBZR", "POLYCAB", "POLYMED", "POONAWALLA", "POWERGRID", "POWERINDIA", "PPLPHARMA", "PRAJIND", "PREMIERENE", "PRESTIGE", "PTCIL", "PVRINOX", "RADICO", "RAILTEL", "RAINBOW", "RAMCOCEM", "RAYMOND", "RAYMONDLSL", "RBLBANK", "RCF", "RECLTD", "REDINGTON", "RELIANCE", "RENUKA", "RHIM", "RITES", "RKFORGE", "ROUTE", "RPOWER", "RRKABEL", "RTNINDIA", "RVNL", "SAGILITY", "SAIL", "SAILIFE", "SAMMAANCAP", "SAPPHIRE", "SARDAEN", "SAREGAMA", "SBFC", "SBICARD", "SBILIFE", "SBIN", "SCHAEFFLER", "SCHNEIDER", "SCI", "SHREECEM", "SHRIRAMFIN", "SHYAMMETL", "SIEMENS", "SIGNATURE", "SJVN", "SKFINDIA", "SOBHA", "SOLARINDS", "SONACOMS", "SONATSOFTW", "SRF", "STARHEALTH", "SUMICHEM", "SUNDARMFIN", "SUNDRMFAST", "SUNPHARMA", "SUNTV", "SUPREMEIND", "SUZLON", "SWANENERGY", "SWIGGY", "SWSOLAR", "SYNGENE", "SYRMA", "TANLA", "TARIL", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAELXSI", "TATAINVEST", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TATATECH", "TBOTEK", "TCS", "TECHM", "TECHNOE", "TEJASNET", "THERMAX", "TIINDIA", "TIMKEN", "TITAGARH", "TITAN", "TORNTPHARM", "TORNTPOWER", "TRENT", "TRIDENT", "TRITURBINE", "TRIVENI", "TTML", "TVSMOTOR", "UBL", "UCOBANK", "ULTRACEMCO", "UNIONBANK", "UNITDSPR", "UNOMINDA", "UPL", "USHAMART", "UTIAMC", "VBL", "VEDL", "VGUARD", "VIJAYA", "VMM", "VOLTAS", "VTL", "WAAREEENER", "WELCORP", "WELSPUNLIV", "WESTLIFE", "WHIRLPOOL", "WIPRO", "WOCKPHARMA", "YESBANK", "ZEEL", "ZENSARTECH", "ZENTEC", "ZFCVINDIA", "ZYDUSLIFE"
]
MAX_CUSTOM_FETCH = 30 # Limit for custom bulk fetch


# Download VADER lexicon for sentiment analysis
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
                # Add a small delay between requests to be gentle on API limits
                self.msleep(100)
                all_data.extend(self.analyzer.get_sentiment_data(ticker))
            self.result_ready.emit(all_data)
        except Exception as e:
            self.error_occurred.emit(str(e))

# --- Sentiment Analysis ---
class SentimentAnalyzer:
    def __init__(self):
        self.sid = SentimentIntensityAnalyzer()
        # NOTE: This API key is public for demonstration purposes.
        # For a production application, use environment variables.
        self.news_api_key = "dade78fd12f844a9890b5f791ee931f4"

    def fetch_news(self, ticker):
        """Fetches news headlines for a given ticker."""
        company_map = {
            "RELIANCE": "Reliance Industries",
            "TCS": "Tata Consultancy Services",
            "INFY": "Infosys",
            "HDFCBANK": "HDFC Bank",
            "ICICIBANK": "ICICI Bank",
        }
        company_name = company_map.get(ticker.upper(), ticker.upper())
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": company_name,
            "apiKey": self.news_api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 100,  # Max articles per request
            "from": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            if data.get("status") == "error":
                print(f"API Error for {ticker}: {data.get('message')}")
                return []

            articles = data.get("articles", [])
            # Filter out articles without a title or URL
            return [{"title": a["title"], "url": a["url"]} for a in articles if a.get("title") and a.get("url")]
        except requests.exceptions.RequestException as e:
            print(f"Request error for {ticker}: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return []

    def analyze_sentiment(self, text):
        """Analyzes sentiment of a text using VADER."""
        score = self.sid.polarity_scores(text)["compound"]
        if score >= 0.05:
            return "positive", score
        elif score <= -0.05:
            return "negative", score
        return "neutral", score

    def get_sentiment_data(self, ticker):
        """Fetches news and performs sentiment analysis."""
        articles = self.fetch_news(ticker)
        result = []
        for a in articles:
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


# --- Sentiment Page (GUI) ---
class SentimentPage(QWidget):
    def __init__(self):
        super().__init__()
        self.analyzer = SentimentAnalyzer()
        self.worker = None
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

        # Search/Input Layout
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter a single ticker (e.g., RELIANCE, TCS)")
        self.search_input.setMinimumHeight(36)
        self.search_input.setStyleSheet("padding: 6px; font-size: 14px; background-color: #2D3748; color: #E2E8F0; border: 1px solid #4A5568; border-radius: 8px;")
        search_layout.addWidget(self.search_input)

        self.search_button = QPushButton("🔍 Search Ticker")
        self.search_button.setStyleSheet(self.button_style("#4299E1"))
        self.search_button.clicked.connect(self.search_ticker_news)
        search_layout.addWidget(self.search_button)
        main_layout.addLayout(search_layout)

        # Action Buttons Layout (Trending / Top 20 / Custom)
        action_layout = QHBoxLayout()

        # Trending Button (Original 5-6 stocks) - EMOJI REMOVED
        self.trending_button = QPushButton("Top 5 Trending News")
        self.trending_button.setStyleSheet(self.button_style("#D69E2E"))
        self.trending_button.clicked.connect(self.show_trending_news)
        action_layout.addWidget(self.trending_button)

        # Button for Top 20 Stocks - EMOJI REMOVED
        self.top20_button = QPushButton("Top 20 Stocks News")
        self.top20_button.setStyleSheet(self.button_style("#38A169"))
        self.top20_button.clicked.connect(self.show_top20_news)
        action_layout.addWidget(self.top20_button)
        
        # NEW: Button for User's Custom Bulk List (Max 30)
        self.custom_button = QPushButton(f"🗃️ Custom Bulk Fetch (Max {MAX_CUSTOM_FETCH})")
        self.custom_button.setStyleSheet(self.button_style("#9F7AEA")) # Purple
        self.custom_button.clicked.connect(self.show_custom_news)
        action_layout.addWidget(self.custom_button)

        main_layout.addLayout(action_layout)

        # Market Mood Summary Label
        self.summary_label = QLabel("Ready to fetch news.")
        self.summary_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.summary_label.setStyleSheet("color: #CBD5E0; padding-top: 10px; padding-bottom: 5px;")
        main_layout.addWidget(self.summary_label)


        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Ticker", "Headline (Click to Open)", "Sentiment", "Score", "Source"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Table Styling
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1A202C; color: #E2E8F0; border: 1px solid #4A5568; }
            QHeaderView::section { background-color: #2D3748; color: #E2E8F0; padding: 6px; font-weight: bold; border: 1px solid #4A5568; }
            QTableWidget::item { padding: 4px; }
            QTableWidget::item:selected { background-color: #4A5568; }
        """)

        # Resize modes
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
            QLabel { background-color: rgba(0,0,0,180); color:white;
                     font-size:18px; font-weight:bold; border-radius:10px; padding:15px; }
        """)
        self.loading_label.hide()
        main_layout.addWidget(self.loading_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setMinimumSize(QSize(1000, 650))

        # Load a default view initially
        self.show_trending_news()

    def button_style(self, color):
        """Generates a consistent style for buttons."""
        return f"""
            QPushButton {{ background-color: {color}; color:white; border-radius:10px; padding:8px 16px; font-weight:bold; }}
            QPushButton:hover {{ background-color: {color[:-2]}B0; }} /* Slightly lighter on hover */
            QPushButton:pressed {{ background-color: {color[:-2]}90; }} /* Slightly darker on press */
        """

    def show_loading(self, text="⏳ Fetching news..."):
        """Shows the loading indicator."""
        self.loading_label.setText(text)
        self.loading_label.show()
        # No QApplication.processEvents() needed as fetching is async

    def hide_loading(self):
        """Hides the loading indicator."""
        self.loading_label.hide()

    def search_ticker_news(self):
        """Handles single ticker search."""
        ticker = self.search_input.text().strip().upper()
        if not ticker:
            QMessageBox.warning(self, "Input Required", "Enter a ticker symbol.")
            return
        self.fetch_news_async([ticker])

    def show_trending_news(self):
        """Fetches news for a small, manually curated list."""
        tickers = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        self.fetch_news_async(tickers, title="Trending")

    def show_top20_news(self):
        """Fetches news for the larger list of 20 top stocks."""
        self.fetch_news_async(TOP_20_STOCKS, title="Top 20 Stocks")

    def show_custom_news(self):
        """Fetches news for the large user-provided list, applying a max limit."""
        
        # Use only the first MAX_CUSTOM_FETCH tickers to prevent rate limit exhaustion
        tickers = USER_CUSTOM_STOCKS[:MAX_CUSTOM_FETCH] 
        
        if len(USER_CUSTOM_STOCKS) > MAX_CUSTOM_FETCH:
             QMessageBox.information(self, "Limit Applied", 
                                     f"The custom list contains {len(USER_CUSTOM_STOCKS)} stocks, "
                                     f"which is too large for a single run due to API limits. "
                                     f"Fetching news for the first {MAX_CUSTOM_FETCH} stocks only. "
                                     f"Rerun the task with a subset of the list if you need to analyze others.")
                                     
        self.fetch_news_async(tickers, title="Custom Bulk")

    def fetch_news_async(self, tickers, title="Search"):
        """Starts the news fetching worker thread."""
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Busy", "A news fetch operation is already running. Please wait.")
            return

        self.show_loading(f"⏳ Fetching {len(tickers)} tickers for {title}...")
        self.table.clearContents()
        self.table.setRowCount(0)
        self.summary_label.setText(f"Fetching news for {len(tickers)} tickers...")
        
        self.worker = NewsWorker(tickers)
        self.worker.result_ready.connect(self._update_table)
        self.worker.error_occurred.connect(lambda e: self.handle_worker_error(e))
        self.worker.finished.connect(self.hide_loading)
        self.worker.start()

    def handle_worker_error(self, message):
        """Handles and displays worker thread errors."""
        QMessageBox.warning(self, "Error During Fetch", f"An error occurred: {message}")
        self.hide_loading()
        self.summary_label.setText("Error fetching data. Check console for details.")

    def _update_table(self, data):
        """Populates the QTableWidget with data and calculates the summary."""
        self.table.setRowCount(len(data))
        self.table.setHorizontalHeaderLabels(["Ticker", "Headline (Click to Open)", "Sentiment", "Score", "Source"])
        
        # New Feature: Calculate Overall Sentiment Summary
        total_articles = len(data)
        total_score_sum = sum(item['score'] for item in data)
        
        if total_articles > 0:
            average_score = total_score_sum / total_articles
            
            if average_score >= 0.05:
                overall_mood = "Positive"
                mood_color = "#22c55e"  # Green
            elif average_score <= -0.05:
                overall_mood = "Negative"
                mood_color = "#ef4444"  # Red
            else:
                overall_mood = "Neutral"
                mood_color = "#eab308"  # Yellow
                
            summary_text = (
                f"Overall Market Mood (based on {total_articles} articles): "
                f"<span style='color: {mood_color}; font-size: 14px;'>{overall_mood} "
                f"({average_score:.4f})</span>"
            )
        else:
            summary_text = "No articles found or API limit reached."
            
        self.summary_label.setText(summary_text)


        # Sort data to group by Ticker for better readability
        data.sort(key=lambda x: x['ticker'])

        for i, item in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(item["ticker"]))
            
            # Headline item, stores URL in UserRole
            text_item = QTableWidgetItem(item["text"])
            text_item.setFlags(text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if item.get("url"):
                text_item.setData(Qt.ItemDataRole.UserRole, item["url"])
            self.table.setItem(i, 1, text_item)

            # Sentiment item with color coding
            sentiment_item = QTableWidgetItem(item["sentiment"].capitalize())
            color_map = {"positive": "#22c55e", "negative": "#ef4444", "neutral": "#eab308"}
            sentiment_item.setForeground(QColor(color_map.get(item["sentiment"], "#eab308")))
            self.table.setItem(i, 2, sentiment_item)

            self.table.setItem(i, 3, QTableWidgetItem(f"{item['score']:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(item["source"]))

    def open_article(self, row, column):
        """Opens the article URL when the Headline cell is clicked."""
        if column == 1:
            item = self.table.item(row, column)
            if item:
                url = item.data(Qt.ItemDataRole.UserRole)
                if url:
                    QDesktopServices.openUrl(QUrl(url))
                    
# --- Application Startup ---
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    
    # Set a modern, clean palette for the app
    app.setStyle("Fusion")
    
    # Create the main window
    window = QWidget()
    main_layout = QVBoxLayout(window)
    
    sentiment_page = SentimentPage()
    main_layout.addWidget(sentiment_page)
    
    window.setWindowTitle("Advanced Financial Sentiment Analyzer")
    window.show()
    
    sys.exit(app.exec())
