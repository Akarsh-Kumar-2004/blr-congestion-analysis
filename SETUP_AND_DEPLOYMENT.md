# Setup & Deployment Guide

## 🚀 Local Development Setup

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- ~100 MB disk space (for models + dependencies)

### Step 1: Clone/Download Project
```bash
cd /path/to/gridlock
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

**What gets installed:**
- `streamlit` 1.41+ — frontend framework
- `lightgbm` 4.0+ — ML inference
- `scikit-learn` — model utilities
- `pandas`, `numpy` — data handling
- `folium` — geospatial maps
- `streamlit-folium` — map embedding
- `plotly` — interactive charts

**Total download**: ~150 MB

### Step 3: Verify Models Exist
```bash
ls -la model_p50.pkl model_p90.pkl
```

Both should be ~6–7 MB each (total ~12 MB).

### Step 4: Initialize Feedback Database (One-Time Setup)
```bash
# This seeds the database with 685 test-set predictions
python build_map_data.py
```

**What this does:**
- Creates `gridlock_feedback.db` (SQLite) with schema:
  - `predictions` table: event details, forecasts, actual outcomes, errors
  - `accuracy_snapshots` table: historical accuracy metrics
- Seeds 685 real test-set predictions (with real model predictions + actual clearance times)
- Generates `map_incidents.json` (50 real map markers with GPS + pred/actual)
- Prints accuracy report:
  ```
  ✅ Database initialized
  Test set: 685 rows
  Median absolute error: 28.4 min
  Baseline threshold: 49.8 min (original training)
  Status: Model performing within tolerance
  ```

### Step 5: Launch App
```bash
streamlit run app.py
```

**Output:**
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
  Network URL: http://192.168.0.4:8501
```

### Step 6: Open in Browser
Click the URL or manually navigate to `http://localhost:8501`

---

## 🧪 Testing Locally

### Test Each Screen
1. **Event Impact Predictor**
   - [ ] Load page (no errors)
   - [ ] Fill form with sample values
   - [ ] Click "Predict Impact"
   - [ ] Results appear in <2 seconds
   - [ ] Confidence % shows (should be 55–95%)
   - [ ] Expandable "Record Actual Outcome" works
   - [ ] Submit actual time → DB updates

2. **Resource Planner**
   - [ ] Sidebar nav to "Resource Planner"
   - [ ] Data auto-populated from prediction
   - [ ] Table shows officers/barricades/tow/diversion
   - [ ] Expandable sections work
   - [ ] "New Prediction" button resets

3. **Historical Hotspots**
   - [ ] 5 Plotly charts load (may take 2–3 sec)
   - [ ] Hover over charts shows tooltips
   - [ ] 3 insight cards appear
   - [ ] Charts are interactive (zoom, pan)

4. **Live Risk Map**
   - [ ] Folium map renders (may take 3–5 sec)
   - [ ] 50 colored markers visible (from map_incidents.json)
   - [ ] Click marker → popup shows pred/actual
   - [ ] Filter by impact/cause works
   - [ ] Heatmap toggle works
   - [ ] Stats row updates based on filters
   - [ ] Expandable section explains real data provenance

5. **Scenario Simulator**
   - [ ] Form fills with defaults
   - [ ] Select scenario type (radio)
   - [ ] Run simulation
   - [ ] Before/After cards show
   - [ ] Delta table shows changes
   - [ ] Insight callout appears (green/red/neutral)

6. **Feedback & Retraining** (NEW)
   - [ ] Accuracy report loads: n_resolved, median_mae, pct_correct_impact
   - [ ] Drift detection working (banner: 🟢 GREEN or 🔴 RED)
   - [ ] Accuracy trend chart renders
   - [ ] Prediction log table shows recent predictions
   - [ ] Expandable sections load
   - [ ] Retrain command is shown
   - [ ] Add a prediction on Screen 1, then come back → log updates

---

## 🌐 Deployment to Cloud

### Option A: Streamlit Cloud (Easiest)

1. **Push to GitHub**
```bash
git add .
git commit -m "Gridlock prototype ready for deployment"
git push origin main
```

2. **Deploy via Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Select your GitHub repo, branch `main`, file `app.py`
   - Streamlit automatically installs dependencies from `requirements.txt`
   - App is live in ~2 minutes

3. **Share link** (public by default, anyone can access)

### Option B: AWS EC2 (Production)

1. **Launch Ubuntu 22.04 instance**
```bash
# SSH into instance
ssh -i key.pem ubuntu@<instance-ip>

# Install Python & pip
sudo apt update
sudo apt install python3.10 python3-pip

# Clone repo
git clone <your-repo>
cd gridlock
pip install -r requirements.txt
```

2. **Run as service** (systemd)
```bash
# Create service file
sudo nano /etc/systemd/system/gridlock.service

[Unit]
Description=Gridlock Streamlit App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/gridlock
ExecStart=/usr/bin/python3 -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target

# Enable & start
sudo systemctl enable gridlock
sudo systemctl start gridlock
```

3. **Access via `http://<instance-ip>:8501`**

### Option C: Docker (Portable)

1. **Create Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

2. **Build & Run**
```bash
docker build -t gridlock:latest .
docker run -p 8501:8501 gridlock:latest
```

3. **Deploy to Docker Hub, ECR, or any container registry**

---

## 📋 Production Checklist

- [ ] Models load without errors
- [ ] All 5 screens responsive
- [ ] No console errors in browser dev tools
- [ ] Filters/controls work on all screens
- [ ] API integration planned (for live incident feed)
- [ ] Database schema designed (PostgreSQL for feedback log)
- [ ] User authentication plan (officers, managers, admins)
- [ ] SSL/HTTPS configured (if public)
- [ ] Monitoring setup (alert on model inference errors)
- [ ] Feedback collection scheduled (weekly/monthly)
- [ ] Retraining pipeline automated (quarterly)

---

## 🔄 Feedback Loop & Retraining

### How the Real Feedback Loop Works

**This is NOT simulated. It's a fully operational system.**

1. **Officer uses Predictor** (Screen 1)
   - Fills: event_type, event_cause, priority, zone, hour, etc.
   - App runs `model_p50.predict()` + `model_p90.predict()`
   - Shows: "Predicted clearance: 95 min (p50) | 145 min (p90) | Impact: CRITICAL"

2. **Prediction Logged Immediately**
   - Saved to `gridlock_feedback.db` (SQLite):
     ```sql
     INSERT INTO predictions (event_id, event_cause, priority, pred_p50, pred_p90, pred_impact, created_at)
     VALUES ("ui_a3f9b2c1de", "vehicle_breakdown", "High", 95, 145, "CRITICAL", now())
     ```

3. **Officer Records Actual Outcome** (Expandable on Screen 1)
   - When incident resolves, officer enters: "Actual clearance: 108 minutes"
   - DB updates:
     ```sql
     UPDATE predictions SET actual_minutes=108, abs_error=13, actual_impact="CRITICAL", resolved_at=now()
     WHERE event_id="ui_a3f9b2c1de"
     ```

4. **Accuracy Auto-Recalculates** (Screen 6)
   - On every page load of Feedback & Retraining:
     ```python
     n_resolved = count(resolved predictions)
     median_mae = percentile(abs_error, 50)
     pct_correct_impact = count(correct impacts) / n_resolved
     drift_flag = median_mae > baseline_mae * 1.20  # baseline = 49.8 min
     ```

5. **Drift Detection**
   - If `median_mae > 59.8 min` (baseline × 1.20):
     - 🔴 RED banner: "Accuracy degraded. Retraining recommended."
     - Command displayed: `python train_model.py --csv augmented_data.csv`

6. **Retraining (Manual, Not Automatic)**
   - Supervisor reviews drift report
   - Exports resolved incidents to CSV
   - Runs: `python train_model.py --csv updated_data.csv --output model_p50_v2.pkl model_p90_v2.pkl`
   - Validates new models (better accuracy? deploy : keep current)
   - Replaces pkl files and restarts app

### Schema of Feedback Database

**`gridlock_feedback.db`** has two tables:

**Table: predictions**
```sql
CREATE TABLE predictions (
  id INTEGER PRIMARY KEY,
  event_id TEXT UNIQUE,           -- UUID for this incident
  created_at TIMESTAMP,            -- When prediction was made
  
  -- Feature values (what was reported)
  event_type TEXT,
  event_cause TEXT,
  priority TEXT,
  road_closure INTEGER,
  zone TEXT,
  corridor TEXT,
  hour INTEGER,
  month INTEGER,
  weekday TEXT,
  
  -- Model outputs (forecast)
  pred_p50 REAL,                  -- Predicted p50 clearance (minutes)
  pred_p90 REAL,                  -- Predicted p90 clearance (minutes)
  pred_impact TEXT,               -- Predicted impact (Low/Med/High/Critical)
  
  -- Ground truth (filled when resolved)
  actual_minutes REAL,
  actual_impact TEXT,
  resolved_at TIMESTAMP,
  
  -- Computed
  abs_error REAL                  -- |pred_p50 - actual_minutes|
);
```

**Table: accuracy_snapshots**
```sql
CREATE TABLE accuracy_snapshots (
  id INTEGER PRIMARY KEY,
  snapshot_at TIMESTAMP,
  n_resolved INTEGER,             -- Count of resolved incidents at this time
  median_abs_error REAL,          -- Median absolute error in minutes
  pct_correct_impact REAL,        -- % of correct impact predictions
  retrain_triggered INTEGER       -- 1 if drift flag was set, 0 otherwise
);
```

### When to Retrain

- **Trigger**: Drift detected (`median_mae > 59.8 min`)
- **Frequency**: Typically quarterly (when 50+ resolved incidents accumulate)
- **Who decides**: Supervisor/Manager (not automatic, for safety)
- **Process**: Export DB → augment training CSV → retrain → validate → deploy

### What Was Different Before

- **Before**: Expandable text saying "feedback loop works like this"
- **After**: Fully operational SQLite database + UI showing live metrics + drift flags

---

## 🔄 Retraining Pipeline (Detail)

### When to Retrain
- **Frequency**: Quarterly (every 3 months)
- **Trigger**: When median absolute error exceeds 65 min (vs current 49.8 min)
- **Data**: All resolved incidents + feedback log

### How to Retrain
1. **Collect feedback**
```python
# From your incident tracking system
query = """
SELECT event_id, event_type, event_cause, priority, zone, 
       hour, month, weekday, predicted_clearance_p50,
       actual_clearance_time
FROM incidents
WHERE resolved_datetime IS NOT NULL
  AND created_date > '2025-01-01'
"""
feedback_df = pd.read_sql(query, db)
```

2. **Run training script**
```bash
python train_model.py --csv feedback_df.csv --output model_p50_v2.pkl model_p90_v2.pkl
```

3. **Validate new models**
   - Compare accuracy vs old models
   - If improvement > 2%, promote to production
   - If worse, investigate (data drift? new event types?)

4. **Deploy new models**
```bash
cp model_p50.pkl model_p50_backup.pkl
cp model_p50_v2.pkl model_p50.pkl
# App auto-reloads on restart
systemctl restart gridlock
```

---

## 🐛 Troubleshooting

### Database Errors
```
sqlite3.OperationalError: no such table: predictions
```
**Solution**: You skipped the `build_map_data.py` initialization step. Run:
```bash
python build_map_data.py
```
This creates the schema and seeds 685 test-set predictions.

### Map Markers Not Loading
```
50 markers not showing on Live Risk Map
```
**Solution**: Check that `map_incidents.json` exists:
```bash
ls -la map_incidents.json
```
Should be ~50 KB. If missing, run `build_map_data.py` again.

### Screen 6 Feedback Shows No Data
```
Prediction log is empty on Feedback & Retraining
```
**Solution**: 
- First time? Run `build_map_data.py` to seed 685 test-set predictions
- Then make a prediction on Screen 1 → it will appear in the log
- The log shows 100 most recent; seed data is from test set (older)

### Slow Predictions
```
Takes >5 seconds to show results
```
**Solution**: 
- Models are cached after first load; 2nd+ predictions should be instant
- If still slow, check CPU usage (LightGBM uses all cores by default)
- Reduce `n_jobs` parameter in `train_model.py` if needed

### Map Not Rendering
```
Folium map is blank
```
**Solution**:
- Check browser console for JavaScript errors
- Ensure `streamlit-folium` is installed: `pip install streamlit-folium`
- Try clearing browser cache (Ctrl+Shift+Delete)

### Charts Missing Data
```
Plotly charts show empty axes
```
**Solution**:
- Data is hardcoded; check SAMPLE_INCIDENTS and TOP_CAUSES dictionaries
- Verify Plotly is installed: `pip install plotly`

### Out of Memory (Large Data)
```
MemoryError when loading test data
```
**Solution** (for production):
- Stream incidents instead of loading all at once
- Implement pagination on the map (load 50 incidents at a time)
- Use DuckDB for efficient local querying

---

## 📞 Support & Monitoring

### Health Check Endpoint (Optional Addition)
```python
# Add to app.py for production
@st.cache_data
def health_check():
    try:
        test_event = {
            "event_type": "unplanned",
            "event_cause": "vehicle_breakdown",
            "priority": "High",
            "requires_road_closure": False,
            "zone": "Central Zone 1",
            "junction": None,
            "corridor": "Tumkur Road",
            "veh_type": None,
            "hour": 18,
            "month": 6,
            "weekday": "Friday",
        }
        p50, p90, impact = run_inference(test_event)
        return {"status": "OK", "p50": p50, "p90": p90}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

if st.secrets.get("ENABLE_HEALTH_CHECK"):
    response = health_check()
    if response["status"] != "OK":
        st.error(f"Model Error: {response['message']}")
```

### Logs
```bash
# View Streamlit logs
tail -f ~/.streamlit/logs/

# Or if running as systemd service
journalctl -u gridlock -f
```

---

## 🚀 Launch Checklist for Hackathon

**One Hour Before Demo:**
- [ ] App loads without errors
- [ ] All 5 screens render
- [ ] Models load (✅ in sidebar)
- [ ] Internet is stable (or disable map overlay)
- [ ] Test a full prediction flow
- [ ] Scenario Simulator runs fast
- [ ] Share link ready (if cloud deployment)

**Demo Order:**
1. Show Predictor (input → output)
2. Show Scenario Sim (the wow moment)
3. Show Live Map (validation)
4. Show Hotspots (data story)
5. Show Planner (resource recommendation)

**Backup Plan:**
- Keep README.md, JUDGES_SCORECARD.md printed
- Have demo video pre-recorded (in case of WiFi failure)
- Know how to explain each screen in 30 seconds

---

Done! You're ready to deploy. 🎉

Questions? Check `JUDGES_SCORECARD.md` for common Q&A.
