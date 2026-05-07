# Macro-Driven Index Rotation Dashboard

A stateless Streamlit Cloud dashboard for monthly DCA investors using Bibit Indonesia funds. The app reads live macro data, classifies the current regime, and maps the regime to concrete overweight/hold/underweight fund actions.

## Features

- Seven macro signals: yield curve, CPI inflation, Fed rate trend, US dollar strength, VIX risk sentiment, BTC sentiment, and IHSG trend.
- Six-regime macro classifier: `CRISIS`, `TIGHTENING`, `INFLATION`, `RISK ON`, `RISK OFF`, and `NEUTRAL`.
- Bibit fund recommendation mapping for monthly DCA decisions.
- Real wealth chart comparing S&P 500, IHSG, gold, CPI inflation, and the manually configured SBN yield.
- Dark, mobile-readable single-page layout with green/yellow/red status cues.
- All external fetches are cached for 24 hours and wrapped with warning fallbacks.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Streamlit secrets

FRED data is fetched through Nasdaq Data Link's public FRED dataset endpoint, so no FRED API key is required. Secrets are only needed for the manually configured SBN yield and the optional RapidAPI Fear & Greed source.

The real `.streamlit/secrets.toml` file is intentionally not committed because it can contain private API keys and is ignored by Git. Use the committed template to create your local secrets file:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml` locally, or configure the same values in Streamlit Cloud:

```toml
SBN_YIELD = 0.065
# Optional; without it, Fear & Greed is approximated from VIX.
RAPIDAPI_KEY = "your_rapidapi_key"
```

`SBN_YIELD` should be updated manually when a new ORI/SBR offering changes the relevant risk-free comparison rate.
