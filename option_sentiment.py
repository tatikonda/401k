import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import altair as alt

# --- CONFIG ---
FMP_API_KEY = "izAv7xiGjKzOoMIosExKA7Ia5RYkRtB3"  # <-- replace with your FMP API key
FMP_EARNINGS_URL = "https://financialmodelingprep.com/stable/earnings-calendar"

st.set_page_config(page_title="Earnings & Options Flow Sentiment Pro", page_icon="📊", layout="wide")

st.title("📈 Earnings & Options Flow Sentiment Pro")
st.markdown("""
Analyze **option sentiment, unusual activity**, and **price trends** for any stock or ETF.  
- Stocks → Based on **earnings proximity**  
- ETFs → Based on **option flow**
---
""")

# --- Dynamic Major Earnings Panel ---
st.subheader("📅 Major Earnings Upcoming (Next 1 Week & 30 Days)")

today = datetime.today()
one_week = today + timedelta(days=7)
thirty_days = today + timedelta(days=30)

try:
    params = {"from": today.strftime("%Y-%m-%d"),
              "to": thirty_days.strftime("%Y-%m-%d"),
              "apikey": FMP_API_KEY}
    resp = requests.get(FMP_EARNINGS_URL, params=params)
    if resp.status_code == 200:
        data = resp.json()
        df_earn = pd.DataFrame(data)
        if not df_earn.empty:
            df_earn['date'] = pd.to_datetime(df_earn['date']).dt.date
            earning_next_week = df_earn[(df_earn['date'] >= today.date()) & (df_earn['date'] <= one_week.date())]
            earning_next_30 = df_earn[(df_earn['date'] >= today.date()) & (df_earn['date'] <= thirty_days.date())]
            next_week_str = ", ".join(sorted(earning_next_week['symbol'].astype(str).unique()))
            next_30_str = ", ".join(sorted(earning_next_30['symbol'].astype(str).unique()))
            st.markdown(f"**Next 1 Week:** {next_week_str if next_week_str else 'None'}")
            st.markdown(f"**Next 30 Days:** {next_30_str if next_30_str else 'None'}")
        else:
            st.info("No major earnings found in the next 30 days.")
    else:
        st.warning("Could not fetch major earnings calendar from FMP.")
except Exception as e:
    st.warning(f"Error fetching earnings calendar: {e}")

st.markdown("---")

# --- Function to calculate sentiment ---
def calc_sentiment(calls, puts):
    total_call_vol = calls['volume'].sum()
    total_put_vol = puts['volume'].sum()
    total_call_oi = calls['openInterest'].sum()
    total_put_oi = puts['openInterest'].sum()

    vol_ratio = total_call_vol / total_put_vol if total_put_vol != 0 else 0.0
    oi_ratio = total_call_oi / total_put_oi if total_put_oi != 0 else 0.0

    score = ((vol_ratio / (vol_ratio + 1)) + (oi_ratio / (oi_ratio + 1))) * 50

    if vol_ratio > 1 and oi_ratio > 1:
        sentiment = "📈 Bullish"
        color = "green"
    elif vol_ratio < 1 and oi_ratio < 1:
        sentiment = "📉 Bearish"
        color = "red"
    else:
        sentiment = "⚖️ Neutral"
        color = "gray"

    return vol_ratio, oi_ratio, sentiment, color, score

# --- Main Ticker Input & Logic ---
ticker = st.text_input("Enter Stock or ETF Ticker (e.g. AAPL, NVDA, SPY, QQQ):", "").upper().strip()
ETF_TICKERS = {"SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLY", "XLP", "XLV", "XLI", "XLRE", "XLB", "XLU"}

if ticker:
    try:
        stock = yf.Ticker(ticker)

        # --- Current Price + Day High/Low + Chart with MA200 in One Row ---
        hist = stock.history(period="12mo", interval="1d")
        if not hist.empty:
            st.subheader(f"📊 Price Overview ({ticker})")
            col1, col2 = st.columns([1,3])

            with col1:
                regular_price = stock.info.get("regularMarketPrice", np.nan)
                day_high = stock.info.get("dayHigh", np.nan)
                day_low = stock.info.get("dayLow", np.nan)
                st.metric(label="💰 Current Price", value=regular_price, delta=f"Day High: {day_high} / Low: {day_low}")

            with col2:
                hist['MA200'] = hist['Close'].rolling(window=200).mean()
                hist_reset = hist.reset_index()
                price_chart = alt.Chart(hist_reset).mark_line().encode(
                    x='Date:T',
                    y='Close:Q',
                    tooltip=['Date:T','Close:Q','MA200:Q']
                )
                ma_chart = alt.Chart(hist_reset).mark_line(color='orange').encode(
                    x='Date:T',
                    y='MA200:Q',
                    tooltip=['Date:T','MA200:Q']
                )
                st.altair_chart(price_chart + ma_chart, width='stretch')

        # --- Determine if ETF ---
        stock_info = stock.info
        is_etf = ticker in ETF_TICKERS or stock_info.get("quoteType", "").upper() == "ETF"

        expirations = stock.options
        if not expirations:
            st.warning("No options data available for this ticker.")
        else:
            expiry_dates = [pd.to_datetime(e) for e in expirations]

            next_earnings = None
            if not is_etf:
                earnings_calendar = stock.earnings_dates
                if earnings_calendar is not None and not earnings_calendar.empty:
                    next_earnings = pd.to_datetime(earnings_calendar.index[0])
                    if getattr(next_earnings, "tz", None) is not None:
                        next_earnings = next_earnings.tz_convert(None)
                    st.subheader(f"📅 Next Earnings Date: `{next_earnings.date()}`")

            if next_earnings is not None:
                closest_expiry = min(expiry_dates, key=lambda x: abs((x - next_earnings).days))
            else:
                closest_expiry = expiry_dates[0]

            closest_expiry_str = closest_expiry.strftime("%Y-%m-%d")
            st.markdown(f"**Analyzing Closest Expiry:** `{closest_expiry_str}`")

            selected_expiries = st.multiselect(
                "Select expirations to analyze:",
                options=expirations,
                default=[closest_expiry_str],
                max_selections=3
            )

            # --- Sentiment Calculation ---
            sentiment_data = []
            for expiry in selected_expiries:
                opt_chain = stock.option_chain(expiry)
                calls, puts = opt_chain.calls, opt_chain.puts
                vol_ratio, oi_ratio, sentiment, color, score = calc_sentiment(calls, puts)
                sentiment_data.append({
                    "Expiry": expiry,
                    "Vol Ratio": round(vol_ratio,2),
                    "OI Ratio": round(oi_ratio,2),
                    "Sentiment": sentiment,
                    "Score (0‑100)": round(score,1)
                })

            sentiment_df = pd.DataFrame(sentiment_data)
            st.dataframe(sentiment_df, width='stretch')

            # --- Weighted Sentiment ---
            st.markdown("---")
            st.markdown("### 🧮 Weighted Sentiment Score")
            valid_scores = [d["Score (0‑100)"] for d in sentiment_data if not np.isnan(d["Score (0‑100)"])]
            avg_score = np.nan if not valid_scores else np.mean(valid_scores)
            if np.isnan(avg_score):
                overall = "⚠️ Insufficient Data"
                color = "gray"
            elif avg_score >= 60:
                overall = "📈 Bullish"
                color = "green"
            elif avg_score <= 40:
                overall = "📉 Bearish"
                color = "red"
            else:
                overall = "⚖️ Neutral"
                color = "gray"
            st.markdown(
                f"<div style='font-size:1.6em; color:{color}; font-weight:bold'>{overall} (Avg Score: {avg_score:.1f})</div>",
                unsafe_allow_html=True
            )

            # --- Unusual Options Activity (Flexible Detection + Inline Heatmap) ---
            st.markdown("---")
            st.subheader("🔍 Options Activity (Volume / Open Interest Heatmap)")

            expiry_for_uoa = selected_expiries[0]
            opt_chain = stock.option_chain(expiry_for_uoa)
            calls, puts = opt_chain.calls, opt_chain.puts

            # Flexible UOA logic
            calls['uoa_flag'] = ((calls['volume'] > 1.5 * calls['openInterest']) & (calls['openInterest'] > 50)) | \
                                (calls['volume'] > 500)
            puts['uoa_flag']  = ((puts['volume'] > 1.5 * puts['openInterest']) & (puts['openInterest'] > 50)) | \
                                (puts['volume'] > 500)

            unusual_calls = calls[calls['uoa_flag']]
            unusual_puts  = puts[puts['uoa_flag']]

            def style_options_table(df):
                return df.style.background_gradient(subset=['volume'], cmap='Reds') \
                               .background_gradient(subset=['openInterest'], cmap='Blues')

            if not unusual_calls.empty or not unusual_puts.empty:
                st.success(f"🔥 Found {len(unusual_calls)} unusual CALL and {len(unusual_puts)} unusual PUT contracts.")
                tab1, tab2 = st.tabs(["📈 Calls", "📉 Puts"])
                with tab1:
                    st.dataframe(style_options_table(unusual_calls[['contractSymbol','strike','volume','openInterest','lastPrice']]), width='stretch')
                with tab2:
                    st.dataframe(style_options_table(unusual_puts[['contractSymbol','strike','volume','openInterest','lastPrice']]), width='stretch')
            else:
                st.info("No unusual options activity detected. Showing top 10 options by volume.")
                top_calls = calls.sort_values(by='volume', ascending=False).head(10)
                top_puts = puts.sort_values(by='volume', ascending=False).head(10)
                tab1, tab2 = st.tabs(["📈 Calls", "📉 Puts"])
                with tab1:
                    st.dataframe(style_options_table(top_calls[['contractSymbol','strike','volume','openInterest','lastPrice']]), width='stretch')
                with tab2:
                    st.dataframe(style_options_table(top_puts[['contractSymbol','strike','volume','openInterest','lastPrice']]), width='stretch')

    except Exception as e:
        st.error(f"Error: {e}")

st.markdown("---")
st.markdown(
    "<div style='text-align:center; font-size:0.9em;'>☕ Built with Streamlit, free Yahoo data, FMP earnings calendar API, and ❤️ by an Options Trader</div>",
    unsafe_allow_html=True
)
