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
                if password in ["Password123", "Pei1234!"]:
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
    
    hide_textinput = False

    if "raw_input" not in st.session_state:
        st.session_state["raw_input"] = ""

    # Define default input
    default_input = ""

    with st.container(border=True):
        cols = st.columns(4)

        with cols[0]:
            if st.button("📥 Pei Stocks"):
                reits = [
                    "F9D.si", "C38U.si", "9CI.si", "C52.si", "TCU.si", "P34.si", "F99.si", "H02.si", "H13.si", "H78.si",
                    "C07.si", "J36.si", "CJLU.si", "Q01.si", "S61.si", "OV8.si", "S68.si", "S63.si", "Y92.si", "AGS.si",
                    "WJP.si", "F34.si", "BSL.si"
                ]
                st.session_state["raw_input"] = " ".join(reits)

        with cols[1]:
            if st.button("📥 Jay Stocks"):
                reits = [
                    "TGT", "GOOGL", "GRAB", "TSLA", "DIS"
                ]
                st.session_state["raw_input"] = " ".join(reits)

    # Use default_input only if it's set by the button
    raw_input = st.text_input(
        "Enter stock tickers (e.g., AAPL MSFT, KO, D05.SI)",
        value=st.session_state["raw_input"]
    )

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
                return "Bullish"
            elif avg_score < -0.2:
                return "Bearish"
            else:
                return "Neutral"
        except:
            return "Unknown"

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
            yield_5y = (payout_5y / low_5y_price) if low_5y_price else 0

            target_actual = (current_price * (dividend_yield/100) / yield_5y) if yield_5y else 0

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

    def highlight_current_price(row):
        try:
            price = row["Current Price"]
            target = row["Target Price (Actual)"]
            if pd.isna(target) or target == 0:
                return ''
            elif price >= target:
                return 'color: white; background-color: #800000'  # dark maroon
            else:
                return 'color: white; background-color: #006400'  # dark green
        except KeyError:
            return ''


    def highlight_sentiment(val):
        Sentiment = val.strip()
        if Sentiment == "Bullish":
            return 'color: white; background-color: #006400'  # dark green
        elif Sentiment == "Bearish":
            return 'color: white; background-color: #800000'  # dark maroon
        else:
            return ''   

    if tickers:
        results = [r for t in tickers if (r := analyze_ticker(t)) is not None]
        df = pd.DataFrame(results)

        desired_order = [
            "Ticker", "Name",  "Sector", "Industry",  "Current Price", "Sentiment", "Trailing EPS", "Forward EPS", 
            "Dividend Yield (%)", "5Y Low Date", "5Y Low Price", "5Y Dividend Payout", "5Y Dividend Yield (%)",
            "PE Ratio", "PEG Ratio", "Price Zone (%)", "Target Price (Actual)"
        ]
        df = df[desired_order]

        if "Target Price (Actual)" not in df.columns:
            df["Target Price (Actual)"] = 0.0

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
            }) \
            .applymap(highlight_sentiment, subset=["Sentiment"]) \
            .applymap(lambda val: highlight_current_price(df.loc[df["Current Price"] == val].iloc[0]), subset=["Current Price"])

        st.markdown("##### 🗄️ Export Database")

        st.dataframe(styled_df, use_container_width=True)

        if messages:
            st.markdown("---")
            for msg_type, msg_text in messages:
                if msg_type == "warning":
                    st.warning(msg_text)
                elif msg_type == "error":
                    st.error(msg_text)

    toggle = st.toggle("Activate Chart Analysis?", value=True)

    if toggle:
    
        # 📈 Enhanced Price Tracker
        if not len(tickers) == 0:
            st.markdown("#### 📈 Chart Analysis")
            
            ticker_list = df["Ticker"].tolist()
            selected_ticker = ticker_list[0] if ticker_list else None  # default to first

            if not len(tickers) == 1:
                # ⏳ List of stocks
                with st.container(border=True):
                    st.markdown("###### 🎯 Select a Stock")

                    if len(ticker_list) > 20:
                        selected_ticker = st.selectbox("Select a ticker to view chart", ticker_list)
                    else:
                        num_cols = 5  # max 5 buttons per row
                        rows = (len(ticker_list) + num_cols - 1) // num_cols  # ceiling division

                        for row in range(rows):
                            cols = st.columns(num_cols)
                            for i in range(num_cols):
                                idx = row * num_cols + i
                                if idx < len(ticker_list):
                                    ticker = ticker_list[idx]
                                    if cols[i].button(ticker):
                                        selected_ticker = ticker


            # 📦 Container 2: Year Toggle + Chart
            with st.container(border=True):
                st.markdown("##### 📈 Price Range Tracker")

                layout = st.columns([1, 4])  # col0 = year toggle, col1 = chart

                # ⏳ Year Toggle in col0
                with layout[0]:
                    # st.markdown("###### Period")
                    st.markdown("######")
                    year_range = 3  # default
                    year_buttons = [1, 2, 3, 4, 5]

                    for yr in year_buttons:
                        if st.button(f"{yr} Year{'s' if yr > 1 else ''}"):
                            year_range = yr


                # 📊 Chart + Analysis
                with layout[1]:
                    import plotly.graph_objects as go

                    stock = yf.Ticker(selected_ticker)
                    current_price = stock.info.get("currentPrice", None)
                    company_name = stock.info.get("shortName", "Unknown Company")
                    end_date = datetime.today().replace(tzinfo=None)
                    start_date = end_date - timedelta(days=365 * year_range)
                    hist = stock.history(start=start_date, end=end_date)

                    if not hist.empty:
                        # 🧮 Monthly high/low
                        monthly = hist.resample("M").agg({"Low": "min", "High": "max"}).dropna()

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

                        # 📐 Year-Specific Dividend-Based Target Price
                        dividends = stock.dividends
                        if dividends.index.tz is not None:
                            dividends.index = dividends.index.tz_convert(None)

                        target_prices = []
                        analysis_start = end_date - timedelta(days=365 * year_range)
                        daily_close.index = daily_close.index.tz_convert(None)
                        analysis_data = daily_close[(daily_close.index >= analysis_start) & (daily_close.index <= end_date)]

                        if not analysis_data.empty:
                            low_price = analysis_data["Daily Close"].min()
                            low_date = analysis_data["Daily Close"].idxmin()
                            if low_date.tzinfo is not None:
                                low_date = low_date.replace(tzinfo=None)

                            payout_window_start = low_date - timedelta(days=366)
                            payout_window_end = low_date
                            payouts = dividends[(dividends.index >= payout_window_start) & (dividends.index <= payout_window_end)]
                            total_payout = payouts.sum()
                            total_payout_yield = total_payout / low_price

                            div_yield = stock.info.get("dividendYield", 0) or 0
                            target_price = (current_price * (div_yield / 100)) / total_payout_yield if div_yield else 0
                            target_prices.append((low_date.year, target_price))

                            safe_zone_90 = (current_price * (div_yield / 100)) / (total_payout_yield * 0.9) if div_yield else 0
                            safe_zone_80 = (current_price * (div_yield / 100)) / (total_payout_yield * 0.8) if div_yield else 0

                        # 🧾 Display Summary
                        if target_prices:
                            year_used, latest_target = target_prices[-1]
                        # 📈 Plotly Chart
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=daily_close.index, y=daily_close["Daily Close"], mode='lines', name='Daily Close'))
                        fig.add_trace(go.Scatter(x=daily_close.index, y=daily_close["Monthly High"], mode='lines', name='Monthly High', line=dict(dash='dash')))
                        fig.add_trace(go.Scatter(x=daily_close.index, y=daily_close["Monthly Low"], mode='lines', name='Monthly Low', line=dict(dash='dash')))

                        if target_prices and latest_target > 0:
                            fig.add_hline(
                                y=latest_target,
                                line=dict(color="green", dash="dot")
                            )

                            fig.add_hline(
                                y=safe_zone_90,
                                line=dict(color="purple", dash="dot")
                            )

                            fig.add_hline(
                                y=safe_zone_80,
                                line=dict(color="red", dash="dot")
                            )

                            fig.add_annotation(
                                text=f"🎯 Target Price ({year_used}): ${latest_target:.2f}",
                                xref="paper", yref="paper",
                                x=0, y=-0.01,
                                showarrow=False,
                                font=dict(color="limegreen", size=12),
                                align="left",
                                bgcolor="rgba(0,128,0,0.15)",
                                bordercolor="green",
                                borderwidth=1
                            )

                            # 🟪 Safe Zone 90% (Purple)
                            fig.add_annotation(
                                text=f"Safe: ${safe_zone_90:.2f}",
                                xref="paper", yref="paper",
                                x=0.6, y=-0.01,
                                showarrow=False,
                                font=dict(color="purple", size=12),
                                align="left",
                                bgcolor="rgba(128,0,128,0.15)",
                                bordercolor="purple",
                                borderwidth=1
                            )

                            # 🟥 Safe Zone 80% (Red)
                            fig.add_annotation(
                                text=f"Moderate: ${safe_zone_80:.2f}",
                                xref="paper", yref="paper",
                                x=1, y=-0.01,
                                showarrow=False,
                                font=dict(color="red", size=12),
                                align="left",
                                bgcolor="rgba(255,0,0,0.15)",
                                bordercolor="red",
                                borderwidth=1
                            )

                        fig.update_layout(
                            title=dict(
                                text=f"<u><b>{company_name} ({selected_ticker})</b></u> (📊 {year_range} Year{'s' if year_range > 1 else ''} Trend) <br> {trend} ({pct_change:.2f}%)",
                                x=0.5,
                                xanchor="center"
                            ),
                            xaxis_title="Date",
                            yaxis_title="Price",
                            legend_title="Legend",
                            height=500
                        )

                        st.plotly_chart(fig, use_container_width=True)
                        
                        with st.container(border=True):
                            st.markdown("##### 📊 Technical Summary")

                            with st.container(border=True):
                                col1, col2 = st.columns(2)

                                with col1:
                                    st.markdown(f"**💰 Current Price:** ${current_price:.2f}")
                                    st.markdown(f"**📈 Current Dividend Yield:** {div_yield:.2f}%")
                                    currentdiv_payout = current_price * (div_yield / 100)
                                    st.markdown(f"**📦 Current Dividend Payout:** ${currentdiv_payout:.2f}")

                                with col2:
                                    st.markdown(f"**📅 Low Date:** {low_date.strftime('%Y-%m-%d')}")
                                    st.markdown(f"**📉 Yearly Low Price:** ${low_price:.2f}")
                                    st.markdown(f"**📐 Historical Payout Yield:** {total_payout_yield * 100:.2f}%")
                                    st.markdown(f"**📦 Yearly Low Payout:** ${total_payout:.2f}")
                                
                    else:
                        st.warning(f"No historical data available for {selected_ticker}.")

    yield_toggle = st.toggle("Activate Dividend Yield Deep Dive?", value=True)

    if yield_toggle:
        if not len(tickers) == 0:
            def get_yield_analysis(ticker):
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    current_price = info.get("currentPrice", 0)
                    dividend_yield = info.get("dividendYield", 0) or 0
                    current_payout = current_price * (dividend_yield / 100)

                    # Historical dividend yield extremes
                    dividends = stock.dividends
                    prices = stock.history(period="max")["Close"]

                    if dividends.empty or prices.empty:
                        return None

                    dividends.index = dividends.index.tz_convert(None) if dividends.index.tz else dividends.index
                    prices.index = prices.index.tz_convert(None) if prices.index.tz else prices.index

                    yield_data = []
                    for date in dividends.index:
                        price_on_date = prices.loc[prices.index.asof(date)] if date in prices.index else None
                        if price_on_date:
                            yield_pct = (dividends[date] / price_on_date) * 100
                            yield_data.append((date, yield_pct, price_on_date))

                    if not yield_data:
                        return None

                    high_yield = max(yield_data, key=lambda x: x[1])
                    low_yield = min(yield_data, key=lambda x: x[1])

                    debt_ratio = info.get("debtToEquity", None)

                    return {
                        "Ticker": ticker,
                        "Name": info.get("shortName", "N/A"),
                        "Current Price": f"${current_price:.2f}",
                        "Current Dividend Yield (%)": f"{dividend_yield:.2f}%",
                        "Current Dividend Payout": f"${current_payout:.3f}",
                        "Debt Servicing Ratio": f"{debt_ratio:.2f}" if debt_ratio else "N/A",
                        "High Yield (%)": f"{high_yield[1]:.2f}%",
                        "High Yield Date": high_yield[0].date(),
                        "High Yield Price": f"${high_yield[2]:.2f}",
                        "Low Yield (%)": f"{low_yield[1]:.2f}%",
                        "Low Yield Date": low_yield[0].date(),
                        "Low Yield Price": f"${low_yield[2]:.2f}",
                        "High - Current Yield (%)": f"{high_yield[1] - dividend_yield:.2f}%",
                        "Low - Current Yield (%)": f"{low_yield[1] - dividend_yield:.2f}%"

                    }
                except Exception as e:
                    messages.append(("error", f"❌ Error in yield analysis for {ticker}: {e}"))
                    return None

            st.markdown("##### 🧮 Dividend Yield Deep Dive")

            yield_results = [get_yield_analysis(t) for t in tickers if t]
            yield_results = [r for r in yield_results if r]

            if yield_results:
                yield_df = pd.DataFrame(yield_results)
                st.dataframe(yield_df, use_container_width=True)
            else:
                st.warning("No yield data available for selected tickers.")