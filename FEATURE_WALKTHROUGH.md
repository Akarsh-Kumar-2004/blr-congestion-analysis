# Gridlock Feature Walkthrough

## 🎮 Screen-by-Screen Breakdown

---

## Screen 1: 📊 Event Impact Predictor

### Subtitle
> "Forecasts clearance time and recommends resource deployment based on real-time event data and LightGBM quantile models trained on 8,173 Bengaluru traffic incidents."

### What Happens
1. **User fills form**:
   - Event Type: `unplanned` or `planned`
   - Event Cause: `vehicle_breakdown`, `accident`, `construction`, `waterlogging`, `tree_fall`, etc.
   - Priority: `Low`, `Medium`, `High`
   - Location: Zone, Corridor, Junction dropdowns (real Bengaluru geography)
   - Time: Hour (0–23), Month (1–12), Day of Week
   - Vehicle: Type + Road Closure flag

2. **App runs inference**:
   - Loads `model_p50.pkl` and `model_p90.pkl`
   - Builds feature row with all inputs
   - Predicts clearance time in minutes (p50 + p90)
   - Computes impact (Low/Medium/High/Critical) using formula:
     ```
     impact_score = priority_num + closure_num + duration_bucket
     ```

3. **Results show**:
   - 🔵 Typical Clearance: `42 min` (p50)
   - 🟠 Worst-Case: `95 min` (p90)
   - 🎖️ Impact Badge: **CRITICAL** (color-coded)
   - 🎯 Model Confidence: `82%` (narrow p50/p90 range = high confidence)
   - **Confidence progress bar**
   - 💡 Interpretation line explaining what this impact means

4. **Data persists** in session state → passed to Screen 2 automatically

---

## Screen 2: 🛠️ Resource Planner

### Subtitle
> "AI-recommended deployment plan based on predicted impact."

### What Happens
1. **Auto-loads prediction** from Screen 1 (no re-entry)
   - Or manual selection if coming cold to this screen

2. **Shows deployment table**:
   - 👮 Officers Required: `8` (for High impact)
   - 🚧 Barricades Required: `6`
   - 🚗 Tow Vehicles: `2`
   - 🔀 Diversion Required: `YES` (if road closure + impact ≥ High)

3. **Expandable "Deployment Rationale"**:
   ```
   High impact = 8 officers (multi-point traffic regulation)
                 6 barricades (full lane management)
                 2 tow vehicles (rapid clearance)
                 Diversion plan activates
   ```

4. **Expandable "Response Timeline"**:
   ```
   0–5 min:    Dispatch 8 officers + 2 tow vehicles
   0–10 min:   Deploy 6 barricades across corridor
   10–30 min:  Activate diversion if road closure confirmed
   30–90 min:  Active multi-point traffic management
   90–180 min: Expected clearance
   ```

5. **Reset button** to clear and go back to Predictor

---

## Screen 3: 🔥 Historical Hotspots

### Subtitle
> "Patterns extracted from 8,173 real Bengaluru traffic events (2023–2024)."

### What Happens
1. **Top Event Causes** (bar chart):
   - vehicle_breakdown: 2,841 incidents
   - others: 2,127
   - construction: 480
   - accident: 365
   - waterlogging: 98
   - tree_fall: 74
   - congestion: 136
   - pothole: 52

2. **Avg Clearance by Cause** (bar chart):
   - Waterlogging: 240 min (requires pumping units)
   - Construction: 195 min
   - Tree Fall: 160 min
   - Accident: 135 min
   - Congestion: 110 min
   - Vehicle Breakdown: 75 min
   - Pothole: 55 min

3. **Peak Incident Hours** (24-hour bar chart):
   - Peaks at 5–8 AM (morning rush, 310–620 incidents across hours)
   - Peaks at 5–8 PM (evening rush, 490–690 incidents)
   - Lowest at 2–4 AM (95–140 incidents)
   - Annotated with emoji callouts ("🌅 Morning Peak", "🌆 Evening Peak")

4. **High Risk Zones** (horizontal bar chart):
   - West Zone 2: 2.648 priority score
   - North Zone 1: 2.591
   - North Zone 2: 2.584
   - Central Zone 1: 2.517
   - South Zone 2: 2.497
   - West Zone 1: 2.259
   - East Zone 1: 2.209
   - Central Zone 2: 2.075 (lowest risk)

5. **Most Incident-Prone Junctions** (top 10):
   - Lalbagh Main Gate: 312 incidents
   - Urvashi Junction: 287
   - Hebbal Flyover: 241
   - Silk Board: 228
   - KR Puram: 196
   - ... etc

6. **3 Insight Cards**:
   - 🚨 Highest Risk Period: 5 PM–8 PM (38% of incidents)
   - ⚠️ Highest Risk Zone: West Zone 2
   - 🕐 Longest Clearance: Waterlogging — 240 min

---

## Screen 4: 🗺️ Live Risk Map

### Subtitle
> "Predicted impact & resource needs for real incidents across Bengaluru. Each marker shows what the model forecasts (clearance time, officers, barricades) for an incident in progress — color-coded by predicted severity."

### What Happens
1. **Folium Map Loads**:
   - Centered on Bengaluru (12.972°N, 77.594°E)
   - Dark theme (CartoDB dark_matter tiles)
   - 15 real-coordinate incidents marked

2. **Filter Controls**:
   - **By Impact**: Multiselect (Low/Medium/High/Critical)
   - **By Cause**: Multiselect (vehicle_breakdown, accident, construction, etc.)
   - **Heatmap**: Optional toggle for density visualization

3. **Legend Row**:
   - 🟢 Low (green icon, info-sign)
   - 🟡 Medium (orange icon, warning-sign)
   - 🟠 High (orange icon, fire)
   - 🔴 Critical (red icon, remove/X)

4. **Interactive Markers**:
   - Click to see popup:
     ```
     ● CRITICAL Impact
     Cause: Accident
     Zone: Central Zone 1
     Corridor: Bellary Road
     Priority: High
     ─────────────────────
     🔮 Predicted Clearance: 142 min
     ✓ Actual Clearance: 158 min
     Status: RESOLVED
     ```
   - Hover for tooltip: "Critical — Accident"
   - Color-coded icon matches impact level

5. **Optional Heatmap Overlay**:
   - Shows incident density across the city
   - Radius 25px, blur 20px, opacity 0.4–1.0 based on severity

6. **Stats Row**:
   - Total Incidents: `15` (based on filters)
   - Critical Count: `3`
   - High Count: `5`
   - Avg Risk: `2.4/4`

7. **ℹ️ "How This Map Works" Expandable**:
   - Explains what "live" means (predicted vs actual from resolved incidents)
   - Why it matters (validates model, shows post-event learning)
   - In production (live API feed, dispatch action logging)

---

## Screen 5: 🎮 Scenario Simulator

### Subtitle
> "Tweak a single variable and instantly see how the impact and resource plan changes. This is your decision support tool."

### What Happens
1. **Base Event Configuration**:
   - Event Cause, Priority (form fields)
   - Zone, Corridor (dropdowns)
   - Hour, Weekday (sliders/selects)
   - Road Closure flag (checkbox)

2. **Choose Scenario Type** (radio buttons):
   - 🚧 Toggle Road Closure
   - ⬆️ Change Priority
   - ⏰ Change Hour
   - 🔄 Change Event Cause

3. **Example: Toggle Road Closure**
   - User selects "Road Closure: Yes → No"
   - App runs TWO predictions in parallel

4. **Side-by-Side Results**:
   
   **BEFORE**                      **AFTER**
   ```
   ● CRITICAL Impact              ● HIGH Impact
   📍 145–180 min                 📍 95–120 min
   👮 10 officers                 👮 8 officers
   🚧 8 barricades                🚧 6 barricades
   🚗 3 tow                       🚗 2 tow
   🔀 YES                         🔀 NO
   ```

5. **Delta Table** (4 cards):
   - Clearance Time: `-50 min` (green, improved)
   - Officers: `-2` (green)
   - Barricades: `-2` (green)
   - Tow Vehicles: `-1` (green)

6. **Insight Callout**:
   - ✅ Green: "This change **reduces** impact from **Critical** to **High** and saves **50 minutes**. Fewer resources needed."
   - ⚠️ Red (if worsens): "This change **worsens** impact… Deploy more resources."
   - ↔️ Neutral: "This change has **no significant impact**."

---

## 🎯 Why Each Screen Matters for Judges

| Screen | Judge Question | Answer |
|--------|---|---|
| **Predictor** | "Does the model work?" | ✅ Real predictions with confidence bands |
| **Planner** | "Is it actionable?" | ✅ Specific resource numbers, not abstract scores |
| **Hotspots** | "Is the data real?" | ✅ 8,173 actual incidents, real patterns |
| **Live Map** | "How do you learn?" | ✅ Pred vs actual feedback loop visible |
| **Scenario** | "Why are you different?" | ✅ Decision support, not just accuracy |

---

## 🔌 Technical Behind the Scenes

### Model Loading
```python
with open("model_p50.pkl", "rb") as f:
    model_p50 = pickle.load(f)
with open("model_p90.pkl", "rb") as f:
    model_p90 = pickle.load(f)
```

### Inference
```python
row = pd.DataFrame([event]).reindex(columns=FEATURE_COLS)
p50 = np.expm1(model_p50.predict(row))[0]  # Un-log the prediction
p90 = np.expm1(model_p90.predict(row))[0]
```

### Impact Formula
```python
priority_num = {"Low": 1, "Medium": 2, "High": 3}.get(priority, 2)
closure_num = 2 if road_closure else 0
duration_bucket = 1 if p50 <= 30 else (2 if p50 <= 120 else 3)
score = priority_num + closure_num + duration_bucket
impact = ["Low", "Medium", "High", "Critical"][min(score-1, 3)]
```

### Resource Mapping
```python
res = {
    "officers":      {1:2, 2:4, 3:8, 4:10}[impact_index],
    "barricades":    {1:1, 2:3, 3:6, 4:8}[impact_index],
    "tow_vehicles":  {1:0, 2:1, 3:2, 4:3}[impact_index],
    "diversion":     road_closure and impact in ("High", "Critical")
}
```

---

## 📱 User Flows

### Flow 1: Quick Prediction
```
Predictor → [fill form] → [click "Predict Impact"]
         → [see results]
         → [optional: go to Planner]
```

### Flow 2: Deep Analysis
```
Hotspots → [see patterns]
        → [understand risks]
        → Predictor → [set up similar event]
                   → [see forecast]
```

### Flow 3: Decision Support (Officer)
```
Scenario Sim → [set base event]
           → [toggle closure: Yes→No]
           → [see: impact Critical→High, clearance 180→120 min]
           → [decide: close road? or handle with 8 officers?]
```

### Flow 4: Validation (Manager)
```
Live Map → [click incidents]
        → [see pred vs actual popup]
        → [assess model accuracy]
        → [confirm deployment data]
```

---

## ✨ Polish Details

- ✅ All forms have **sensible defaults** (Hour=18, Month=6, Day=Friday, Priority=High)
- ✅ Multiselect filters **default to all options** (not "none selected")
- ✅ Confidence progress bar shows **p50/p90 ratio interpretation**
- ✅ All numeric outputs **rounded/formatted** (no 45.23849381 clutter)
- ✅ Color scheme is **dark theme** (easier on eyes in hackathon room)
- ✅ Icons + emojis **consistent** throughout (officers=👮, barricades=🚧, etc.)
- ✅ Expandable sections **preserve state** (don't collapse on rerun)
- ✅ Sidebar **shows ✅ ML Models Loaded** (not ⚠️ Rule-based mode)

---

Done! 🎉 Your judges will see a **professional, thoughtful, actionable system**—not just a model.
