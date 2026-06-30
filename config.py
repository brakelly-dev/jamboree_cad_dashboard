# config.py — all environment settings and constants

import streamlit as st
GOOGLE_SHEET_ID = st.secrets.get("GOOGLE_SHEET_ID", "YOUR_SHEET_ID_HERE")

# Find this in the Sheet's URL after "#gid=" when that tab is open.
SHEET_GID = "1704716365"

# Column positions in the Google Form response sheet (0-indexed)
# Adjust if you reorder questions in the form
SHEET_COLUMNS = {
    "timestamp":  0,
    "checkpoint": 1,
    "unit_number":  2,
    "transport":  3,
    "notes":      4,
}

# Canonical checkpoint names (must match form options exactly)
CHECKPOINTS = {
    "ruby":        "Ruby Welcome Center",
    "south_gate": "South Gate",
    "basecamp":   "Basecamp",
}

# Status labels — order matters (pipeline progression)
STATUS_ORDER = ["Not arrived", "At Ruby", "At South Gate", "On-site"]

STATUS_COLORS = {
    "Not arrived":   "#888780",
    "At Ruby":       "#BA7517",
    "At South Gate": "#185FA5",
    "On-site":       "#3B6D11",
}

# Fuzzy match threshold (0–100). Lower = more permissive.
FUZZY_MATCH_THRESHOLD = 75

# How often to re-fetch the Google Sheet (seconds)
POLL_INTERVAL_SECONDS = 60

# Path to the registry JSON exported from the importer tool
REGISTRY_PATH = "jamboree_registry.json" # This is where unit information is stored

# Google Sheets public CSV export URL template
SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/{sheet_id}"
    "/export?format=csv&gid=" + SHEET_GID
)
