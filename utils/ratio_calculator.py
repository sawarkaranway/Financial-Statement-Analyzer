# utils/ratio_calculator.py
"""
Compute financial ratios from yfinance-style dataframes.

The yfinance financials and balance sheets are DataFrames where columns are periods
(e.g., Timestamp objects) and rows are account names like 'Net Income', 'Total Assets', etc.

This module extracts likely rows using heuristics and computes:
- ROA = Net Income / Total Assets
- ROE = Net Income / Total Equity (Total Stockholder Equity)
- Current Ratio = Total Current Assets / Total Current Liabilities
- Quick Ratio = (Current Assets - Inventory) / Current Liabilities
"""

from typing import Optional
import pandas as pd
import numpy as np


def _find_row(df: pd.DataFrame, possible_names):
    """Return a row (Series) matched by any of the names in possible_names (case-insensitively).
    If not found, return a series of NaNs with appropriate length."""
    if df is None or df.empty:
        return None
    lower_index = [str(i).lower() for i in df.index.astype(str)]
    for name in possible_names:
        name_l = name.lower()
        for idx, label in enumerate(lower_index):
            if name_l == label or name_l in label or label in name_l:
                return pd.to_numeric(df.iloc[idx], errors="coerce")
    return None


def compute_ratios_df(financials: Optional[pd.DataFrame], balance: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    Returns a DataFrame with columns:
    - Period (string)
    - ROA, ROE, Current Ratio, Quick Ratio
    Period ordering will match the order of columns in input financials/balance.
    """
    # If both are empty, return empty
    if (financials is None or financials.empty) and (balance is None or balance.empty):
        return pd.DataFrame()

    # Prefer financials columns for period labels; else balance
    source = financials if (financials is not None and not financials.empty) else balance
    if source is None or source.empty:
        return pd.DataFrame()

    # periods as strings
    periods = [str(c.date() if hasattr(c, "date") else c) for c in source.columns]

    # Extract key rows from financials & balance
    # Candidate names (common variants)
    net_income_names = ["Net Income", "NetIncome", "Net Income Applicable To Common Stockholders", "Net earnings"]
    total_assets_names = ["Total Assets", "TotalAssets"]
    total_equity_names = ["Total Stockholder Equity", "Total Equity", "TotalStockholderEquity"]
    current_assets_names = ["Total Current Assets", "Total Current Assets (Gross)", "Current Assets"]
    current_liabilities_names = ["Total Current Liabilities", "Current Liabilities"]
    inventory_names = ["Inventory", "Total Inventory"]

    net_income = _find_row(financials, net_income_names) if financials is not None else None
    total_assets = _find_row(balance, total_assets_names) if balance is not None else None
    total_equity = _find_row(balance, total_equity_names) if balance is not None else None
    current_assets = _find_row(balance, current_assets_names) if balance is not None else None
    current_liabilities = _find_row(balance, current_liabilities_names) if balance is not None else None
    inventory = _find_row(balance, inventory_names) if balance is not None else None

    # If any series is None, replace with NaN series matching periods length
    def ensure_length(s):
        if s is None:
            return pd.Series([np.nan] * len(periods))
        # coerce to numeric and align to columns order
        s = pd.to_numeric(s, errors="coerce")
        # If index and source.columns differ, try to reindex by the source columns
        try:
            s = s.reindex(source.columns).astype(float)
        except Exception:
            s = pd.Series(s.values, index=source.columns).astype(float)
        return s.reset_index(drop=True)

    net_income = ensure_length(net_income)
    total_assets = ensure_length(total_assets)
    total_equity = ensure_length(total_equity)
    current_assets = ensure_length(current_assets)
    current_liabilities = ensure_length(current_liabilities)
    inventory = ensure_length(inventory)

    # Safe divide
    with np.errstate(divide="ignore", invalid="ignore"):
        roa = net_income / total_assets
        roe = net_income / total_equity
        current_ratio = current_assets / current_liabilities
        quick_ratio = (current_assets - inventory) / current_liabilities

    # Replace inf with NaN
    roa = roa.replace([np.inf, -np.inf], np.nan)
    roe = roe.replace([np.inf, -np.inf], np.nan)
    current_ratio = current_ratio.replace([np.inf, -np.inf], np.nan)
    quick_ratio = quick_ratio.replace([np.inf, -np.inf], np.nan)

    out = pd.DataFrame({
        "Period": periods,
        "ROA": roa,
        "ROE": roe,
        "Current Ratio": current_ratio,
        "Quick Ratio": quick_ratio
    })

    # Keep ordering as seen in source (most recent first in yfinance)
    return out
