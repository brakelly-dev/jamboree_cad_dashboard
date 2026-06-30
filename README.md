# Jamboree Arrival Day Dashboard

## Setup

```bash
pip install -r requirements.txt
```

## Configure

1. Open `config.py` and paste your Google Sheet ID into `GOOGLE_SHEET_ID`.
   The Sheet ID is the long string in your Sheet URL:
   `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit`

2. Make the Sheet publicly readable:
   Share → Anyone with the link → Viewer.

3. Place your exported `jamboree_registry.json` (from the importer tool)
   in this folder. Or update `REGISTRY_PATH` in `config.py` to point
   to wherever it lives.

## Run

```bash
streamlit run app.py
```

The dashboard opens at http://localhost:8501 and auto-refreshes every 60 seconds.

## File structure

```
jamboree_dashboard/
├── app.py              # Streamlit entry point — the dashboard UI
├── config.py           # All settings: Sheet ID, column positions, thresholds
├── data_loader.py      # Loads registry JSON + fetches Google Sheet CSV
├── matcher.py          # Fuzzy unit name matching + checkpoint normalisation
├── state_manager.py    # Merges roster + check-ins into unit state table
├── charts.py           # Plotly figure builders
├── requirements.txt
└── jamboree_registry.json   # Your imported unit roster (from the importer)
```

## Adjusting column order

If you reorder questions in your Google Form, update `SHEET_COLUMNS` in `config.py`.
The values are 0-indexed column positions in the Sheet.

## Deploying publicly

To share the dashboard with others, deploy to Streamlit Community Cloud (free):
1. Push this folder to a GitHub repo.
2. Go to share.streamlit.io → New app → select your repo and `app.py`.
3. Add `GOOGLE_SHEET_ID` as a secret in the app settings if desired.

## Virtual environment (recommended)

Create and activate an isolated virtual environment before installing dependencies.

Windows (PowerShell):

```powershell
cd "path\to\cad_dashboard"
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:

```bash
cd path/to/cad_dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or run the helper scripts added to this folder: see `setup_venv.ps1` and `setup_venv.sh`.
