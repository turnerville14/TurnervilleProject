import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.title("📊 Dividend Analysis App")

# 🧾 User input
tickers = st.text_input("Enter stock tickers separated by commas (e.g., AAPL, MSFT, KO)").upper().split(',')
st.set_page_config(layout="wide")

def get_dividend_payout(ticker, low_date):
    start = low_date - timedelta(days=365)
    end = low_date
    hist = yf.Ticker(ticker).dividends
    payout = hist[(hist.index >= start) & (hist.index <= end)].sum()
    return payout

def analyze_ticker(ticker):
    ticker = ticker.strip()
    stock = yf.Ticker(ticker)
    info = stock.info

    # Basic Info
    name = info.get("shortName", "N/A")
    current_price = info.get("currentPrice", 0)
    dividend_yield = info.get("dividendYield", 0) if info.get("dividendYield") else 0
    high_52 = info.get("fiftyTwoWeekHigh", 0)
    low_52 = info.get("fiftyTwoWeekLow", 0)

    # Price Zone
    price_zone = ((current_price - low_52) / (high_52 - low_52)) * 100 if high_52 != low_52 else 0

    # Historical Data
    hist = stock.history(period="5y")
    low_5y_price = hist["Close"].min()
    low_5y_date = hist["Close"].idxmin()

    # Dividend payout from 1 year before 5yr low date
    payout_5y = get_dividend_payout(ticker, low_5y_date)

    # 5yr low dividend yield
    yield_5y = (payout_5y / low_5y_price) * 100 if low_5y_price else 0

    # Target Prices
    target_actual = (current_price * dividend_yield / yield_5y) if yield_5y else 0
    target_safe = (current_price * dividend_yield / (yield_5y * 0.9)) if yield_5y else 0
    target_safest = (current_price * dividend_yield / (yield_5y * 0.8)) if yield_5y else 0

    # Stock Strength
    strength = "Undervalued" if current_price < target_actual else "Overvalued"

    return {
        "Ticker": ticker,
        "Name": name,
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

if tickers and tickers[0]:
    results = [analyze_ticker(t) for t in tickers]
    df = pd.DataFrame(results)

    # 🎨 Conditional formatting
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

    # Formatters
    def format_currency(val):
        return f"${val:,.2f}"

    def format_percent(val):
        return f"{val:.2f}%"

    # Columns
    currency_cols = [
        "Current Price", "52W High", "52W Low",
        "5Y Low Price", "5Y Dividend Payout",
        "Target Price (Actual)", "Target Price (Safe)", "Target Price (Safest)"]

    percent_cols = [
        "Dividend Yield (%)", "5Y Dividend Yield (%)", "Price Zone (%)"]

    # Combine formatters
    formatters = {col: format_currency for col in currency_cols}
    formatters.update({col: format_percent for col in percent_cols})

    df_display = df.reset_index(drop=True)

    styled_df = df_display.style \
        .applymap(highlight_zone, subset=["Price Zone (%)"]) \
        .applymap(highlight_strength, subset=["Stock Strength"]) \
        .format(formatters)

    st.dataframe(styled_df, use_container_width=True)