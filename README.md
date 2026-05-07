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

Create `.streamlit/secrets.toml` locally or configure secrets in Streamlit Cloud. `FRED_API_KEY` and `RAPIDAPI_KEY` are different services and must use different keys:

```toml
# Required for FRED series such as FEDFUNDS, CPIAUCSL, DGS2, and DGS10.
# Get this from https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY = "paste_your_st_louis_fred_key_here"

# Required for the risk-free comparison line. Update manually for new ORI/SBR offerings.
SBN_YIELD = 0.065

# Optional. Without it, Fear & Greed is approximated from VIX.
# This is the RapidAPI key, not the FRED key.
RAPIDAPI_KEY = "paste_your_rapidapi_key_here"
```

Do not paste literal `\n` characters into Streamlit Cloud secrets. Each key must be on its own line in TOML format. If you add or change `FRED_API_KEY` after the app has already run, reboot the Streamlit app or clear its cache so the 24-hour data cache refreshes with the new key.

If the app still says `FRED_API_KEY is missing`, open the in-app **Configuration check** expander. It shows only whether the app can see each secret and the secret length; it never prints the secret value. If `FRED_API_KEY detected` is `False`, the deployed app is not receiving that secret, usually because the secret was saved on a different app, the TOML was not saved successfully, the app was not rebooted, or Streamlit Cloud is still running an older branch/commit.

`SBN_YIELD` should be updated manually when a new ORI/SBR offering changes the relevant risk-free comparison rate.
