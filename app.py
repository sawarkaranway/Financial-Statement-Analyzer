# app.py — Streamlit UI (single-page dashboard) with integrated Gemini chatbot
import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
from chatbot import configure_gemini, ask_gemini
import os


# Gemini SDK
import google.generativeai as genai

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
    # --- Overall Analysis Summary (Based on KPI Constraints) ---
    st.markdown("## 📈 Overall Analysis Summary")

    if ratios_df is not None and not ratios_df.empty:
        try:
            # --- Select the most recent period/year ---
            # Ensure Period column exists and is sorted properly
            if "Period" in ratios_df.columns:
                try:
                    ratios_df["Period_parsed"] = pd.to_datetime(ratios_df["Period"], errors="coerce")
                    latest_row = ratios_df.sort_values(by="Period_parsed", ascending=False).iloc[0]
                except Exception:
                    # fallback if not datetime — try sorting lexicographically
                    latest_row = ratios_df.sort_values(by="Period", ascending=False).iloc[0]
            else:
                # fallback if Period column missing
                latest_row = ratios_df.iloc[-1]

            latest = latest_row.to_dict()

            current_ratio = latest.get("Current Ratio")
            quick_ratio = latest.get("Quick Ratio")
            roa = latest.get("ROA")
            roe = latest.get("ROE")

            summary = []

            # --- Current Ratio ---
            if current_ratio is not None and not pd.isna(current_ratio):
                if current_ratio > 1:
                    summary.append(f"✅ **Current Ratio ({current_ratio:.2f})** indicates a strong ability to meet short-term obligations using current assets.")
                elif current_ratio < 1:
                    summary.append(f"⚠️ **Current Ratio ({current_ratio:.2f})** suggests possible liquidity issues as liabilities exceed current assets.")
                else:
                    summary.append(f"ℹ️ **Current Ratio ({current_ratio:.2f})** is at threshold; liquidity position is adequate but could improve.")

            # --- Quick Ratio ---
            if quick_ratio is not None and not pd.isna(quick_ratio):
                if quick_ratio > 1:
                    summary.append(f"✅ **Quick Ratio ({quick_ratio:.2f})** shows strong liquidity even without relying on inventory.")
                elif quick_ratio < 1:
                    summary.append(f"⚠️ **Quick Ratio ({quick_ratio:.2f})** indicates potential short-term cash flow risk if inventory is slow moving.")
                else:
                    summary.append(f"ℹ️ **Quick Ratio ({quick_ratio:.2f})** suggests moderate liquidity, borderline case.")

            # --- ROA ---
            if roa is not None and not pd.isna(roa):
                if roa >= 0.10:
                    summary.append(f"✅ **ROA ({roa:.2%})** shows excellent operational efficiency and effective use of assets.")
                elif roa < 0.05:
                    summary.append(f"⚠️ **ROA ({roa:.2%})** indicates weak efficiency in using assets to generate profit.")
                else:
                    summary.append(f"ℹ️ **ROA ({roa:.2%})** is moderate, showing average asset utilization.")

            # --- ROE ---
            if roe is not None and not pd.isna(roe):
                if roe > 0.15:
                    summary.append(f"✅ **ROE ({roe:.2%})** reflects excellent profitability and strong returns for shareholders.")
                elif 0.05 <= roe <= 0.10:
                    summary.append(f"ℹ️ **ROE ({roe:.2%})** indicates average profitability; potential exists for improvement.")
                elif roe < 0.05:
                    summary.append(f"⚠️ **ROE ({roe:.2%})** is poor, showing low returns on shareholder equity.")
                else:
                    summary.append(f"✅ **ROE ({roe:.2%})** is good, showing consistent performance.")

            # --- Final Display ---
            if summary:
                st.markdown(f"**Period Analyzed:** {latest.get('Period', 'Most Recent')}")
                for point in summary:
                    st.markdown(point)
            else:
                st.info("Insufficient data to generate detailed summary.")
        except Exception as e:
            st.error(f"Error generating summary: {e}")
    else:
        st.info("Financial ratios unavailable — cannot generate overall analysis summary.")

    st.markdown("----")
    st.markdown("## 💬 Ask the AI Chatbot")

    # ---------------------------
# Conversational Chatbot Integration (fixed: safe clearing of input)
# ---------------------------
from chatbot import configure_gemini, ask_gemini
import os

st.markdown("----")
st.markdown("## 💬 AI Chatbot (conversational)")

# --- Load Gemini API key safely ---
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
elif "GEMINI_API_KEY" in os.environ:
    api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.warning("⚠️ Gemini API key not found. Add GEMINI_API_KEY to .streamlit/secrets.toml or export it as an environment variable to enable the chatbot.")
else:
    # configure gemini once
    try:
        configure_gemini(api_key)
    except Exception as e:
        st.error(f"Failed to configure Gemini SDK: {e}")
        api_key = None

# Only proceed if key configured
if api_key:
    # initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []  # list of {"role":"user"|"assistant","content":...}

    # initialize clear flag if missing
    if "clear_chat_input" not in st.session_state:
        st.session_state["clear_chat_input"] = False

    # If flagged to clear, do it BEFORE creating the widget
    if st.session_state.get("clear_chat_input", False):
        # safe to assign because widget not yet created
        st.session_state["chat_input"] = ""
        st.session_state["clear_chat_input"] = False

    # Display previous messages
    st.markdown("#### Conversation")
    if st.session_state["chat_history"]:
        for msg in st.session_state["chat_history"]:
            if msg.get("role") == "user":
                st.markdown(f"**You:** {msg.get('content')}")
            else:
                st.markdown(f"**AI:** {msg.get('content')}")
    else:
        st.info("No conversation yet — ask a question below about this company's ratios or KPIs.")

    # Input row (text + send button)
    col_inp, col_btn = st.columns([8, 1])
    with col_inp:
        # use key 'chat_input' so we can persist value in session_state
        st.text_input(
            "Ask about financial performance, ratios or investment insights:",
            placeholder="e.g. Is the liquidity healthy? What should I watch for next?",
            key="chat_input"
        )
    with col_btn:
        send = st.button("Send", key="send_button")

    # Handle send button press
    if send:
        user_question = st.session_state.get("chat_input", "").strip()
        if not user_question:
            st.info("Please type a question before sending.")
        else:
            # Build context from latest ratios and KPIs
            if "ratios_df" in locals() and ratios_df is not None and not ratios_df.empty:
                try:
                    context_row = latest_row if "latest_row" in locals() else ratios_df.sort_values(by="Period", ascending=False).iloc[0]
                except Exception:
                    context_row = ratios_df.iloc[-1]
                context_text = "\n".join([f"{k}: {v}" for k, v in context_row.to_dict().items()])
            else:
                context_text = "No ratio data available."

            # Append user message to history
            st.session_state["chat_history"].append({"role": "user", "content": user_question})

            # Call the chatbot (network call may take time)
            with st.spinner("Analyzing with Gemini..."):
                try:
                    ai_reply = ask_gemini(user_query=user_question, context=context_text, chat_history=st.session_state["chat_history"])
                except Exception as e:
                    st.error(f"Chatbot error: {e}")
                    ai_reply = None

            if ai_reply:
                # store assistant reply
                st.session_state["chat_history"].append({"role": "assistant", "content": ai_reply})

                # flag to clear the input on next run (must be cleared BEFORE widget creation)
                st.session_state["clear_chat_input"] = True

                # rerun so UI updates and input gets cleared safely
                st.rerun()
