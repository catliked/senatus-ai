import yfinance as yf

# Pre-fetched fallback data for demo reliability
MOCK_DATA = {
    "NVDA": {
        "ticker": "NVDA",
        "price": 875.39,
        "pe_ratio": 68.4,
        "forward_pe": 35.2,
        "52w_high": 974.00,
        "52w_low": 439.00,
        "revenue_growth": 0.122,
        "debt_to_equity": 42.0,
        "profit_margins": 0.553,
        "market_cap": 2150000000000,
        "analyst_target_price": 950.00,
        "recommendation": "buy",
        "news": [
            "NVIDIA Reports Record Revenue of $44.1 Billion, Up 78% YoY",
            "NVIDIA Blackwell GPU Demand Outstrips Supply Through 2025",
            "NVIDIA Partners with Every Major Cloud Provider for AI Infrastructure",
            "Analysts Raise NVIDIA Price Targets After Strong Q4 Beat",
            "NVIDIA CEO Jensen Huang: AI Infrastructure Spending 'Insatiable'",
        ],
    },
    "AAPL": {
        "ticker": "AAPL",
        "price": 189.30,
        "pe_ratio": 29.1,
        "forward_pe": 26.8,
        "52w_high": 199.62,
        "52w_low": 164.08,
        "revenue_growth": 0.021,
        "debt_to_equity": 140.0,
        "profit_margins": 0.263,
        "market_cap": 2910000000000,
        "analyst_target_price": 205.00,
        "recommendation": "buy",
        "news": [
            "Apple Intelligence Features Rollout Continues Across iOS 18",
            "Apple Reports Q1 Revenue of $119.6 Billion, iPhone Sales Mixed",
            "Apple Vision Pro Sales Underwhelm; Company Pivots to Lower-Cost Model",
            "Analysts Debate Apple's AI Monetization Strategy for 2025",
            "Apple Services Revenue Hits All-Time High at $26.3 Billion",
        ],
    },
    "TSLA": {
        "ticker": "TSLA",
        "price": 248.50,
        "pe_ratio": 62.1,
        "forward_pe": 78.5,
        "52w_high": 414.50,
        "52w_low": 138.80,
        "revenue_growth": -0.071,
        "debt_to_equity": 18.0,
        "profit_margins": 0.056,
        "market_cap": 793000000000,
        "analyst_target_price": 215.00,
        "recommendation": "hold",
        "news": [
            "Tesla Q4 Deliveries Miss Estimates for Second Consecutive Quarter",
            "Tesla Announces Robotaxi Launch in Austin — Limited Beta",
            "Elon Musk's Commitment to Tesla Questioned Amid X and xAI Distractions",
            "Tesla Cuts Prices Again in China Amid Intensifying BYD Competition",
            "Tesla FSD V13 Shows Improvement But Full Autonomy Timeline Unclear",
        ],
    },
}


def get_stock_data(ticker: str) -> dict:
    ticker = ticker.upper().strip()
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            raise ValueError("Empty response from yfinance")

        news_raw = stock.news[:5] if stock.news else []
        news_titles = []
        for n in news_raw:
            if isinstance(n, dict):
                if "content" in n and isinstance(n["content"], dict) and "title" in n["content"]:
                    news_titles.append(n["content"]["title"])
                elif "title" in n:
                    news_titles.append(n["title"])

        data = {
            "ticker": ticker,
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "revenue_growth": info.get("revenueGrowth"),
            "debt_to_equity": info.get("debtToEquity"),
            "profit_margins": info.get("profitMargins"),
            "market_cap": info.get("marketCap"),
            "analyst_target_price": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey"),
            "news": news_titles,
        }

        return {k: v for k, v in data.items() if v is not None}

    except Exception as e:
        print(f"[WARN] yfinance failed for {ticker}: {e}. Falling back to mock data.")
        if ticker in MOCK_DATA:
            return MOCK_DATA[ticker]
        # Return generic mock if ticker not in our set
        base = MOCK_DATA["NVDA"].copy()
        base["ticker"] = ticker
        return base


def format_market_cap(mc: float | None) -> str:
    if mc is None:
        return "N/A"
    if mc >= 1e12:
        return f"${mc/1e12:.2f}T"
    if mc >= 1e9:
        return f"${mc/1e9:.2f}B"
    return f"${mc/1e6:.2f}M"


def format_stock_summary(data: dict) -> str:
    """Human-readable summary of raw stock data for injection into Band room."""
    ticker = data.get("ticker", "?")
    price = data.get("price")
    pe = data.get("pe_ratio")
    fpe = data.get("forward_pe")
    high = data.get("52w_high")
    low = data.get("52w_low")
    rev_growth = data.get("revenue_growth")
    de = data.get("debt_to_equity")
    margins = data.get("profit_margins")
    mc = data.get("market_cap")
    target = data.get("analyst_target_price")
    rec = data.get("recommendation", "N/A")
    news = data.get("news", [])

    lines = [
        f"=== RAW MARKET DATA: {ticker} ===",
        f"Price: ${price:.2f}" if price else "Price: N/A",
        f"Market Cap: {format_market_cap(mc)}",
        f"Trailing P/E: {pe:.1f}" if pe else "Trailing P/E: N/A",
        f"Forward P/E: {fpe:.1f}" if fpe else "Forward P/E: N/A",
        f"52W Range: ${low:.2f} – ${high:.2f}" if low and high else "52W Range: N/A",
        f"Revenue Growth (YoY): {rev_growth*100:.1f}%" if rev_growth else "Revenue Growth: N/A",
        f"Debt/Equity: {de:.1f}" if de else "Debt/Equity: N/A",
        f"Profit Margin: {margins*100:.1f}%" if margins else "Profit Margin: N/A",
        f"Analyst Target: ${target:.2f}" if target else "Analyst Target: N/A",
        f"Analyst Consensus: {rec.upper()}",
        "",
        "Recent Headlines:",
    ] + [f"  - {h}" for h in news]

    return "\n".join(lines)
