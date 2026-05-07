from datetime import date
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Macro Index Rotation Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

REGIME_DESCRIPTIONS = {
    "CRISIS": "Yield curve stress and fear are elevated. Capital preservation comes first.",
    "TIGHTENING": "Fed is raising rates to fight high inflation. Growth assets face headwinds. Value and defensives favored.",
    "INFLATION": "Inflation is the dominant risk. Real assets and commodity-linked exposure become more useful.",
    "RISK ON": "Policy is easing while sentiment is positive. Growth and risk assets have a macro tailwind.",
    "RISK OFF": "Policy may be easing, but markets remain fearful. Defensives and liquidity are preferred.",
    "NEUTRAL": "No single macro signal dominates. Keep the core DCA plan steady and avoid aggressive tilts.",
}

REGIME_PLAYBOOK = {
    "RISK ON": {
        "overweight": ["S&P 500 Index", "Global Tech Index", "EM Asia Index", "Small Cap Index"],
        "neutral": ["IDX LQ45 Index", "Global Dividend Index"],
        "underweight": ["Gold Fund", "Short Bond Fund", "Money Market / RDPU"],
        "rationale": "Rates easing, sentiment positive. Growth and risk assets outperform. Maximize equity exposure.",
    },
    "TIGHTENING": {
        "overweight": ["Energy & Commodities", "Value / Dividend Index", "Short Bond Fund", "Money Market / RDPU"],
        "neutral": ["IDX LQ45 Index", "S&P 500 Index"],
        "underweight": ["Global Tech Index", "Small Cap Index", "EM Asia Index", "Long Bond Fund"],
        "rationale": "Rising rates punish growth stocks and long duration bonds. Value, commodities, and cash win.",
    },
    "INFLATION": {
        "overweight": ["Commodities Index", "Energy Index", "Gold Fund", "IDX Commodity Stocks Index"],
        "neutral": ["Value / Dividend Index", "IDX LQ45 Index"],
        "underweight": ["Global Tech Index", "Long Bonds", "EM Bonds"],
        "rationale": "Inflation erodes fixed income and growth valuations. Real assets and commodities preserve purchasing power.",
    },
    "RISK OFF": {
        "overweight": ["Gold Fund", "Money Market / RDPU", "Short Bond Fund", "Government Bond (SBN)"],
        "neutral": ["S&P 500 Index", "IDX LQ45 Index"],
        "underweight": ["Small Cap Index", "EM Asia Index", "Global Tech Index", "Crypto Index"],
        "rationale": "Markets fearful. Capital preservation priority. Reduce volatility, hold defensive assets.",
    },
    "CRISIS": {
        "overweight": ["Money Market / RDPU", "Government Bond (SBN)", "Gold Fund"],
        "neutral": [],
        "underweight": ["Everything else"],
        "rationale": "Yield curve inverted, VIX elevated. Preserve capital first. Opportunities come after the flush.",
    },
    "NEUTRAL": {
        "overweight": ["S&P 500 Index", "IDX LQ45 Index"],
        "neutral": ["Global Dividend Index", "Short Bond Fund"],
        "underweight": ["Speculative / Thematic ETFs"],
        "rationale": "No strong macro signal. Default to core allocation. Keep DCA steady, no tactical shifts needed.",
    },
}

BIBIT_FUND_MAP = {
    "S&P 500 Index": "Reksa Dana Sucorinvest S&P 500 Index Fund",
    "Global Tech Index": "Reksa Dana Syailendra US Equity Index Fund",
    "IDX LQ45 Index": "Reksa Dana Indeks BNI-AM LQ45",
    "IDX30 Index": "Reksa Dana Indeks Principal IDX30",
    "EM Asia Index": "Reksa Dana Manulife Emerging Market Index",
    "Gold Fund": "Reksa Dana Emas Syailendra / Reksa Dana Emas Autus",
    "Money Market / RDPU": "Reksa Dana Pasar Uang STAR by Bibit",
    "Government Bond (SBN)": "Wait for ORI/SBR offering — check www.kemenkeu.go.id",
    "Short Bond Fund": "Reksa Dana Pendapatan Tetap Schroder Dana Mantap Plus",
    "Global Dividend Index": "Reksa Dana Manulife Global Sharia Equity Fund",
    "Commodities Index": "No direct Bibit equivalent — use Gold Fund as proxy",
    "Energy & Commodities": "No direct Bibit equivalent — combine Gold Fund and IDX dividend/commodity exposure",
    "Energy Index": "No direct Bibit equivalent — use Gold Fund as proxy",
    "IDX Commodity Stocks Index": "No direct Bibit equivalent — prefer IDX high dividend/value proxy",
    "Value / Dividend Index": "Reksa Dana Indeks BNI-AM IDX High Dividend 20",
    "Small Cap Index": "Reksa Dana Indeks Principal IDX SMC Liquid",
    "Long Bond Fund": "Long-duration bond funds — skip this month",
    "Long Bonds": "Long-duration bond funds — skip this month",
    "EM Bonds": "Emerging-market bond funds — skip this month",
    "Crypto Index": "Crypto/thematic exposure — skip this month",
    "Speculative / Thematic ETFs": "Speculative or thematic funds — skip this month",
    "Everything else": "All non-cash, non-SBN, non-gold risk assets — skip until stress fades",
}

REGIME_HISTORY = {
    "TIGHTENING": {
        "avg_duration_months": 18,
        "sp500_avg_return": "+4% (flat to modest gains)",
        "bonds_avg_return": "-8% (long bonds hurt most)",
        "gold_avg_return": "+12%",
        "commodities": "+18%",
        "historical_examples": "2004–2006, 2015–2018, 2022–2023",
    },
    "RISK ON": {
        "avg_duration_months": 30,
        "sp500_avg_return": "+22% annualized",
        "bonds_avg_return": "+3%",
        "gold_avg_return": "+5%",
        "commodities": "+8%",
        "historical_examples": "2009–2018, 2019–2021",
    },
    "INFLATION": {
        "avg_duration_months": 14,
        "sp500_avg_return": "+6% (uneven)",
        "bonds_avg_return": "-12%",
        "gold_avg_return": "+18%",
        "commodities": "+30%",
        "historical_examples": "1973–1975, 1977–1980, 2021–2022",
    },
    "RISK OFF": {
        "avg_duration_months": 10,
        "sp500_avg_return": "-10% to flat",
        "bonds_avg_return": "+8% (flight to safety)",
        "gold_avg_return": "+15%",
        "commodities": "-10%",
        "historical_examples": "2011, 2018 Q4, 2022 H1",
    },
    "CRISIS": {
        "avg_duration_months": 8,
        "sp500_avg_return": "-35% peak to trough",
        "bonds_avg_return": "+15% (flight to safety)",
        "gold_avg_return": "+20%",
        "commodities": "-25%",
        "historical_examples": "2000–2002, 2008–2009, 2020 (brief)",
    },
    "NEUTRAL": {
        "avg_duration_months": 12,
        "sp500_avg_return": "+10% (historical average)",
        "bonds_avg_return": "+4%",
        "gold_avg_return": "+5%",
        "commodities": "+5%",
        "historical_examples": "Most of 2012–2014, 2016–2017",
    },
}

CHART_LINES = {
    "S&P 500": {"ticker": "^GSPC", "color": "#00C853", "style": "solid"},
    "IHSG": {"ticker": "^JKSE", "color": "#2196F3", "style": "solid"},
    "Gold": {"ticker": "GC=F", "color": "#FFD700", "style": "solid"},
    "CPI Inflation": {"source": "FRED", "color": "#FF5252", "style": "dash"},
    "Risk-Free (SBN)": {"source": "static", "color": "#FF9800", "style": "dash"},
}

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

st.markdown(
    """
    <style>
        .stApp { background: #0B1020; color: #F5F7FA; }
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1180px; }
        div[data-testid="stMetric"] { background: #111827; border: 1px solid #263244; border-radius: 16px; padding: 1rem; }
        .briefing, .regime-box, .panel { border-radius: 18px; padding: 1.1rem 1.25rem; border: 1px solid #263244; background: linear-gradient(135deg, #111827, #0F172A); margin-bottom: 1rem; }
        .briefing { border-left: 6px solid #38BDF8; font-size: 1.02rem; line-height: 1.65; }
        .regime-box { text-align: center; border-width: 2px; }
        .signal-grid { display: grid; grid-template-columns: repeat(7, minmax(120px, 1fr)); gap: .6rem; margin-bottom: 1rem; }
        .badge { border-radius: 14px; padding: .75rem .65rem; min-height: 88px; border: 1px solid rgba(255,255,255,.12); }
        .badge-label { font-size: .72rem; text-transform: uppercase; color: #A7B0C0; margin-bottom: .35rem; letter-spacing: .04em; }
        .badge-value { font-weight: 800; font-size: .92rem; }
        .green { background: rgba(0, 200, 83, .16); color: #9EF5B4; }
        .yellow { background: rgba(255, 193, 7, .16); color: #FFE08A; }
        .red { background: rgba(255, 82, 82, .16); color: #FFB4B4; }
        .buy { border-left: 5px solid #00C853; }
        .hold { border-left: 5px solid #FFC107; }
        .skip { border-left: 5px solid #FF5252; }
        @media (max-width: 900px) { .signal-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
        @media (max-width: 520px) { .signal-grid { grid-template-columns: 1fr; } .block-container { padding-left: .8rem; padding-right: .8rem; } }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_secret_text(name):
    value = ""
    try:
        value = st.secrets.get(name, "")
    except Exception as exc:
        st.warning(f"Could not read Streamlit secret {name}: {exc}")
    if value in (None, ""):
        value = os.environ.get(name, "")
    return str(value).strip() if value is not None else ""


def get_secret_float(name, default):
    value = default
    try:
        value = st.secrets.get(name, os.environ.get(name, default))
    except Exception as exc:
        st.warning(f"Could not read Streamlit secret {name}: {exc}")
        value = os.environ.get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        st.warning(f"Secret {name} is invalid. Falling back to {default:.2%}.")
        return default


def render_config_diagnostics(fred_api_key, rapidapi_key, sbn_yield):
    with st.expander("Configuration check — no secret values shown"):
        st.write(
            {
                "FRED_API_KEY detected": bool(fred_api_key),
                "FRED_API_KEY length": len(fred_api_key),
                "RAPIDAPI_KEY detected": bool(rapidapi_key),
                "RAPIDAPI_KEY length": len(rapidapi_key),
                "SBN_YIELD": sbn_yield,
            }
        )
        if not fred_api_key:
            st.error(
                "The running app cannot see FRED_API_KEY. Save it in this app's Streamlit Cloud "
                "Secrets settings, reboot the app, and confirm you deployed the branch that contains this code."
            )


@st.cache_data(ttl=86400)
def fetch_fred_series(series_id, api_key, limit=3):
    try:
        api_key = str(api_key).strip() if api_key else ""
        if not api_key:
            st.warning(f"FRED_API_KEY is missing. {series_id} data is unavailable until configured.")
            return pd.DataFrame(columns=["date", "value"])
        response = requests.get(
            FRED_BASE_URL,
            params={
                "series_id": series_id,
                "api_key": api_key,
                "sort_order": "desc",
                "limit": limit,
                "file_type": "json",
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if "error_code" in payload:
            st.warning(
                f"FRED rejected FRED_API_KEY for {series_id}: "
                f"{payload.get('error_message', 'invalid API key or request')}"
            )
            return pd.DataFrame(columns=["date", "value"])
        observations = payload.get("observations", [])
        frame = pd.DataFrame(observations)
        if frame.empty:
            st.warning(f"FRED returned no observations for {series_id}.")
            return pd.DataFrame(columns=["date", "value"])
        frame = frame[["date", "value"]].copy()
        frame["date"] = pd.to_datetime(frame["date"])
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        return frame.dropna().sort_values("date")
    except Exception as exc:
        st.warning(f"Could not fetch FRED series {series_id}: {exc}")
        return pd.DataFrame(columns=["date", "value"])


@st.cache_data(ttl=86400)
def fetch_yfinance_history(ticker, period="1y"):
    try:
        data = yf.download(ticker, period=period, auto_adjust=False, progress=False, threads=False)
        if data.empty:
            st.warning(f"Yahoo Finance returned no data for {ticker}.")
            return pd.DataFrame(columns=["Close"])
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        close_column = "Adj Close" if "Adj Close" in data.columns else "Close"
        frame = data[[close_column]].rename(columns={close_column: "Close"}).dropna().copy()
        frame.index = pd.to_datetime(frame.index).tz_localize(None)
        return frame
    except Exception as exc:
        st.warning(f"Could not fetch Yahoo Finance ticker {ticker}: {exc}")
        return pd.DataFrame(columns=["Close"])


@st.cache_data(ttl=86400)
def fetch_fear_greed(vix_value, rapidapi_key):
    try:
        rapidapi_key = str(rapidapi_key).strip() if rapidapi_key else ""
        if rapidapi_key:
            response = requests.get(
                "https://fear-and-greed-index.p.rapidapi.com/v1/fgi",
                headers={
                    "X-RapidAPI-Key": rapidapi_key,
                    "X-RapidAPI-Host": "fear-and-greed-index.p.rapidapi.com",
                },
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            value = payload.get("fgi", {}).get("now", {}).get("value")
            if value is not None:
                return float(value), "CNN Fear & Greed"
        if pd.notna(vix_value):
            approximation = float(np.clip(100 - (vix_value * 3), 0, 100))
            return approximation, "VIX inversion approximation"
        st.warning("Fear & Greed data unavailable; no VIX value available for approximation.")
        return np.nan, "Unavailable"
    except Exception as exc:
        st.warning(f"Could not fetch CNN Fear & Greed data; using VIX approximation if possible: {exc}")
        if pd.notna(vix_value):
            return float(np.clip(100 - (vix_value * 3), 0, 100)), "VIX inversion approximation"
        return np.nan, "Unavailable"


def latest_value(frame):
    if frame.empty:
        return np.nan
    return frame["value"].iloc[-1]


def latest_close(frame):
    if frame.empty:
        return np.nan
    return frame["Close"].dropna().iloc[-1]


def sma_signal(frame, label_above, label_below, window=50):
    closes = frame["Close"].dropna() if not frame.empty else pd.Series(dtype=float)
    if len(closes) < window:
        return "UNKNOWN", np.nan
    sma = closes.rolling(window).mean().iloc[-1]
    return (label_above if closes.iloc[-1] > sma else label_below), sma


def classify_yield_curve(dgs10, dgs2):
    if pd.isna(dgs10) or pd.isna(dgs2):
        return "UNKNOWN", np.nan
    spread = dgs10 - dgs2
    if spread < 0:
        return "INVERTED", spread
    if spread <= 0.5:
        return "FLAT", spread
    return "NORMAL", spread


def classify_inflation(cpi_frame):
    if len(cpi_frame) < 13:
        return "UNKNOWN", np.nan
    latest = cpi_frame["value"].iloc[-1]
    year_ago = cpi_frame["value"].iloc[-13]
    yoy = (latest / year_ago - 1) * 100
    if yoy > 4:
        return "HIGH INFLATION", yoy
    if yoy >= 2:
        return "MODERATE", yoy
    return "LOW INFLATION", yoy


def classify_rate_trend(fed_frame):
    values = fed_frame["value"].dropna().tail(3).to_numpy() if not fed_frame.empty else np.array([])
    if len(values) < 3:
        return "UNKNOWN"
    if values[-1] > values[0]:
        return "TIGHTENING"
    if values[-1] < values[0]:
        return "EASING"
    return "PAUSE"


def classify_vix(vix_value):
    if pd.isna(vix_value):
        return "UNKNOWN"
    if vix_value < 15:
        return "RISK ON"
    if vix_value <= 25:
        return "NEUTRAL"
    return "RISK OFF"


def classify_regime(yield_curve, inflation, rate_trend, dollar, vix_sentiment):
    if vix_sentiment == "RISK OFF" and yield_curve == "INVERTED":
        return "CRISIS"
    if rate_trend == "TIGHTENING" and inflation == "HIGH INFLATION":
        return "TIGHTENING"
    if inflation == "HIGH INFLATION" and rate_trend != "TIGHTENING":
        return "INFLATION"
    if rate_trend == "EASING" and vix_sentiment == "RISK ON":
        return "RISK ON"
    if rate_trend == "EASING" and vix_sentiment == "RISK OFF":
        return "RISK OFF"
    return "NEUTRAL"


def generate_briefing(regime, yield_curve, inflation, rate_trend, dollar, vix):
    dollar_note = (
        "favors US domestic assets over emerging markets"
        if dollar == "STRONG DOLLAR"
        else "supports emerging market and commodity exposure"
    )
    return (
        f"As of {date.today().strftime('%B %Y')}, the macro environment is classified as {regime}. "
        f"The Fed is currently in a {rate_trend} cycle with inflation running {inflation}. "
        f"The yield curve is {yield_curve}, and market sentiment is {vix}. "
        f"The US dollar is {dollar}, which {dollar_note}. "
        f"Recommended action this month: {REGIME_PLAYBOOK[regime]['rationale']}"
    )


def badge_color(label):
    green = {"NORMAL", "LOW INFLATION", "EASING", "WEAK DOLLAR", "RISK ON", "CRYPTO BULL", "IDX BULL"}
    red = {"INVERTED", "HIGH INFLATION", "TIGHTENING", "STRONG DOLLAR", "RISK OFF", "CRYPTO BEAR", "IDX BEAR"}
    if label in green:
        return "green"
    if label in red:
        return "red"
    return "yellow"


def regime_color(regime):
    return {
        "RISK ON": "#00C853",
        "TIGHTENING": "#FF9800",
        "INFLATION": "#FF5252",
        "RISK OFF": "#FFC107",
        "CRISIS": "#D50000",
        "NEUTRAL": "#38BDF8",
    }.get(regime, "#38BDF8")


def map_funds(categories):
    return [BIBIT_FUND_MAP.get(category, category) for category in categories]


def rate_cycle_month(rate_frame):
    if len(rate_frame) < 4:
        return None
    ordered = rate_frame.sort_values("date").copy()
    ordered["diff"] = ordered["value"].diff()
    ordered["direction"] = np.sign(ordered["diff"]).replace(0, np.nan).ffill().fillna(0)
    latest_direction = ordered["direction"].iloc[-1]
    changes = ordered[ordered["direction"] != ordered["direction"].shift(1)]
    changes = changes[changes["direction"] == latest_direction]
    if changes.empty:
        start_date = ordered["date"].iloc[0]
    else:
        start_date = changes["date"].iloc[-1]
    return max(1, (pd.Timestamp.today().to_period("M") - start_date.to_period("M")).n + 1)


def normalize_series(series):
    clean = series.dropna()
    if clean.empty:
        return clean
    return clean / clean.iloc[0] * 100


def build_chart_data(period_key, sbn_yield, fred_api_key):
    days = {"3M": 92, "6M": 183, "1Y": 365, "3Y": 1095}[period_key]
    start = pd.Timestamp.today().normalize() - pd.Timedelta(days=days)
    dates = pd.date_range(start=start, end=pd.Timestamp.today().normalize(), freq="D")
    chart_data = pd.DataFrame(index=dates)

    ticker_period = "5y" if period_key == "3Y" else "2y"
    for name, config in CHART_LINES.items():
        if "ticker" in config:
            frame = fetch_yfinance_history(config["ticker"], ticker_period)
            if not frame.empty:
                series = frame["Close"][frame.index >= start]
                chart_data[name] = normalize_series(series).reindex(dates).ffill()

    cpi = fetch_fred_series("CPIAUCSL", fred_api_key, 60)
    if not cpi.empty:
        cpi_series = cpi.set_index("date")["value"]
        cpi_daily = cpi_series.reindex(dates.union(cpi_series.index)).sort_index().ffill().reindex(dates)
        chart_data["CPI Inflation"] = normalize_series(cpi_daily)

    day_numbers = np.arange(len(dates))
    chart_data["Risk-Free (SBN)"] = 100 * np.power(1 + sbn_yield, day_numbers / 365)
    return chart_data


def render_signal_grid(signals):
    html = '<div class="signal-grid">'
    for label, value in signals:
        html += (
            f'<div class="badge {badge_color(value)}">'
            f'<div class="badge-label">{label}</div>'
            f'<div class="badge-value">{value}</div>'
            "</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_recommendation(regime, dollar, ihsg_trend):
    playbook = REGIME_PLAYBOOK[regime]
    dollar_note = (
        "STRONG DOLLAR: EM index funds are unfavorable — dollar strength can hurt emerging-market returns."
        if dollar == "STRONG DOLLAR"
        else "WEAK DOLLAR: EM and commodity exposure receives an extra macro boost."
    )
    ihsg_note = (
        "IDX locally weak. Tilt DCA toward US/global index over IDX funds this month."
        if ihsg_trend == "IDX BEAR"
        else "IDX showing strength. Local index funds can carry higher allocation this month."
    )

    st.subheader("💡 THIS MONTH'S DCA RECOMMENDATION")
    st.markdown(f"**Regime:** `{regime}`")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="panel buy"><h4>🟢 BUY MORE</h4>', unsafe_allow_html=True)
        for fund in map_funds(playbook["overweight"]):
            st.markdown(f"• {fund}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="panel hold"><h4>🟡 HOLD</h4>', unsafe_allow_html=True)
        if playbook["neutral"]:
            for fund in map_funds(playbook["neutral"]):
                st.markdown(f"• {fund}")
        else:
            st.markdown("• No neutral allocation this month")
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="panel skip"><h4>🔴 REDUCE / SKIP</h4>', unsafe_allow_html=True)
        for fund in map_funds(playbook["underweight"]):
            st.markdown(f"• {fund}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.info(f"📝 {playbook['rationale']}\n\n{dollar_note}\n\n{ihsg_note}")


def render_history(regime, cycle_month):
    history = REGIME_HISTORY[regime]
    current_month = "Unknown" if cycle_month is None else f"Month {cycle_month}"
    st.subheader("📚 HISTORICAL REGIME CONTEXT")
    st.markdown(
        f"""
        <div class="panel">
            <b>Estimated current position:</b> {current_month}<br>
            <b>Average duration:</b> {history['avg_duration_months']} months<br>
            <b>S&P 500:</b> {history['sp500_avg_return']}<br>
            <b>Bonds:</b> {history['bonds_avg_return']}<br>
            <b>Gold:</b> {history['gold_avg_return']}<br>
            <b>Commodities:</b> {history['commodities']}<br>
            <b>Historical examples:</b> {history['historical_examples']}
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.title("🌍 Macro-Driven Index Rotation Dashboard")
    st.caption("Monthly DCA guidance for Bibit Indonesia index-fund investors. Data refreshes at most once per day.")

    fred_api_key = get_secret_text("FRED_API_KEY")
    rapidapi_key = get_secret_text("RAPIDAPI_KEY")
    sbn_yield = get_secret_float("SBN_YIELD", 0.065)
    render_config_diagnostics(fred_api_key, rapidapi_key, sbn_yield)

    fed = fetch_fred_series("FEDFUNDS", fred_api_key, 60)
    cpi = fetch_fred_series("CPIAUCSL", fred_api_key, 60)
    dgs2 = fetch_fred_series("DGS2", fred_api_key, 10)
    dgs10 = fetch_fred_series("DGS10", fred_api_key, 10)
    dxy = fetch_yfinance_history("DX-Y.NYB", "1y")
    vix = fetch_yfinance_history("^VIX", "1y")
    sp500 = fetch_yfinance_history("^GSPC", "1y")
    gold = fetch_yfinance_history("GC=F", "1y")
    oil = fetch_yfinance_history("CL=F", "1y")
    ihsg = fetch_yfinance_history("^JKSE", "1y")
    btc = fetch_yfinance_history("BTC-USD", "1y")

    yield_curve, spread = classify_yield_curve(latest_value(dgs10), latest_value(dgs2))
    inflation, cpi_yoy = classify_inflation(cpi)
    rate_trend = classify_rate_trend(fed)
    dollar, dxy_sma = sma_signal(dxy, "STRONG DOLLAR", "WEAK DOLLAR")
    vix_value = latest_close(vix)
    vix_sentiment = classify_vix(vix_value)
    crypto_sentiment, btc_sma = sma_signal(btc, "CRYPTO BULL", "CRYPTO BEAR")
    ihsg_trend, ihsg_sma = sma_signal(ihsg, "IDX BULL", "IDX BEAR")
    fear_greed_value, fear_greed_source = fetch_fear_greed(vix_value, rapidapi_key)
    regime = classify_regime(yield_curve, inflation, rate_trend, dollar, vix_sentiment)

    st.subheader("📋 MONTHLY MACRO BRIEFING")
    st.markdown(f'<div class="briefing">{generate_briefing(regime, yield_curve, inflation, rate_trend, dollar, vix_sentiment)}</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="regime-box" style="border-color: {regime_color(regime)}; box-shadow: 0 0 28px {regime_color(regime)}33;">
            <div style="font-size: .9rem; letter-spacing: .12em; color: #A7B0C0;">🌍 CURRENT MACRO REGIME</div>
            <div style="font-size: clamp(2.4rem, 9vw, 5.2rem); font-weight: 900; color: {regime_color(regime)}; line-height: 1.05;">{regime}</div>
            <div style="font-size: 1.05rem; color: #D6DEE9;">{REGIME_DESCRIPTIONS[regime]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("📡 SIGNAL GRID")
    render_signal_grid(
        [
            ("Yield Curve", yield_curve),
            ("Inflation", inflation),
            ("Rate Trend", rate_trend),
            ("US Dollar", dollar),
            ("Risk Sentiment", vix_sentiment),
            ("Crypto", crypto_sentiment),
            ("IHSG", ihsg_trend),
        ]
    )
    detail_cols = st.columns(4)
    detail_cols[0].metric("10Y - 2Y Spread", "N/A" if pd.isna(spread) else f"{spread:.2f}%")
    detail_cols[1].metric("CPI YoY", "N/A" if pd.isna(cpi_yoy) else f"{cpi_yoy:.1f}%")
    detail_cols[2].metric("VIX", "N/A" if pd.isna(vix_value) else f"{vix_value:.1f}")
    detail_cols[3].metric("Fear & Greed", "N/A" if pd.isna(fear_greed_value) else f"{fear_greed_value:.0f}", fear_greed_source)

    with st.expander("Raw source snapshot"):
        st.write(
            {
                "Fed Funds latest": latest_value(fed),
                "DXY latest / SMA50": (latest_close(dxy), dxy_sma),
                "BTC latest / SMA50": (latest_close(btc), btc_sma),
                "IHSG latest / SMA50": (latest_close(ihsg), ihsg_sma),
                "S&P 500 latest": latest_close(sp500),
                "Gold latest": latest_close(gold),
                "Oil latest": latest_close(oil),
            }
        )

    st.subheader("📈 REAL WEALTH CHART")
    controls = st.columns([1, 2])
    period = controls[0].selectbox("Time Period", ["3M", "6M", "1Y", "3Y"], index=2)
    selected_lines = controls[1].multiselect("Lines", list(CHART_LINES.keys()), default=list(CHART_LINES.keys()))
    chart_data = build_chart_data(period, sbn_yield, fred_api_key)

    fig = go.Figure()
    for name in selected_lines:
        if name in chart_data.columns:
            config = CHART_LINES[name]
            fig.add_trace(
                go.Scatter(
                    x=chart_data.index,
                    y=chart_data[name],
                    name=name,
                    line=dict(
                        color=config["color"],
                        dash="dash" if config["style"] == "dash" else "solid",
                        width=2,
                    ),
                )
            )
    fig.add_hline(y=100, line_dash="dot", line_color="white", opacity=0.3, annotation_text="Starting point")
    fig.update_layout(
        title="Real Wealth Check: Are Your Investments Actually Winning?",
        yaxis_title="Growth (Base 100)",
        xaxis_title="",
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=10, r=10, t=70, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    sp500_return = np.nan
    inflation_cost = np.nan
    sbn_cumulative_return = np.nan
    if "S&P 500" in chart_data and chart_data["S&P 500"].dropna().size >= 2:
        sp500_return = chart_data["S&P 500"].dropna().iloc[-1] - 100
    if "CPI Inflation" in chart_data and chart_data["CPI Inflation"].dropna().size >= 2:
        inflation_cost = chart_data["CPI Inflation"].dropna().iloc[-1] - 100
    if "Risk-Free (SBN)" in chart_data and chart_data["Risk-Free (SBN)"].dropna().size >= 2:
        sbn_cumulative_return = chart_data["Risk-Free (SBN)"].dropna().iloc[-1] - 100
    real_return = sp500_return - inflation_cost
    vs_sbn = sp500_return - sbn_cumulative_return

    metric_cols = st.columns(3)
    metric_cols[0].metric("S&P 500 Nominal Return", "N/A" if pd.isna(sp500_return) else f"{sp500_return:+.1f}%")
    metric_cols[1].metric(
        "Real Return (vs CPI)",
        "N/A" if pd.isna(real_return) else f"{real_return:+.1f}%",
        "Beating inflation ✓" if pd.notna(real_return) and real_return > 0 else "Losing to inflation ✗",
    )
    metric_cols[2].metric(
        "vs Risk-Free Rate (SBN)",
        "N/A" if pd.isna(vs_sbn) else f"{vs_sbn:+.1f}%",
        "Equity risk justified ✓" if pd.notna(vs_sbn) and vs_sbn > 0 else "SBN was better this period ✗",
    )

    render_recommendation(regime, dollar, ihsg_trend)
    render_history(regime, rate_cycle_month(fed))

    st.caption("Educational dashboard only — not financial advice. Fund availability on Bibit can change; update mappings manually before investing.")


if __name__ == "__main__":
    main()
