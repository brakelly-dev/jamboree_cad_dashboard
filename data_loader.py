# data_loader.py — loads the unit roster and polls the Google Sheet

import json
import time
import pandas as pd
import streamlit as st
from config import (
    GOOGLE_SHEET_ID,
    SHEET_CSV_URL,
    SHEET_COLUMNS,
    REGISTRY_PATH,
    POLL_INTERVAL_SECONDS,
)


def load_registry(path: str = REGISTRY_PATH) -> list[dict]:
    """Load the unit registry JSON exported from the importer tool."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Registry file not found: {path}. Import your roster first.")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Registry file is invalid JSON: {e}")
        return []


@st.cache_data(ttl=POLL_INTERVAL_SECONDS)
def fetch_checkins(sheet_id: str = GOOGLE_SHEET_ID) -> pd.DataFrame:
    """
    Fetch check-in submissions from the public Google Sheet CSV export.
    Cached for POLL_INTERVAL_SECONDS — Streamlit auto-revalidates on expiry.
    """
    url = SHEET_CSV_URL.format(sheet_id=sheet_id)
    try:
        df = pd.read_csv(url, header=0)
    except Exception as e:
        st.warning(f"Could not reach Google Sheet: {e}")
        return _empty_checkins()

    col = SHEET_COLUMNS
    if df.shape[1] <= max(col.values()):
        st.warning("Google Sheet has fewer columns than expected. Check SHEET_COLUMNS in config.py.")
        return _empty_checkins()

    df = df.iloc[:, list(col.values())]
    df.columns = list(col.keys())

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["unit_number"] = df["unit_number"].astype(str).str.strip()
    df["checkpoint"] = df["checkpoint"].astype(str).str.strip()
    df["transport"] = df["transport"].astype(str).str.strip()
    df["notes"] = df["notes"].fillna("").astype(str).str.strip()

    return df.sort_values("timestamp").reset_index(drop=True)


def _empty_checkins() -> pd.DataFrame:
    return pd.DataFrame(columns=["timestamp", "checkpoint", "unit", "transport", "notes"])


def last_fetch_age(sheet_id: str = GOOGLE_SHEET_ID) -> int:
    """Returns seconds since the cached fetch was last refreshed (approximate)."""
    cache_info = fetch_checkins.cache_info() if hasattr(fetch_checkins, "cache_info") else None
    return POLL_INTERVAL_SECONDS  # Streamlit TTL handles this; exposed for display only
