import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import altair as alt

# --- CONFIG ---
FMP_API_KEY = st.secrets["FMP_API_KEY"]  # <-- replace with your FMP API key
FMP_EARNINGS_URL = "https://financialmodelingprep.com/stable/earnings-calendar"

st.set_page_config(page_title="Earnings & Options Flow Sentiment Pro",
                   page_icon="📊", layout="wide")

st.title("📈 Earnings & Options Flow Sentiment")
st.markdown("""
Analyze **option sentiment, unusual activity**, and **price trends** for any stock or ETF.  
- Stocks → Based on **earnings proximity**  
- ETFs → Based on **option flow**
---
""")

# --- Cached Earnings Fetch ---
@st.cache_data(ttl=3600*6, show_spinner=False)
def get_fmp_earnings():
    today = datetime.today()
    future = today + timedelta(days=45)
    url = FMP_EARNINGS_URL
    params = {
        "from": today.strftime("%Y-%m-%d"),
        "to": future.strftime("%Y-%m-%d"),
        "apikey": FMP_API_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            return df
    except Exception as e:
        st.warning(f"⚠️ Could not fetch or parse FMP data: {e}")
    return pd.DataFrame()

col1, col2 = st.columns([4, 1])
with col1:
    st.subheader("📅 Major Upcoming Earnings (Next 10 Days & 45 Days)")
with col2:
    if st.button("🔁 Refresh Earnings", width='stretch'):
        get_fmp_earnings.clear()
        # ✅ Backward-compatible rerun
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.experimental_rerun()

earnings_df = get_fmp_earnings()

# --- Dynamic Major Earnings Panel ---
if not earnings_df.empty:
    today = datetime.today()
    next_7 = today + timedelta(days=10)
    next_30 = today + timedelta(days=45)

    #st.subheader("📅 Major Upcoming Earnings (Next 10 Days & 45 Days)")

    col1, col2 = st.columns(2)

    def safe_display(df):
        cols_to_show = [c for c in ["symbol", "date", "epsEstimated", "revenueEstimated"] if c in df.columns]
        st.dataframe(df[cols_to_show], width='stretch')

    with col1:
        st.markdown("**Next 10 Days**")
        upcoming_7 = earnings_df[(earnings_df["date"] >= today) &
                                (earnings_df["date"] <= next_7)]
        safe_display(upcoming_7)

    with col2:
        st.markdown("**Next 45 Days**")
        upcoming_30 = earnings_df[(earnings_df["date"] > next_7) &
                                (earnings_df["date"] <= next_30)]
        safe_display(upcoming_30)
else:
    st.warning("⚠️ No earnings data available. Check your API key or wait for cache refresh.")

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

def parse_contract_symbol(symbol):
    try:
        underlying = symbol[:-15]
        date_str = symbol[-15:-9]  # YYMMDD
        opt_type = symbol[-9:-8]
        strike_str = symbol[-8:]
        exp_date = f"20{date_str[:2]}-{date_str[2:4]}-{date_str[4:]}"
        strike = float(strike_str) / 1000
        return f"{underlying} {exp_date} {opt_type} {strike:.0f}"
    except Exception:
        return symbol

if ticker:
    try:
        stock = yf.Ticker(ticker)
        # --- Price Overview & Chart Block ---
        hist = stock.history(period="12mo", interval="1d")
        stock_name = stock.info.get("longName") or stock.info.get("shortName") or ticker
        if not hist.empty:
            st.subheader(f"📊 {stock_name}({ticker})")

            # Columns for metrics + chart
            col1, col2 = st.columns([1, 3])

            with col1:
                # --- RSI Calculation ---
                delta = hist['Close'].diff()
                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)
                avg_gain = gain.rolling(14, min_periods=1).mean()
                avg_loss = loss.rolling(14, min_periods=1).mean()
                rs = avg_gain / avg_loss.replace(0, 0.0001)
                hist['RSI'] = 100 - (100 / (1 + rs))
                latest_rsi = hist['RSI'].iloc[-1]
                # --- Determine color ---
                if latest_rsi > 70:
                    rsi_color = "red"
                elif latest_rsi < 30:
                    rsi_color = "green"
                else:
                    rsi_color = "yellow"                
                regular_price = stock.info.get("regularMarketPrice", np.nan)
                day_high = stock.info.get("dayHigh", np.nan)
                day_low = stock.info.get("dayLow", np.nan)
                prev_close = stock.info.get("previousClose", np.nan)
                # Determine current price color
                if regular_price > prev_close:
                    price_color = "green"
                elif regular_price < prev_close:
                    price_color = "red"
                else:
                    price_color = "yellow"
                st.markdown(
                    f"<div style='font-size:1.4em; font-weight:bold; color:{price_color}'>💰Current Price:${regular_price:.2f}</div>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<div style='font-size:1.2em; color:gray'>High: {day_high} / Low: {day_low}</div>",
                    unsafe_allow_html=True
                )
                st.metric(label="⏮️ Previous Close", 
                        value=f"${prev_close:.2f}" if not np.isnan(prev_close) else "N/A")
                # --- Display as styled metric ---
                st.markdown(f"<div style='font-size:1.4em; font-weight:bold; color:{rsi_color}'>📊 RSI (14): {latest_rsi:.1f}</div>",
                unsafe_allow_html=True
                )
                st.caption("RSI = Relative Strength Index; >70 = overbought, <30 = oversold.")
            with col2:
                # Calculate EMAs and MA
                hist['EMA10'] = hist['Close'].ewm(span=10, adjust=False).mean()
                hist['EMA20'] = hist['Close'].ewm(span=20, adjust=False).mean()
                hist['MA200'] = hist['Close'].rolling(window=200, min_periods=1).mean()
                ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
                ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
                hist['MACD'] = ema12 - ema26
                hist['Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
                hist['Hist'] = hist['MACD'] - hist['Signal']

                hist_reset = hist.reset_index()
                latest_price = hist_reset['Close'].iloc[-1]

                base = alt.Chart(hist_reset).encode(x='Date:T')

                # Candlestick wicks
                wicks = base.mark_rule(size=1).encode(
                    y='Low:Q',
                    y2='High:Q',
                    color=alt.condition("datum.Open <= datum.Close",
                                        alt.value("#26a69a"),  # up = green
                                        alt.value("#ef5350"))  # down = red
                )

                # Candlestick bodies
                candles = base.mark_bar(size=4).encode(
                    y='Open:Q',
                    y2='Close:Q',
                    color=alt.condition("datum.Open <= datum.Close",
                                        alt.value("#26a69a"),  # up
                                        alt.value("#ef5350")),  # down
                    tooltip=['Date:T', 'Open:Q', 'High:Q', 'Low:Q', 'Close:Q']
                )

                # Moving Averages
                ema10_line = base.mark_line(color='orange', size=1.5).encode(y='EMA10:Q')
                ema20_line = base.mark_line(color='white', size=1.5).encode(y='EMA20:Q')
                ma200_line = base.mark_line(color='blue', size=2).encode(y='MA200:Q')

                # Current Price Line
                price_line = alt.Chart(pd.DataFrame({'y': [latest_price]})).mark_rule(
                    color='yellow', strokeDash=[5, 5], size=1.5
                ).encode(y='y:Q')
                # Previous Proce Line
                prev_close_line = alt.Chart(pd.DataFrame({'y':[prev_close]})).mark_rule(
                    color='gray', strokeDash=[4,4], size=1.5
                ).encode(y='y:Q')

                price_text = alt.Chart(pd.DataFrame({'y': [latest_price]})).mark_text(
                    align='left', dx=5, dy=-5, color='yellow', fontSize=12, fontWeight='bold'
                ).encode(y='y:Q', text=alt.value(f"${latest_price:.2f}"))

                # Volume Histogram (optional)
                vol_chart = alt.Chart(hist_reset).mark_bar(opacity=0.5).encode(
                    x='Date:T',
                    y=alt.Y('Volume:Q', axis=alt.Axis(title='Volume')),
                    color=alt.condition("datum.Open <= datum.Close",
                                        alt.value("#26a69a"),
                                        alt.value("#ef5350"))
                ).properties(height=100)

                # --- MACD chart ---
                macd_base = alt.Chart(hist_reset).encode(x='Date:T')
                macd_bar = macd_base.mark_bar().encode(
                    y='Hist:Q',
                    color=alt.condition("datum.Hist > 0", alt.value("#26a69a"), alt.value("#ef5350"))
                )
                macd_line = macd_base.mark_line(color='cyan', size=1).encode(y='MACD:Q')
                signal_line = macd_base.mark_line(color='orange', size=1).encode(y='Signal:Q')
                vol_macd_chart = alt.layer(vol_chart, macd_line, signal_line).resolve_scale(y='independent').properties(height=100, title="Volume + MACD")

                # Combine all charts
                price_chart = (wicks + candles + ema10_line + ema20_line + ma200_line + prev_close_line ).properties(height=420)
                final_chart = alt.vconcat(price_chart, vol_macd_chart).resolve_scale(x='shared')
                st.altair_chart(final_chart, width='stretch')
        else:
            st.warning("⚠️ No historical data available for this ticker.")




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

            # --- Unusual Options Activity (with Heatmap) ---
            st.markdown("---")
            st.subheader("🔍 Options Activity (Volume / Open Interest Heatmap)")

            expiry_for_uoa = selected_expiries[0]
            opt_chain = stock.option_chain(expiry_for_uoa)
            calls, puts = opt_chain.calls.copy(), opt_chain.puts.copy()

            # --- Add formatted readable contract symbols ---
            calls["Readable Symbol"] = calls["contractSymbol"].apply(parse_contract_symbol)
            puts["Readable Symbol"] = puts["contractSymbol"].apply(parse_contract_symbol)

            # --- Flexible UOA logic ---
            calls['uoa_flag'] = ((calls['volume'] > 1.5 * calls['openInterest']) & (calls['openInterest'] > 50)) | \
                                (calls['volume'] > 500)
            puts['uoa_flag']  = ((puts['volume'] > 1.5 * puts['openInterest']) & (puts['openInterest'] > 50)) | \
                                (puts['volume'] > 500)

            unusual_calls = calls[calls['uoa_flag']]
            unusual_puts  = puts[puts['uoa_flag']]

            # --- Function to add heatmap styling ---
            def style_options_table(df):
                return df.style.background_gradient(subset=['volume'], cmap='Reds') \
                               .background_gradient(subset=['openInterest'], cmap='Blues')

            # --- Display Tables ---
            if not unusual_calls.empty or not unusual_puts.empty:
                st.success(f"🔥 Found {len(unusual_calls)} unusual CALL and {len(unusual_puts)} unusual PUT contracts.")
                tab1, tab2 = st.tabs(["📈 Calls", "📉 Puts"])
                with tab1:
                    st.dataframe(style_options_table(unusual_calls[['Readable Symbol','strike','volume','openInterest','lastPrice']]), width='stretch')
                with tab2:
                    st.dataframe(style_options_table(unusual_puts[['Readable Symbol','strike','volume','openInterest','lastPrice']]), width='stretch')
            else:
                st.info("No unusual options activity detected. Showing top 10 options by volume.")
                top_calls = calls.sort_values(by='volume', ascending=False).head(10)
                top_puts = puts.sort_values(by='volume', ascending=False).head(10)
                tab1, tab2 = st.tabs(["📈 Calls", "📉 Puts"])
                with tab1:
                    st.dataframe(style_options_table(top_calls[['Readable Symbol','strike','volume','openInterest','lastPrice']]), width='stretch')
                with tab2:
                    st.dataframe(style_options_table(top_puts[['Readable Symbol','strike','volume','openInterest','lastPrice']]), width='stretch')

    except Exception as e:
        st.error(f"Error: {e}")

# --- Sector ETF Containers in 3x3 Grid with Enhanced Formatting ---
st.markdown("---")

# --- Header Row with Refresh Button ---
col1, col2 = st.columns([4, 1])
with col1:
    st.header("📊 Top ETFs by Sector (3×3 Grid)")
with col2:
    if st.button("🔁 Refresh", width='stretch'):
        st.cache_data.clear()
        st.rerun()

# --- Cached ETF Fetch Function ---
@st.cache_data(ttl=3600)
def fetch_etf_metrics(etfs):
    data = []
    for ticker in etfs:
        try:
            etf = yf.Ticker(ticker)
            info = etf.info
            prev_close = info.get("previousClose", np.nan)
            curr_price = info.get("regularMarketPrice", np.nan)

            # Calculate % change
            pct_change = np.nan
            if pd.notna(prev_close) and prev_close != 0 and pd.notna(curr_price):
                pct_change = ((curr_price - prev_close) / prev_close) * 100

            color = (
                "green" if pct_change > 0 else
                "red" if pct_change < 0 else
                "gray"
            )

            # Format Market Cap
            market_cap = info.get("marketCap", np.nan)
            if pd.notna(market_cap):
                if market_cap >= 1e12:
                    market_cap_str = f"{market_cap/1e12:.2f}T"
                elif market_cap >= 1e9:
                    market_cap_str = f"{market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"{market_cap/1e6:.2f}M"
                else:
                    market_cap_str = str(market_cap)
            else:
                market_cap_str = "N/A"

            # Format volume
            vol = info.get("volume", np.nan)
            vol_str = f"{int(vol):,}" if pd.notna(vol) else "N/A"

            data.append({
                "ETF": ticker,
                "Price": curr_price,
                "PriceColor": color,
                "% Change": pct_change,
                "Previous Close": prev_close,
                "Market Cap": market_cap_str,
                "Volume": vol_str
            })
        except Exception:
            data.append({
                "ETF": ticker,
                "Price": np.nan,
                "PriceColor": "gray",
                "% Change": np.nan,
                "Previous Close": np.nan,
                "Market Cap": "N/A",
                "Volume": "N/A"
            })
    return pd.DataFrame(data)

# --- Sector ETF List ---
sector_list = [
    ("Semiconductors", ["SMH", "SOXX", "PSI", "USD", "HXL"]),    
    ("Technology", ["XLK", "VGT", "FTEC", "SMH", "TECL"]),
    ("Finance", ["XLF", "VFH", "KBE", "KRE", "FINX"]),
    ("Oil & Energy", ["XLE", "VDE", "OIH", "IEO", "USO"]),
    ("AI & Robotics", ["BOTZ", "ROBO", "ARKQ", "IRBO", "PRNT"]),
    ("Datacenters / Cloud", ["SRVR", "CORZ", "QCLN", "CIBR", "SKYY"]),
    ("Healthcare", ["XLV", "VHT", "IYH", "RYH", "FHLC"]),
    ("Consumer Discretionary", ["XLY", "VCR", "FDIS", "PEJ", "RCD"]),
    ("Consumer Staples", ["XLP", "VDC", "KXI", "RHS", "FSTA"]),
    ("Industrial / Manufacturing", ["XLI", "VIS", "IYJ", "PRN", "RGI"]),
    ("Utilities", ["XLU", "VPU", "IDU", "FUTY", "FXU"]),
    ("Materials", ["XLB", "VAW", "MXI", "RTM", "PYZ"]),
    ("Real Estate", ["XLRE", "VNQ", "IYR", "RWR", "FREL"]),
    ("Communications / Media", ["XLC", "VOX", "FCOM", "IXP", "PEJ"]),
    ("Biotech", ["IBB", "XBI", "BBH", "LABU", "BTX"])
]

# --- Display in 3×3 Grid ---
for i in range(0, len(sector_list), 3):
    cols = st.columns(3)
    for j, (sector_name, etfs) in enumerate(sector_list[i:i+3]):
        with cols[j]:
            st.subheader(f"💼 {sector_name}")
            df_metrics = fetch_etf_metrics(etfs)
            df_display = df_metrics.copy()

            # Color the price and % change inline
            df_display["Price"] = df_display.apply(
                lambda x: f"<span style='color:{x['PriceColor']}'>{x['Price']:.2f}</span>"
                if pd.notna(x["Price"]) else "N/A", axis=1
            )
            df_display["% Change"] = df_display.apply(
                lambda x: f"<span style='color:{x['PriceColor']}'>{x['% Change']:.2f}%</span>"
                if pd.notna(x["% Change"]) else "N/A", axis=1
            )

            st.write(
                df_display[["ETF", "Price", "% Change", "Previous Close", "Market Cap", "Volume"]]
                .to_html(escape=False, index=False),
                unsafe_allow_html=True
            )

# --- Footer ---
st.markdown(
    """
    ---
    <div style='text-align:center; font-size:0.9em;'>
    Built with Streamlit, free Yahoo data, and ❤️ by Arun Tatikonda 🧠 | ☕ <a href="https://www.paypal.com/donate/?hosted_button_id=RKQ6B5LAPK6FG" target="_blank"> 
        Buy me a coffee  </a>
        </div>
    """,
    unsafe_allow_html=True
)
