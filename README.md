# Gridlock

Traffic event forecasting + resource planning for Bengaluru.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501

## What it does

1. **Event Impact Predictor** — you enter event details (cause, priority, location, time), it predicts clearance time + impact level
2. **Resource Planner** — shows how many officers, barricades, tow vehicles you need
3. **Historical Hotspots** — charts from 8,173 real incidents (peak hours, high-risk zones, causes)
4. **Live Risk Map** — real incidents on a map, shows predicted vs actual clearance
5. **Scenario Simulator** — change one variable (e.g. road closure), see how impact changes
6. **Feedback & Retraining** — tracks model accuracy, detects when it's degrading, flags for retraining

## Model

- LightGBM quantile regression (predicts p50 and p90 clearance time)
- Trained on 2,818 events from Astram dataset
- No data leakage (features are creation-time only)
- 86% accuracy on impact classification, median error 49.8 min

## Data Storage

- Predictions logged to `gridlock_feedback.db` (SQLite)
- When incident resolves, officer enters actual time
- System calculates error and detects drift
- If accuracy drops >20%, retraining is flagged

## Map Data

The 50 markers on the Live Risk Map are real test-set incidents. Each has:
- Real GPS coordinates from the dataset
- Real predicted clearance (what model_p50 returned)
- Real actual clearance (from incident timestamps)
- Real error (predicted vs actual)

No synthetic data anywhere.

## Files

- `app.py` — the app (6 screens)
- `model_p50.pkl`, `model_p90.pkl` — trained models
- `feedback_store.py` — database operations
- `gridlock_feedback.db` — where predictions are stored
- `map_incidents.json` — 50 real incidents
- `build_map_data.py` — generates map data from test set

## Setup

Run `python build_map_data.py` once to initialize the database and generate map data.

## How it's different

- Real feedback loop (not just text about it)
- Real data (8,173 actual incidents)
- Drift detection that actually works
- Scenario simulator (shows the model is actionable)
- No misleading accuracy percentages
