# services/finance_api.py
"""
Fetch financial statements and historical prices using yfinance.
Return a dict with keys:
- financials (DataFrame)   : income statement (columns are periods)
- balance_sheet (DataFrame): balance sheet
- cashflow (DataFrame)     : cashflow statement
- history (DataFrame)      : price history (index = DatetimeIndex)
- info (dict)              : ticker.info metadata
"""

from typing import Dict, Optional
import pandas as pd
import yfinance as yf


def _safe_df(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    # yfinance returns DataFrames with Periods as columns (DatetimeIndex-like)
    return df.fillna(pd.NA)


def fetch_financials_and_history(ticker: str, frequency: str = "annual", history_period: str = "1y", history_interval: str = "1d") -> Dict:
    """
    frequency: 'Annual' or 'Quarterly'
    history_period: '1y', '2y', '5y', '10y', etc.
    history_interval: '1d', '1wk', '1mo'
    """
    t = yf.Ticker(ticker)
    # info may raise in some cases; protect with try/except
    try:
        info = t.info or {}
    except Exception:
        info = {}

    # yfinance uses attributes: financials (annual), quarterly_financials
    if frequency == "quarterly":
        financials = _safe_df(t.quarterly_financials)
        balance = _safe_df(t.quarterly_balance_sheet)
        cashflow = _safe_df(t.quarterly_cashflow)
    else:
        financials = _safe_df(t.financials)
        balance = _safe_df(t.balance_sheet)
        cashflow = _safe_df(t.cashflow)

    # history
    try:
        history = t.history(period=history_period, interval=history_interval)
    except Exception:
        history = pd.DataFrame()

    # Return
    return {
        "financials": financials,
        "balance_sheet": balance,
        "cashflow": cashflow,
        "history": history,
        "info": info,
    }
