import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import re
import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

st.set_page_config(page_title="Stock Analysis App", layout="wide")

# 🛡️ Session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "login_success" not in st.session_state:
    st.session_state.login_success = False

# 🔐 Login
if not st.session_state.logged_in:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        with st.form("login_form", clear_on_submit=False):
            st.markdown("#### 🔐 Login to Stock Analysis")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if password == "Password123":
                    st.session_state.logged_in = True
                    st.session_state.login_success = True
                else:
                    st.error("Invalid credentials.")

# ✅ Main App
if st.session_state.logged_in:
    if st.session_state.login_success:
        st.success("Login successful! 🎉")
        st.session_state.login_success = False

    st.markdown("## 📊 Stock Analysis Dashboard")

    raw_input = st.text_input("Enter stock tickers (e.g., AAPL MSFT, KO)")
    tickers = re.split(r'[,\s]+', raw_input.upper().strip())
    tickers = [t for t in tickers if t]

    messages = []
    analyzer = SentimentIntensityAnalyzer()

    def get_dividend_payout(ticker, low_date):
        start = low_date - timedelta(days=365)
        end = low_date
        hist = yf.Ticker(ticker).dividends
        payout = hist[(hist.index >= start) & (hist.index <= end)].sum()
        return payout

    def get_eps_metrics(stock):
        info = stock.info
        eps_data = {}
        try:
            eps_data["Trailing EPS"] = round(info.get("trailingEps", 0), 2)
            eps_data["Forward EPS"] = round(info.get("forwardEps", 0), 2)
            eps_data["PE Ratio"] = round(info.get("trailingPE", 0), 2)
            eps_data["PEG Ratio"] = round(info.get("pegRatio", 0), 2)
        except:
            pass
        return eps_data

    def get_sentiment(ticker):
        try:
            url = f"https://finviz.com/quote.ashx?t={ticker}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            soup = BeautifulSoup(requests.get(url, headers=headers).content, "html.parser")
            news_table = soup.find(id='news-table')
            headlines = [row.a.text for row in news_table.findAll('tr') if row.a]
            scores = [analyzer.polarity_scores(h)['compound'] for h in headlines[:10]]
            avg_score = sum(scores) / len(scores) if scores else 0
            if avg_score > 0.2:
                return "🟢 Bullish"
            elif avg_score < -0.2:
                return "🔴 Bearish"
            else:
                return "🟡 Neutral"
        except:
            return "⚪ Unknown"

    def analyze_ticker(ticker):
        ticker = ticker.strip()
        if not re.match(r'^[A-Z0-9\-\.]+$', ticker):
            messages.append(("warning", f"⚠️ Invalid ticker: {ticker}"))
            return None

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            if not info or "currentPrice" not in info:
                messages.append(("warning", f"⚠️ No data for: {ticker}"))
                return None

            name = info.get("shortName", "N/A")
            sector = info.get("sector", "N/A")
            industry = info.get("industry", "N/A")
            current_price = info.get("currentPrice", 0)
            dividend_yield = info.get("dividendYield", 0) or 0
            high_52 = info.get("fiftyTwoWeekHigh", 0)
            low_52 = info.get("fiftyTwoWeekLow", 0)
            price_zone = ((current_price - low_52) / (high_52 - low_52)) * 100 if high_52 != low_52 else 0

            hist = stock.history(period="5y")
            if hist.empty:
                messages.append(("warning", f"⚠️ No historical data for: {ticker}"))
                return None

            low_5y_price = hist["Close"].min()
            low_5y_date = hist["Close"].idxmin()
            payout_5y = get_dividend_payout(ticker, low_5y_date)
            yield_5y = (payout_5y / low_5y_price) * 100 if low_5y_price else 0

            target_actual = (current_price * dividend_yield / yield_5y) if yield_5y else 0

            result = {
                "Ticker": ticker,
                "Name": name,
                "Sector": sector,
                "Industry": industry,
                "Current Price": round(current_price, 2),
                "Price Zone (%)": round(price_zone, 2),
                "Dividend Yield (%)": round(dividend_yield, 2),
                "52W High": round(high_52, 2),
                "52W Low": round(low_52, 2),
                "5Y Low Date": low_5y_date.date(),
                "5Y Low Price": round(low_5y_price, 2),
                "5Y Dividend Payout": round(payout_5y, 2),
                "5Y Dividend Yield (%)": round(yield_5y, 2),
                "Target Price (Actual)": round(target_actual, 2),
                "Sentiment": get_sentiment(ticker)
            }

            result.update(get_eps_metrics(stock))
            return result

        except Exception as e:
            messages.append(("error", f"❌ Error analyzing {ticker}: {e}"))
            return None

    if tickers:
        results = [r for t in tickers if (r := analyze_ticker(t)) is not None]
        df = pd.DataFrame(results)

        desired_order = [
            "Ticker", "Name", "Sector", "Industry",
            "Current Price", "Trailing EPS", "Forward EPS", "PE Ratio", "PEG Ratio",
            "Dividend Yield (%)", "5Y Dividend Yield (%)",
            "Price Zone (%)", "Sentiment",
            "Target Price (Actual)", "5Y Low Date", "5Y Low Price", "5Y Dividend Payout"
        ]
        df = df[desired_order]

        styled_df = df.style \
            .format({
                "Current Price": "{:.2f}",
                "5Y Low Price": "{:.2f}",
                "5Y Dividend Payout": "{:.2f}",
                "Target Price (Actual)": "{:.2f}",
                "Trailing EPS": "{:.2f}",
                "Forward EPS": "{:.2f}",
                "PE Ratio": "{:.2f}",
                "PEG Ratio": "{:.2f}",
                "Dividend Yield (%)": "{:.2f}%",
                "5Y Dividend Yield (%)": "{:.2f}%",
                "Price Zone (%)": "{:.2f}%"
            })

        st.dataframe(styled_df, use_container_width=True)

        if messages:
            st.markdown("---")
            for msg_type, msg_text in messages:
                if msg_type == "warning":
                    st.warning(msg_text)
                elif msg_type == "error":
                    st.error(msg_text)

    # 📈 Enhanced Price Tracker (Single Ticker Only)
    if len(tickers) == 1:
        st.markdown("### 📈 Price Range Tracker")

        year_range = st.select_slider("Select analysis period (years)", options=[1, 2, 3, 4, 5], value=1)
        selected_ticker = tickers[0]
        stock = yf.Ticker(selected_ticker)
        end_date = datetime.today()
        start_date = end_date - timedelta(days=365 * year_range)
        hist = stock.history(start=start_date, end=end_date)

        if not hist.empty:
            # 🧮 Monthly low/high
            monthly = hist.resample("M").agg({
                "Low": "min",
                "High": "max"
            }).dropna()

            # 📊 Daily close
            daily_close = hist[["Close"]].copy()
            daily_close.rename(columns={"Close": "Daily Close"}, inplace=True)

            # 🧩 Merge monthly high/low into daily timeline
            monthly["Date"] = monthly.index
            monthly = monthly.set_index(monthly["Date"].dt.to_period("M"))
            daily_close["Month"] = daily_close.index.to_period("M")
            daily_close["Monthly Low"] = daily_close["Month"].map(monthly["Low"])
            daily_close["Monthly High"] = daily_close["Month"].map(monthly["High"])
            daily_close.drop(columns=["Month"], inplace=True)

            st.line_chart(daily_close, use_container_width=True)

            # 📈 Trend Summary
            start_price = daily_close["Daily Close"].iloc[0]
            end_price = daily_close["Daily Close"].iloc[-1]
            pct_change = ((end_price - start_price) / start_price) * 100

            if pct_change > 5:
                trend = "📈 Upward"
            elif pct_change < -5:
                trend = "📉 Downward"
            else:
                trend = "➖ Stable"

            st.write(f"**Trend over {year_range} year(s):** {trend} ({pct_change:.2f}%)")
        else:
            st.warning(f"No historical data available for {selected_ticker}.")