# app.py — Streamlit UI (single-page dashboard)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

# Local modules
from services.finance_api import fetch_financials_and_history
from utils.ratio_calculator import compute_ratios_df

# Optional: UI helpers (streamlit_shadcn_ui is optional; fallback to basic streamlit if not installed)
try:
    import streamlit_shadcn_ui as shad
except Exception:
    shad = None

st.set_page_config(page_title="📊 Financial Statement Analyzer", layout="wide", initial_sidebar_state="expanded")

HEADER_HTML = "<h1 style='text-align:center;'>📊 Financial Statement Analyzer</h1>"
st.markdown(HEADER_HTML, unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:gray;'>Enter a ticker to fetch financials, compute ratios and visualize trends.</p>",
            unsafe_allow_html=True)

# Sidebar inputs
with st.sidebar:
    st.header("Query")
    ticker_input = st.text_input("Ticker (e.g. AAPL, TSLA, INFY.NS)", value="")
    period = st.selectbox("Financials frequency", options=["annual", "quarterly"], index=0)
    hist_period = st.selectbox("Price history period", options=["1y", "2y", "5y", "10y"], index=0)
    hist_interval = st.selectbox("Price interval", options=["1d", "1wk", "1mo"], index=0)
    act = st.button("Fetch & Analyze")

st.info("Tip: use ticker symbols like AAPL, MSFT, TSLA or NSE tickers like INFY.NS")

if not ticker_input:
    st.stop()

if act:
    with st.spinner(f"Fetching data for {ticker_input}..."):
        try:
            # Fetch financial statements and price history
            fin_data = fetch_financials_and_history(
                ticker=ticker_input, frequency=period, history_period=hist_period, history_interval=hist_interval
            )
        except Exception as e:
            st.error(f"Failed to fetch data: {e}")
            st.stop()

    # Unpack
    financials_df = fin_data.get("financials")      # DataFrame (periods as cols)
    balance_df = fin_data.get("balance_sheet")
    cashflow_df = fin_data.get("cashflow")
    history_df = fin_data.get("history")           # historical prices

    # Header row with company info
    company_name = fin_data.get("info", {}).get("longName") or ticker_input
    st.subheader(f"{company_name} — {ticker_input}")

    # Top KPIs
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    info = fin_data.get("info", {})

    market_cap = info.get("marketCap")
    trailing_pe = info.get("trailingPE")
    profit_margin = info.get("profitMargins")

    col_kpi1.metric("Market Cap", f"${market_cap:,}" if market_cap else "N/A")
    col_kpi2.metric("Trailing P/E", f"{trailing_pe:.2f}" if trailing_pe else "N/A")
    col_kpi3.metric("Profit Margin", f"{profit_margin:.2%}" if profit_margin else "N/A")
    col_kpi4.metric("Previous Close", f"${info.get('previousClose', 'N/A')}")

    st.markdown("---")

    # Show raw frames (transpose to have periods as rows)
    st.markdown("### Financials & Balance Sheet (preview)")
    cols_show = st.columns(2)
    with cols_show[0]:
        st.write("Income Statement")
        if financials_df is None or financials_df.empty:
            st.warning("No income statement data available.")
        else:
            # Transpose so periods become rows
            st.dataframe(financials_df.T.head(8))

    with cols_show[1]:
        st.write("Balance Sheet")
        if balance_df is None or balance_df.empty:
            st.warning("No balance sheet data available.")
        else:
            st.dataframe(balance_df.T.head(8))

    # Compute ratios (returns DataFrame with Period + computed ratios)
    st.markdown("### Computed Ratios")
    try:
        ratios_df = compute_ratios_df(financials_df, balance_df)
    except Exception as e:
        st.error(f"Failed to compute ratios: {e}")
        ratios_df = None

    if ratios_df is not None and not ratios_df.empty:
        # Format display
        styled = ratios_df.copy()
        # Convert percent columns for nicer display
        st.dataframe(
            styled.style.format({
                "ROA": "{:.2%}",
                "ROE": "{:.2%}",
                "Current Ratio": "{:.2f}",
                "Quick Ratio": "{:.2f}"
            }),
            use_container_width=True
        )

        csv_buf = BytesIO()
        styled.to_csv(csv_buf, index=False)
        st.download_button("Download ratios CSV", csv_buf.getvalue(), file_name=f"{ticker_input}_ratios.csv", mime="text/csv")

        # Plots
        st.markdown("#### Ratio trends")
        metrics = ["ROA", "ROE", "Current Ratio", "Quick Ratio"]
        chosen = st.multiselect("Metrics to plot", options=metrics, default=metrics)

        if chosen:
            plot_df = ratios_df.melt(id_vars=["Period"], value_vars=chosen, var_name="Metric", value_name="Value")
            # Plotly line chart grouped by Metric
            fig = go.Figure()
            for metric in plot_df["Metric"].unique():
                dfm = plot_df[plot_df["Metric"] == metric]
                fig.add_trace(go.Scatter(x=dfm["Period"], y=dfm["Value"], mode="lines+markers", name=metric))
            fig.update_layout(title="Ratio Trends", xaxis_title="Period", yaxis_title="Value", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Ratios not available for this company / period.")

    st.markdown("---")

    # Price history chart
    st.markdown("### Historical Price")
    if history_df is None or history_df.empty:
        st.warning("No historical price available.")
    else:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=history_df.index, y=history_df["Close"], mode="lines", name="Close"))
        fig2.update_layout(title=f"{ticker_input} Close Price ({hist_period})", xaxis_title="Date", yaxis_title="Price", template="plotly_white")
        st.plotly_chart(fig2, use_container_width=True)

    # Basic diagnostics
    st.markdown("### Diagnostics")
    diag_msgs = []
    if ratios_df is not None:
        if ratios_df["ROA"].isna().all():
            diag_msgs.append("ROA could not be calculated — check if Net Income or Total Assets are present.")
        if ratios_df["ROE"].isna().all():
            diag_msgs.append("ROE could not be calculated — check if Net Income or Total Equity are present.")
    if diag_msgs:
        for m in diag_msgs:
            st.warning(m)
    else:
        st.success("No immediate calculation warnings detected.")

    st.markdown("---")
    st.caption("This free demo uses Yahoo Finance via yfinance. Data availability depends on the ticker and region.")
