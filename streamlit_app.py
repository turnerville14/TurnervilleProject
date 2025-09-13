import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="Dividend Analysis App", layout="wide")

# 🛡️ Session state initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "login_success" not in st.session_state:
    st.session_state.login_success = False

# 🔐 Login form
if not st.session_state.get("logged_in", False):
    # Create 3 columns and use the center one with enhanced container styling
    cols = st.columns([1, 2, 1])
    with cols[1]:
        # Apply border directly to the form container
        with st.form("login_form", clear_on_submit=False).container(border=False, height="stretch", vertical_alignment="center"):
            st.markdown("### 🔐 Login to Dividend Analysis")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                if username == "Admin" and password == "Password123":
                    st.session_state.logged_in = True
                    st.session_state.login_success = True
                else:
                    st.error("Invalid credentials. Please try again.")

# ✅ Main App Interface
if st.session_state.logged_in:
    if st.session_state.login_success:
        st.success("Login successful! 🎉")
        st.session_state.login_success = False  # Show message only once

    st.markdown("## 📊 Dividend Analysis App")

    # 🧾 User input
    raw_input = st.text_input("Enter stock tickers separated by commas or spaces (e.g., AAPL MSFT, KO)")
    tickers = re.split(r'[,\s]+', raw_input.upper().strip())
    tickers = [t for t in tickers if t]  # remove any empty strings

    # 📌 Collect messages to display later
    messages = []

    def get_dividend_payout(ticker, low_date):
        start = low_date - timedelta(days=365)
        end = low_date
        hist = yf.Ticker(ticker).dividends
        payout = hist[(hist.index >= start) & (hist.index <= end)].sum()
        return payout

    def analyze_ticker(ticker):
        ticker = ticker.strip()

        # 🚫 Skip if ticker contains special characters
        if not re.match(r'^[A-Z0-9\-\.]+$', ticker):
            messages.append(("warning", f"⚠️ Skipping invalid ticker: {ticker}"))
            return None

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # 🚫 Skip if info is empty or missing key data
            if not info or "currentPrice" not in info:
                messages.append(("warning", f"⚠️ No data available for: {ticker}"))
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
            target_safe = (current_price * dividend_yield / (yield_5y * 0.9)) if yield_5y else 0
            target_safest = (current_price * dividend_yield / (yield_5y * 0.8)) if yield_5y else 0
            strength = "Undervalued" if current_price < target_actual else "Overvalued"

            return {
                "Ticker": ticker,
                "Name": name,
                "Sector": sector,
                "Industry": industry,
                "Current Price": round(current_price, 2),
                "Stock Strength": strength,
                "Price Zone (%)": round(price_zone, 2),
                "Dividend Yield (%)": round(dividend_yield, 2),
                "52W High": round(high_52, 2),
                "52W Low": round(low_52, 2),
                "5Y Low Date": low_5y_date.date(),
                "5Y Low Price": round(low_5y_price, 2),
                "5Y Dividend Payout": round(payout_5y, 2),
                "5Y Dividend Yield (%)": round(yield_5y, 2),
                "Target Price (Actual)": round(target_actual, 2),
                "Target Price (Safe)": round(target_safe, 2),
                "Target Price (Safest)": round(target_safest, 2)
            }

        except Exception as e:
            messages.append(("error", f"❌ Error analyzing {ticker}: {e}"))
            return None

    if tickers and tickers[0]:
        results = [r for t in tickers if (r := analyze_ticker(t)) is not None]
        df = pd.DataFrame(results)

        def highlight_zone(val):
            if val < 35:
                return 'background-color: lightgreen; color: black;'
            elif 35 <= val <= 65:
                return 'background-color: lightyellow; color: black;'
            else:
                return 'background-color: lightcoral; color: black;'

        def highlight_strength(val):
            return 'background-color: lightgreen; color: black;' if val == "Undervalued" else 'background-color: lightcoral; color: black;'

        def format_currency(val):
            return f"${val:,.2f}"

        def format_percent(val):
            return f"{val:.2f}%"

        currency_cols = [
            "Current Price", "52W High", "52W Low",
            "5Y Low Price", "5Y Dividend Payout",
            "Target Price (Actual)", "Target Price (Safe)", "Target Price (Safest)"
        ]

        percent_cols = [
            "Dividend Yield (%)", "5Y Dividend Yield (%)", "Price Zone (%)"
        ]

        formatters = {col: format_currency for col in currency_cols}
        formatters.update({col: format_percent for col in percent_cols})

        styled_df = df.style \
            .applymap(highlight_zone, subset=["Price Zone (%)"]) \
            .applymap(highlight_strength, subset=["Stock Strength"]) \
            .format(formatters)

        st.dataframe(styled_df, use_container_width=True)

        # ✨ Visual separator before messages
        if messages:
            st.markdown("---")

        # 🚨 Show collected messages after the table
        for msg_type, msg_text in messages:
            if msg_type == "warning":
                st.warning(msg_text)
            elif msg_type == "error":
                st.error(msg_text)