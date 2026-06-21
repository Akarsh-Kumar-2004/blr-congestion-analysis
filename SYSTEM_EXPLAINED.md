# How Every Piece of the System Actually Works

This document answers the exact questions:
- Is retraining happening automatically?
- Where is live data stored?
- Is the feedback loop real?
- What are those map markers — real data or made up?

---

## ❓ Is retraining happening automatically?

**Short answer: No — and that's intentional. Here's why and what does happen.**

### What IS automated:
- Every prediction made via the app is **immediately written to `gridlock_feedback.db`** (SQLite)
- Every time an officer enters an actual outcome, the DB updates the error and recalculates accuracy
- Drift detection runs automatically on every page load of "Feedback & Retraining"
- Accuracy snapshots can be triggered with one click

### What requires a manual step:
- Retraining itself — running `python train_model.py --csv <new_data.csv>`
- This is intentional. Automatic retraining without human review is dangerous in operational systems

### Why not fully automatic?
In traffic management, a bad model update could send the wrong number of officers
to a critical incident. The system flags drift, a supervisor reviews it, then approves retrain.
That's the correct pattern for safety-critical ML.

### The drift detection logic:
```python
baseline_medae = 49.8  # min (from original training evaluation)
drift_flag = current_medae > baseline_medae * 1.20  # >20% degradation
retrain_recommended = drift_flag AND n_resolved >= 50
```

If both conditions are true, a red banner appears on the Feedback screen
and the retrain command is shown. Officer runs it, replaces pkl files, restarts app.

---

## ❓ Where is live data stored?

Everything goes into **`gridlock_feedback.db`** — a SQLite file in the project folder.

### Schema:

**Table: `predictions`**
```sql
id, event_id, created_at,
-- what was reported (features at creation time)
event_type, event_cause, priority, road_closure,
zone, corridor, hour, month, weekday,
-- what the model forecast
pred_p50, pred_p90, pred_impact,
-- what actually happened (filled when incident resolves)
actual_minutes, actual_impact, resolved_at,
-- computed
abs_error
```

**Table: `accuracy_snapshots`**
```sql
id, snapshot_at, n_resolved,
median_abs_error, pct_correct_impact,
retrain_triggered
```

### What triggers a write:
| Action | What gets written |
|--------|-------------------|
| Officer uses Event Impact Predictor | `predictions` row with features + forecast |
| Officer enters actual outcome | `predictions` row updated with actual_minutes + abs_error |
| "Save Accuracy Snapshot" clicked | New row in `accuracy_snapshots` |

### Does this feed into training?
Yes, indirectly. When you retrain:
```bash
python train_model.py --csv <new_or_augmented_csv>
```
You can export the feedback DB and append it to the training CSV. The train script
reuses the same split + feature engineering. New models replace the pkl files.

---

## ❓ Is the feedback loop real?

**Yes. Here is the complete, real loop:**

```
1. Officer opens Event Impact Predictor
   → Fills: cause=vehicle_breakdown, priority=High, zone=West Zone 1,
            hour=18, road_closure=True
   → App runs model_p50.predict() + model_p90.predict()
   → Shows: "Expected 95 min, worst-case 145 min — CRITICAL"

2. This prediction is IMMEDIATELY saved:
   INSERT INTO predictions (event_id, event_cause, priority, pred_p50, pred_impact...)
   event_id = "ui_a3f9b2c1de"  ← unique ID for this incident

3. Officer dispatches resources (8 officers, 6 barricades)

4. Incident resolves 108 minutes later

5. Officer opens "Record Actual Outcome" on Predictor screen
   → Enters: 108 minutes
   → DB updates: actual_minutes=108, abs_error=|95-108|=13, actual_impact=computed

6. Accuracy report auto-recalculates:
   n_resolved: 686  (one more than before)
   median_abs_error: 28.5 min  (stays within baseline)
   pct_correct_impact: 87.6%
   drift_flag: False

7. If after many incidents medae grows to 62 min (>49.8 × 1.20):
   → drift_flag = True
   → Feedback screen shows red banner: "Retraining Recommended"
   → Supervisor runs: python train_model.py --csv updated_data.csv
   → New pkl files replace old ones
   → App restarts, loop resets with new baseline
```

**What was there before this was built:** Only text in an expandable section saying "feedback loop works like this." No actual storage. No actual logging. No drift detection.

**What's there now:** A fully functional SQLite-backed system wired into Screen 1 and Screen 6.

---

## ❓ What are those markers on the Live Risk Map?

**Every single marker is a real incident from the actual dataset.**

### Exactly where they come from:

1. The dataset has 8,173 real Bengaluru incidents with GPS coordinates
2. The notebook used `train_test_split(X, y, test_size=0.2, random_state=42)`
   → 80% training (2,818 rows after filtering), 20% test (685 rows)
3. `build_map_data.py` reproduces that **exact same split** (`random_state=42`)
4. It runs `model_p50.predict()` and `model_p90.predict()` on all 685 test rows
5. It computes actual duration from `closed_datetime - start_datetime` (ground truth)
6. It samples **40 resolved + 10 active** incidents into `map_incidents.json`

### So every marker has:
- **Real GPS coordinates** — from the `latitude`/`longitude` columns of the actual incident
- **Real predicted clearance** — what model_p50 returned for that incident's features
- **Real actual clearance** — ground-truth duration from the same row's timestamps
- **Real error** — `|pred_p50 - actual_minutes|`

### What "resolved" vs "active" means on the map:
- **Resolved (pin markers)**: 40 test rows where we show both predicted AND actual time
  → Click → see "Predicted: 95 min | Actual: 108 min | Error: 13 min"
  → This validates the model — the numbers are real
- **Active (circle markers)**: 10 test rows where we show forecast only
  → Simulates what a dispatcher sees for a live in-progress incident
  → "Predicted: 85 min — await resolution"

### What was there before:
15 hardcoded rows with coordinates and numbers I made up.
"pred_clearance: 42 min, actual_clearance: 38 min" — those were fictional.

### What's there now:
50 real rows from the actual test set with real model predictions and real ground-truth outcomes.

---

## 📊 Numbers You Can Cite to Judges

From `build_map_data.py` output:
```
Test set: 685 rows
Rows with valid Bengaluru coordinates: 685
Impact distribution (resolved sample): Critical=10, High=10, Low=10, Medium=10
Active incidents: 10

Seeded 685 records into feedback DB
Median absolute error on map data: 28.4 min
Baseline MedAE (from training): 49.8 min
Impact accuracy: 87.7%
Drift flag: False
Status: ✅ Model performing within baseline tolerance
```

---

## 🗂️ Files Added / Changed

| File | What it does |
|------|--------------|
| `feedback_store.py` | SQLite CRUD — log prediction, record actual, compute drift, snapshot |
| `build_map_data.py` | One-time script: runs real test split, generates map_incidents.json + seeds DB |
| `map_incidents.json` | 50 real incidents with real model predictions and real actual outcomes |
| `gridlock_feedback.db` | SQLite database — all predictions, actuals, accuracy snapshots |
| `app.py` | Updated: Screen 1 logs every prediction; Screen 4 loads from JSON; Screen 6 new |

---

## 🎤 How to Explain This to Judges (2 minutes)

**"Most teams say they have a feedback loop. We actually built one."**

Show Screen 6 (Feedback & Retraining):
- "Every prediction is logged here. You can see the exact event features, what the model predicted, and what actually happened."
- "The system computes median absolute error in real-time. Baseline from training is 49.8 min. If it crosses 59.8 min, this banner turns red and tells us to retrain."
- "We seeded this with the 685 real test-set predictions so the chart starts meaningful."

Show Live Risk Map:
- "These aren't fake markers. Every pin is a real GPS coordinate from the dataset. Click any resolved incident — that predicted number came from model_p50.predict(), that actual number came from closed_datetime minus start_datetime. Same row, same model."
- "The 10 circle markers are active — simulating what dispatch sees right now for live incidents."

Show Screen 1 → Record Actual Outcome:
- "When an incident resolves, the officer enters the actual time here. It writes directly to the database, updates the accuracy stats, and if drift builds up, triggers the retrain flag."

**That's a complete, working, honest system. Not promises — running code.**
