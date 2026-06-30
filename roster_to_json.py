#!/usr/bin/env python3
"""
roster_to_json.py — Convert a Jamboree unit roster (CSV or Excel) into the
jamboree_registry.json format used by the dashboard.

USAGE
-----
    python roster_to_json.py roster.xlsx
    python roster_to_json.py roster.csv -o my_registry.json
    python roster_to_json.py roster.xlsx --sheet "Units"

What it does
------------
1. Reads your CSV/XLSX file.
2. Auto-detects which of your columns map to: unit_number, council,
   expected_time, transport, unit_type, size, basecamp, notes.
3. Validates each row (missing required fields, unparseable times,
   unrecognized transport values, duplicate unit names).
4. Writes a clean jamboree_registry.json, ready to drop into the
   dashboard folder next to app.py.
5. Prints a summary of what was imported and any rows skipped.

Required columns in your spreadsheet (any name/order — auto-detected):
    Unit name, Council, Expected arrival time, Transport type

Optional columns:
    Unit type, Size, Basecamp, Notes
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ── Column auto-detection aliases ────────────────────────────────────────────
ALIASES = {
    "unit_number":   ["unit number", "unit name", "unit", "troop", "crew", "name", "ship", "team"],
    "council":       ["council", "bsa council"],
    "expected_time": ["expected arrival time", "eta"],
    "transport":     ["transport", "vehicle", "bus", "transport type", "travel"],
    "unit_type":     ["variant", "unit type", "program", "category"],
    "size":          ["size", "members", "count", "participants", "headcount"],
    "basecamp":      ["basecamp", "camp", "site", "assigned basecamp", "assignment"],
    "subcamp":       ["subcamp", "subcampus", "area", "section"],
    "notes":         ["notes", "comments", "remarks", "other"],
}

REQUIRED_FIELDS = ["unit_number", "council", "expected_time", "transport"]


def detect_columns(headers: list[str]) -> dict[str, str]:
    """Map registry field -> actual column header found in the file."""
    lower_headers = {h: h.lower().strip() for h in headers}
    mapping = {}
    for field, aliases in ALIASES.items():
        best_match = None
        for header, lower in lower_headers.items():
            if any(alias in lower for alias in aliases):
                best_match = header
                break
        if best_match:
            mapping[field] = best_match
    return mapping


def parse_time(raw: str) -> str | None:
    """Normalize a time string to 'HH:MM' (24h). Returns None if unparseable."""
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw:
        return None

    # Already a datetime/time object from pandas/openpyxl
    if isinstance(raw, (pd.Timestamp,)):
        return raw.strftime("%H:%M")

    formats = ["%H:%M", "%I:%M %p", "%I:%M%p", "%H:%M:%S", "%I:%M:%S %p"]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None


def normalize_transport(raw: str) -> str:
    """Normalize transport free text to 'Motor Coach' or 'Personal Vehicle'."""
    if not raw:
        return ""
    low = str(raw).lower()
    if any(k in low for k in ["motor", "coach", "bus"]):
        return "Motor Coach"
    if any(k in low for k in ["personal", "vehicle", "car", "pov"]):
        return "Personal Vehicle"
    return str(raw).strip()


def load_table(path: Path, sheet: str | None) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    elif ext in (".xlsx", ".xls", ".xlsm"):
        return pd.read_excel(path, sheet_name=sheet or 0, dtype=str, keep_default_na=False)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use .csv or .xlsx")


def convert(input_path: str, output_path: str, sheet: str | None) -> None:
    path = Path(input_path)
    if not path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    df = load_table(path, sheet)
    df.columns = [str(c).strip() for c in df.columns]

    col_map = detect_columns(list(df.columns))

    missing_required = [f for f in REQUIRED_FIELDS if f not in col_map]
    if missing_required:
        print("Error: could not auto-detect these required columns:", file=sys.stderr)
        for f in missing_required:
            print(f"  - {f}", file=sys.stderr)
        print(f"\nColumns found in your file: {list(df.columns)}", file=sys.stderr)
        print("\nRename your column headers to something recognizable "
              "(e.g. 'Unit Name', 'Council', 'Expected Arrival', 'Transport') "
              "and try again.", file=sys.stderr)
        sys.exit(1)

    print("Detected column mapping:")
    for field, header in col_map.items():
        print(f"  {field:15s} <- \"{header}\"")
    print()

    registry = []
    errors = []
    warnings = []
    seen_names = {}

    for i, row in df.iterrows():
        row_num = i + 2  # +1 for 0-index, +1 for header row

        unit_number = str(row.get(col_map["unit_number"], "")).strip()
        council = str(row.get(col_map["council"], "")).strip()
        raw_time = row.get(col_map["expected_time"], "")
        raw_transport = str(row.get(col_map["transport"], "")).strip()

        if not unit_number:
            errors.append(f"Row {row_num}: missing unit name — skipped")
            continue
        if not council:
            errors.append(f"Row {row_num} ({unit_number}): missing council — skipped")
            continue

        expected_time = parse_time(raw_time)
        if expected_time is None:
            errors.append(
                f"Row {row_num} ({unit_number}): unparseable time \"{raw_time}\" — skipped"
            )
            continue

        transport = normalize_transport(raw_transport)
        if transport not in ("Motor Coach", "Personal Vehicle"):
            warnings.append(
                f"Row {row_num} ({unit_number}): unrecognized transport \"{raw_transport}\""
            )

        if unit_number in seen_names:
            warnings.append(
                f"Row {row_num}: duplicate unit name \"{unit_number}\" "
                f"(also row {seen_names[unit_number]})"
            )
        seen_names[unit_number] = row_num

        unit = {
            "id":             f"unit_{len(registry) + 1}",
            "unit_number":      unit_number,
            "council":        council,
            "expected_time":  expected_time,
            "transport":      transport,
            "unit_type":      str(row.get(col_map.get("unit_type", ""), "")).strip() or "Troop",
            "size":           str(row.get(col_map.get("size", ""), "")).strip(),
            "basecamp":       str(row.get(col_map.get("basecamp", ""), "")).strip(),
            "subcamp":        str(row.get(col_map.get("subcamp", ""), "")).strip(),
            "notes":          str(row.get(col_map.get("notes", ""), "")).strip(),
            "status":         "Not arrived",
            "rwc_time":       None,
            "south_gate_time": None,
            "onsite_time":    None,
        }
        registry.append(unit)

    out_path = Path(output_path)
    with open(out_path, "w") as f:
        json.dump(registry, f, indent=2)

    print(f"Wrote {len(registry)} units to {out_path.resolve()}\n")

    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
        print()

    if errors:
        print(f"{len(errors)} row(s) skipped due to errors:")
        for e in errors:
            print(f"  - {e}")
        print()

    motor_coach = sum(1 for u in registry if u["transport"] == "Motor Coach")
    personal = len(registry) - motor_coach
    print(f"Summary: {len(registry)} units total "
          f"({motor_coach} motor coach, {personal} personal vehicle)")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a Jamboree unit roster (CSV/Excel) into registry JSON."
    )
    parser.add_argument("input", help="Path to the roster .csv or .xlsx file")
    parser.add_argument(
        "-o", "--output", default="jamboree_registry.json",
        help="Output JSON path (default: jamboree_registry.json)"
    )
    parser.add_argument(
        "--sheet", default=None,
        help="Sheet name to read, for multi-sheet Excel files (default: first sheet)"
    )
    args = parser.parse_args()
    convert(args.input, args.output, args.sheet)


if __name__ == "__main__":
    main()