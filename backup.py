import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta

st.title("📊 Dividend-Based Stock Analyzer")

ticker = st.text_input("Enter Stock Ticker (e.g., KO)")

if ticker:
    stock = yf.Ticker(ticker)
    hist = stock.history(period="5y")
    dividends = stock.dividends

    # Lowest price in 5 years
    lowest_row = hist["Close"].idxmin()
    lowest_price = hist["Close"].min()
    st.write(f"📉 Lowest Price: ${lowest_price:.2f} on {lowest_row.date()}")

    # Dividend payout from lowest date to 1 year forward
    start = lowest_row
    end = start + timedelta(days=365)
    div_period = dividends[(dividends.index >= start) & (dividends.index <= end)]
    total_div = div_period.sum()
    yield_low = total_div / lowest_price

    st.write(f"💰 Dividend from {start.date()} to {end.date()}: ${total_div:.2f}")
    st.write(f"📈 Yield at Lowest Price: {yield_low:.2%}")

    # Current price and yield
    current_price = hist["Close"][-1]
    annual_div = dividends[-4:].sum()  # Approximate annual dividend
    yield_current = annual_div / current_price

    st.write(f"🟢 Current Price: ${current_price:.2f}")
    st.write(f"🟡 Current Dividend Yield: {yield_current:.2%}")

    # Valuation
    if yield_current < yield_low:
        st.markdown("🔴 **Stock appears overvalued based on dividend yield.**")
    else:
        st.markdown("🟢 **Stock appears undervalued based on dividend yield.**")

    # Collapsed table
    with st.expander("📁 View 5-Year Summary Table"):
        st.dataframe(hist[["Close"]].resample("Y").mean().rename(columns={"Close": "Avg Close"}))