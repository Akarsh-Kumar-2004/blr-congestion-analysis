"""
train_model.py
Run once to train the LightGBM models from the raw dataset and save
them as .pkl files that the Streamlit app will load.

Usage:
    python train_model.py --csv "path/to/Astram event data_anonymized.csv"
"""

import argparse
import pickle
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split

# ── helpers ──────────────────────────────────────────────────────────
CAT_COLS = [
    "event_type", "event_cause", "priority", "requires_road_closure",
    "zone", "junction", "corridor", "veh_type", "weekday",
]
FEATURE_COLS = CAT_COLS + ["hour", "month"]


def impact_class(score: float) -> str:
    if score <= 3:
        return "Low"
    elif score <= 5:
        return "Medium"
    elif score <= 7:
        return "High"
    else:
        return "Critical"


def dur_bucket(minutes):
    m = np.asarray(minutes)
    return np.where(m <= 30, 1, np.where(m <= 120, 2, 3))


def resource_plan(impact: str, road_closure: bool) -> dict:
    officers   = {"Low": 2, "Medium": 4, "High": 8, "Critical": 10}[impact]
    barricades = {"Low": 1, "Medium": 3, "High": 6, "Critical": 8}[impact]
    tow_veh    = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}[impact]
    diversion  = road_closure and impact in ("High", "Critical")
    return {
        "officers":   officers,
        "barricades": barricades,
        "tow_vehicles": tow_veh,
        "diversion":  diversion,
    }


# ── main ──────────────────────────────────────────────────────────────
def main(csv_path: str):
    print(f"Loading data from: {csv_path}")
    df = pd.read_csv(csv_path)

    # parse timestamps
    for col in ["start_datetime", "end_datetime", "closed_datetime", "resolved_datetime"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    # best-available clearance time
    end_best = (
        df["closed_datetime"]
        .fillna(df["end_datetime"])
        .fillna(df["resolved_datetime"])
    )
    df["duration_minutes_clean"] = (
        end_best - df["start_datetime"]
    ).dt.total_seconds() / 60
    df.loc[df["duration_minutes_clean"] <= 0, "duration_minutes_clean"] = np.nan

    # time features
    df["hour"]    = df["start_datetime"].dt.hour
    df["month"]   = df["start_datetime"].dt.month
    df["weekday"] = df["start_datetime"].dt.day_name()

    # formula ingredients
    df["priority_num"] = df["priority"].map({"Low": 1, "Medium": 2, "High": 3}).fillna(2)
    df["closure_num"]  = np.where(df["requires_road_closure"] == True, 2, 0)

    # filter rows with usable duration
    q99 = df["duration_minutes_clean"].quantile(0.99)
    d = df[df["duration_minutes_clean"].between(1, q99)].copy()
    d["log_dur"] = np.log1p(d["duration_minutes_clean"])

    features = [f for f in FEATURE_COLS if f in d.columns]
    cat_cols  = [c for c in CAT_COLS if c in features]

    X = d[features].copy()
    for c in cat_cols:
        X[c] = X[c].astype("category")
    y = d["log_dur"]

    X_train, X_test, y_train, _ = train_test_split(X, y, test_size=0.2, random_state=42)

    def fit_quantile(alpha):
        m = lgb.LGBMRegressor(
            objective="quantile", alpha=alpha,
            n_estimators=700, learning_rate=0.03,
            num_leaves=63, random_state=42, n_jobs=-1,
        )
        m.fit(X_train, y_train, categorical_feature=cat_cols)
        return m

    print("Training p50 model …")
    model_p50 = fit_quantile(0.5)
    print("Training p90 model …")
    model_p90 = fit_quantile(0.9)

    # collect unique category values for the UI drop-downs
    categories = {c: sorted(d[c].dropna().astype(str).unique().tolist()) for c in cat_cols}

    bundle = {
        "model_p50":   model_p50,
        "model_p90":   model_p90,
        "feature_cols": features,
        "cat_cols":    cat_cols,
        "train_cols":  X_train.columns.tolist(),
        "categories":  categories,
    }

    out = "d:/gridlock/gridlock_models.pkl"
    with open(out, "wb") as f:
        pickle.dump(bundle, f)
    print(f"Models saved to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to the event CSV file")
    args = parser.parse_args()
    main(args.csv)
