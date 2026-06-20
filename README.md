# Gridlock: Event-Driven Congestion Intelligence

AI-powered decision support for traffic management during planned & unplanned events in Bengaluru.

## ⚡ Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open **http://localhost:8501**

## 🎮 Five Screens

| Screen | Purpose |
|--------|---------|
| **📊 Event Impact Predictor** | Forecast clearance time & severity |
| **🛠️ Resource Planner** | Get officer, barricade, tow vehicle recommendations |
| **🔥 Historical Hotspots** | See patterns from 8,173 real incidents |
| **🗺️ Live Risk Map** | View incidents on map with pred vs actual feedback |
| **🎮 Scenario Simulator** | What-if analysis: flip one variable, see impact |

## 🔬 Model Architecture

- **Target**: Clearance time (minutes) — predicted via LightGBM quantile regression (p50 + p90)
- **Features**: event_type, cause, priority, road_closure, zone, junction, corridor, veh_type, hour, month, weekday
- **Validation**: 86% accuracy on impact classification (no data leakage)
- **Feedback**: Actual outcomes used to retrain quarterly

## 📁 Files

- `app.py` — 5-screen Streamlit frontend
- `model_p50.pkl` — LightGBM quantile model for p50 (typical)
- `model_p90.pkl` — LightGBM quantile model for p90 (worst-case)
- `gridlock-2 (4).ipynb` — Model training & EDA (reference)
- `train_model.py` — Script to retrain models from raw CSV
- `requirements.txt` — Dependencies
- `PROTOTYPE_SUMMARY.md` — Full technical writeup for judges

## 🎯 Key Innovation

**Scenario Simulator** lets officers see trade-offs:
- "If we reopen one lane before peak hour, clearance drops 145 → 85 min"
- "If we pre-deploy before construction, officers needed drop 10 → 6"

This is **decision support**, not just accuracy reporting.

## 📊 Dataset

- **8,173 real Bengaluru traffic incidents** (2023–2024)
- Event type, cause, priority, zone, junction, corridor, vehicle type, timestamps
- Clearance times: median 72 min, range 0.03–2,051 min (heavy-tailed)
- Used via Kaggle Astram dataset (anonymized)

## 🚀 Deployment Ready

- ✅ Models cached in memory (instant predictions)
- ✅ All UI components are responsive & dark-themed
- ✅ Filter/controls on every screen
- ✅ Explanatory tooltips & expandable sections
- ✅ Post-event learning loop designed (feedback log structure included)

## 📝 For Judges

See **PROTOTYPE_SUMMARY.md** for:
- Full system architecture
- Why no data leakage matters
- How scenario simulator wins hackathons
- Post-launch roadmap

---

**Built for**: Hackathon - Event-Driven Congestion Challenge  
**Status**: Demo-ready, production roadmap included  
**Contact**: Check with your team lead
