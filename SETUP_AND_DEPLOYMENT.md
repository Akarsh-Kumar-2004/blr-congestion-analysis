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

### Step 4: Launch App
```bash
streamlit run app.py
```

**Output:**
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
  Network URL: http://192.168.0.4:8501
```

### Step 5: Open in Browser
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
   - [ ] 15 colored markers visible
   - [ ] Click marker → popup shows pred/actual
   - [ ] Filter by impact/cause works
   - [ ] Heatmap toggle works
   - [ ] Stats row updates based on filters

5. **Scenario Simulator**
   - [ ] Form fills with defaults
   - [ ] Select scenario type (radio)
   - [ ] Run simulation
   - [ ] Before/After cards show
   - [ ] Delta table shows changes
   - [ ] Insight callout appears (green/red/neutral)

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

## 🔄 Retraining Pipeline

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

### Models Not Loading
```
FileNotFoundError: model_p50.pkl not found
```
**Solution**: Check both pkl files exist in the same directory as `app.py`
```bash
ls -la model_*.pkl
```

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
