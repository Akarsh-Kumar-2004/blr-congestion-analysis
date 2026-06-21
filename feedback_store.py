"""
feedback_store.py
------------------
SQLite-backed store for:
  1. Logging every prediction made by the app
  2. Recording actual outcomes when incidents resolve
  3. Computing accuracy drift over time
  4. Triggering retraining when drift threshold is crossed

This is the "gets smarter over time" pillar.
All state persists in gridlock_feedback.db (SQLite, no server needed).
"""

import sqlite3
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "gridlock_feedback.db")


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA SETUP
# ─────────────────────────────────────────────────────────────────────────────
def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS predictions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id        TEXT UNIQUE,
            created_at      TEXT NOT NULL,
            -- input features
            event_type      TEXT,
            event_cause     TEXT,
            priority        TEXT,
            road_closure    INTEGER,
            zone            TEXT,
            corridor        TEXT,
            hour            INTEGER,
            month           INTEGER,
            weekday         TEXT,
            -- model outputs
            pred_p50        REAL,
            pred_p90        REAL,
            pred_impact     TEXT,
            -- ground truth (filled when incident resolves)
            actual_minutes  REAL,
            actual_impact   TEXT,
            resolved_at     TEXT,
            -- computed error
            abs_error       REAL
        );

        CREATE TABLE IF NOT EXISTS accuracy_snapshots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_at     TEXT NOT NULL,
            n_resolved      INTEGER,
            median_abs_error REAL,
            pct_correct_impact REAL,
            retrain_triggered INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# WRITE OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────
def log_prediction(event_id: str, event: dict, p50: float, p90: float, impact: str):
    """Called when the app makes a prediction. Stores inputs + model output."""
    conn = _get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO predictions
          (event_id, created_at,
           event_type, event_cause, priority, road_closure,
           zone, corridor, hour, month, weekday,
           pred_p50, pred_p90, pred_impact)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        event_id,
        datetime.now(timezone.utc).isoformat(),
        event.get("event_type"),
        event.get("event_cause"),
        event.get("priority"),
        int(bool(event.get("requires_road_closure"))),
        event.get("zone"),
        event.get("corridor"),
        event.get("hour"),
        event.get("month"),
        event.get("weekday"),
        round(p50, 1),
        round(p90, 1),
        impact,
    ))
    conn.commit()
    conn.close()


def record_actual(event_id: str, actual_minutes: float):
    """
    Called when an incident resolves. Fills in ground truth and computes error.
    Also recomputes impact from actual duration and updates accuracy.
    """
    conn = _get_conn()
    row = conn.execute(
        "SELECT pred_p50, pred_impact, priority, road_closure FROM predictions WHERE event_id=?",
        (event_id,)
    ).fetchone()

    if row is None:
        conn.close()
        return False

    pred_p50   = row["pred_p50"]
    abs_error  = abs(pred_p50 - actual_minutes)

    # Recompute actual impact using same formula
    pri_n  = {"Low":1, "Medium":2, "High":3}.get(row["priority"], 2)
    clos_n = 2 if row["road_closure"] else 0
    dbk    = 1 if actual_minutes <= 30 else (2 if actual_minutes <= 120 else 3)
    score  = pri_n + clos_n + dbk
    if score <= 3:   actual_impact = "Low"
    elif score <= 5: actual_impact = "Medium"
    elif score <= 7: actual_impact = "High"
    else:            actual_impact = "Critical"

    conn.execute("""
        UPDATE predictions
        SET actual_minutes=?, actual_impact=?, resolved_at=?, abs_error=?
        WHERE event_id=?
    """, (
        round(actual_minutes, 1),
        actual_impact,
        datetime.now(timezone.utc).isoformat(),
        round(abs_error, 1),
        event_id,
    ))
    conn.commit()
    conn.close()
    return True


# ─────────────────────────────────────────────────────────────────────────────
# READ / ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────
def get_all_predictions() -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql_query("SELECT * FROM predictions ORDER BY created_at DESC", conn)
    conn.close()
    return df


def get_resolved() -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM predictions WHERE actual_minutes IS NOT NULL ORDER BY resolved_at DESC",
        conn,
    )
    conn.close()
    return df


def accuracy_report() -> dict:
    """
    Compute current accuracy metrics over all resolved incidents.
    Returns dict with:
      - n_resolved: how many incidents have ground truth
      - median_abs_error: MedAE in minutes (main metric)
      - pct_correct_impact: % where pred_impact == actual_impact
      - drift_flag: True if median error has grown >= 20% vs baseline (49.8 min)
      - retrain_recommended: True if drift_flag AND n_resolved >= 50
    """
    df = get_resolved()
    if df.empty:
        return {
            "n_resolved": 0,
            "median_abs_error": None,
            "pct_correct_impact": None,
            "drift_flag": False,
            "retrain_recommended": False,
            "message": "No resolved incidents yet. Predictions are being logged.",
        }

    n = len(df)
    medae = round(float(np.median(df["abs_error"].dropna())), 1)
    pct_correct = round(
        (df["pred_impact"] == df["actual_impact"]).mean() * 100, 1
    )

    baseline_medae = 49.8   # from training — the reference point
    drift_flag = medae > baseline_medae * 1.20   # >20% degradation triggers warning
    retrain_recommended = drift_flag and n >= 50  # need 50+ resolved to be meaningful

    return {
        "n_resolved": n,
        "median_abs_error": medae,
        "baseline_medae": baseline_medae,
        "pct_correct_impact": pct_correct,
        "drift_flag": drift_flag,
        "retrain_recommended": retrain_recommended,
        "message": (
            "⚠️ Accuracy drift detected — retraining recommended."
            if retrain_recommended else
            "✅ Model performing within baseline tolerance."
            if n >= 5 else
            f"Tracking {n} resolved incident(s). Need 50+ for drift detection."
        ),
    }


def take_accuracy_snapshot(triggered_retrain: bool = False):
    """Save a point-in-time accuracy snapshot to the snapshots table."""
    report = accuracy_report()
    if report["n_resolved"] == 0:
        return
    conn = _get_conn()
    conn.execute("""
        INSERT INTO accuracy_snapshots
          (snapshot_at, n_resolved, median_abs_error, pct_correct_impact, retrain_triggered)
        VALUES (?,?,?,?,?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        report["n_resolved"],
        report["median_abs_error"],
        report["pct_correct_impact"],
        int(triggered_retrain),
    ))
    conn.commit()
    conn.close()


def get_accuracy_history() -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM accuracy_snapshots ORDER BY snapshot_at ASC", conn
    )
    conn.close()
    return df
