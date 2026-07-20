# state_manager.py — merges registry + check-ins into a single unit state table

import pandas as pd
from datetime import datetime
from matcher import find_best_match, normalize_checkpoint, CHECKPOINT_TO_STATUS
from config import STATUS_ORDER


# Pipeline rank so we never downgrade a unit's status
STATUS_RANK = {s: i for i, s in enumerate(STATUS_ORDER)}


def build_unit_states(registry: list[dict], checkins: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a DataFrame with one row per unit containing:
      unit_id, unit, council, transport, expected_time,
      basecamp, status, ruby_time, south_gate_time, onsite_time,
      last_checkin_notes, variance_minutes
    """
    # Start from registry — every unit initialised as Not arrived
    rows = []
    for unit in registry:
        rows.append({
            "unit_id":            unit.get("id", ""),
            "unit_number":        unit.get("unit_number", ""),
            "council":            unit.get("council", ""),
            "transport":          unit.get("transport", ""),
            "expected_time":      unit.get("expected_time", ""),
            "basecamp":           unit.get("basecamp", ""),
            "status":             "Not arrived",
            "ruby_time":          None,
            "south_gate_time":    None,
            "onsite_time":        None,
            "checkin_time":       None,
            "last_checkin_notes": "",
            "variance_minutes":   None,
            "unmatched_flags":    0,
        })

    state = {r["unit_number"]: r for r in rows}
    unmatched = []

    for _, row in checkins.iterrows():
        matched_unit = find_best_match(row["unit_number"], registry)
        checkpoint_key = normalize_checkpoint(row["checkpoint"])

        if matched_unit is None or checkpoint_key is None:
            unmatched.append({
                "raw_name":   row["unit_number"],
                "checkpoint": row["checkpoint"],
                "timestamp":  row["timestamp"],
                "notes":      row["notes"],
            })
            continue

        uname = matched_unit["unit_number"]
        if uname not in state:
            continue

        new_status = CHECKPOINT_TO_STATUS[checkpoint_key]
        current_status = state[uname]["status"]

        # Only advance status, never retreat
        if STATUS_RANK[new_status] > STATUS_RANK[current_status]:
            state[uname]["status"] = new_status

        ts = row["timestamp"]

        if checkpoint_key == "ruby" and state[uname]["ruby_time"] is None:
            state[uname]["ruby_time"] = ts
        elif checkpoint_key == "south_gate" and state[uname]["south_gate_time"] is None:
            state[uname]["south_gate_time"] = ts
        elif checkpoint_key == "basecamp" and state[uname]["onsite_time"] is None:
            state[uname]["onsite_time"] = ts
            state[uname]["variance_minutes"] = _compute_variance(
                matched_unit.get("expected_time", ""), ts
            )
        elif checkpoint_key == "check_in" and state[uname]["checkin_time"] is None:
            state[uname]["checkin_time"] = ts

        state[uname]["last_checkin_notes"] = row["notes"] or state[uname]["last_checkin_notes"]

    df = pd.DataFrame(list(state.values()))
    df["status"] = pd.Categorical(df["status"], categories=STATUS_ORDER, ordered=True)
    return df, unmatched


def _compute_variance(expected_str: str, actual_ts: datetime) -> float | None:
    """
    Returns actual minus expected in minutes (positive = late, negative = early).
    """
    if not expected_str:
        return None
    try:
        # Strip timezone info from actual_ts for a clean comparison
        actual_naive = actual_ts.replace(tzinfo=None)
        
        # Parse expected time (supports HH:MM and H:MM AM/PM)
        for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
            try:
                t = datetime.strptime(expected_str.strip(), fmt)
                # Reconstruct expected as a full datetime on the same date as actual
                expected = actual_naive.replace(
                    hour=t.hour, minute=t.minute, second=0, microsecond=0
                )
                # delta = (actual_naive - expected).total_seconds() / 60
                delta = (expected - actual_naive).total_seconds() / 60
                return round(delta, 1)
            except ValueError:
                continue
    except Exception:
        pass
    return None


def summary_stats(df: pd.DataFrame) -> dict:
    """Compute the four headline metrics for the dashboard."""
    total = len(df)
    checked_in = int((df["status"] == "Checked-in").sum())
    on_site = int((df["status"] == "On-site").sum())
    in_transit = int(df["status"].isin(["At Ruby", "At South Gate"]).sum())
    not_arrived = int((df["status"] == "Not arrived").sum())

    arrived_vars = df.loc[df["variance_minutes"].notna(), "variance_minutes"]
    avg_variance = round(arrived_vars.mean(), 1) if not arrived_vars.empty else None

    motor_coach = int(
        df["transport"].str.lower().str.contains("motor|coach|bus", na=False).sum()
    )
    personal = total - motor_coach

    return {
        "total":       total,
        "checked_in":  checked_in,
        "on_site":     on_site,
        "in_transit":  in_transit,
        "not_arrived": not_arrived,
        "avg_variance": avg_variance,
        "motor_coach": motor_coach,
        "personal_vehicle": personal,
    }


def arrival_distribution(df: pd.DataFrame, registry: list[dict]) -> pd.DataFrame:
    """
    Returns a DataFrame with columns: hour, projected, actual
    for the arrival distribution chart.
    """
    from config import STATUS_ORDER
    import re

    hours = list(range(6, 22))  # 6am to 9pm
    projected = {h: 0 for h in hours}
    actual = {h: 0 for h in hours}

    for unit in registry:
        t = unit.get("expected_time", "")
        h = _parse_hour(t)
        if h is not None and h in projected:
            projected[h] += 1

    for _, row in df.iterrows():
        if row["onsite_time"] is not None:
            h = row["onsite_time"].hour
            if h in actual:
                actual[h] += 1

    return pd.DataFrame({
        "hour":      hours,
        "projected": [projected[h] for h in hours],
        "actual":    [actual[h] for h in hours],
    })


def _parse_hour(time_str: str) -> int | None:
    if not time_str:
        return None
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(time_str.strip(), fmt).hour
        except ValueError:
            continue
    return None


def leg_durations(df: pd.DataFrame) -> dict:
    """
    Computes travel-time statistics (in minutes) for each leg of the journey:
      Ruby -> South Gate, South Gate -> Basecamp, Ruby -> Basecamp (direct).

    Returns a dict like:
      {
        "ruby_to_southgate": {"avg": 23.4, "min": 8.0, "max": 51.0, "count": 34, "values": [...]},
        "southgate_to_basecamp": {...},
        "ruby_to_basecamp": {...},
      }
    Units with missing timestamps for a given leg are simply excluded from that leg's stats.
    """
    legs = {
        "ruby_to_southgate":     [],
        "southgate_to_basecamp": [],
        "ruby_to_basecamp":      [],
    }

    for _, row in df.iterrows():
        ruby = row["ruby_time"]
        sg = row["south_gate_time"]
        onsite = row["onsite_time"]

        if pd.notna(ruby) and pd.notna(sg):
            delta = (sg - ruby).total_seconds() / 60
            if delta >= 0:  # guard against bad data ordering
                legs["ruby_to_southgate"].append(delta)

        if pd.notna(sg) and pd.notna(onsite):
            delta = (onsite - sg).total_seconds() / 60
            if delta >= 0:
                legs["southgate_to_basecamp"].append(delta)

        if pd.notna(ruby) and pd.notna(onsite):
            delta = (onsite - ruby).total_seconds() / 60
            if delta >= 0:
                legs["ruby_to_basecamp"].append(delta)

    result = {}
    for leg_name, values in legs.items():
        if values:
            result[leg_name] = {
                "avg":    round(sum(values) / len(values), 1),
                "min":    round(min(values), 1),
                "max":    round(max(values), 1),
                "count":  len(values),
                "values": values,
            }
        else:
            result[leg_name] = {"avg": None, "min": None, "max": None, "count": 0, "values": []}

    return result