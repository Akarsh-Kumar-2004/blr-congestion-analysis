# 🎬 Gridlock — Demo Video Script

**Recommended length:** 3–4 minutes
**Format:** Screen recording + voiceover
**Tone:** Confident, clear, no filler — like a product demo, not a lecture

---

## ⚙️ Before You Hit Record

**Setup checklist:**
- [ ] App running: `streamlit run app.py` → open `http://localhost:8501`
- [ ] Sidebar visible (not collapsed)
- [ ] Browser zoom: 90% (fits more content)
- [ ] Dark desktop background (matches app's dark theme)
- [ ] Screen resolution: 1920×1080 recommended
- [ ] Microphone tested
- [ ] Close notifications / Do Not Disturb mode ON

**Pre-load screens by clicking each once** (so no loading spinners mid-recording):
1. Event Impact Predictor
2. Resource Planner
3. Historical Hotspots
4. Live Risk Map
5. Scenario Simulator
6. Feedback & Retraining

---

## 🎙️ SCRIPT (Spoken Words + Screen Actions)

---

### [INTRO — 0:00–0:20]

> **SAY:**
> "Traffic events — rallies, construction, accidents — cause unpredictable congestion every day in Bengaluru.
> Dispatch teams guess how many officers and barricades to send.
> Wrong guess? Either chaos, or wasted resources.
> Gridlock changes that."

**SCREEN ACTION:**
- Show the app landing on **Screen 1: Event Impact Predictor**
- Let the sidebar be visible so judges see all 6 screen names
- Pause 1 second on the full screen before speaking

---

### [SCREEN 1 — Event Impact Predictor — 0:20–1:00]

> **SAY:**
> "This is our Event Impact Predictor.
> An officer gets a call: vehicle breakdown, High priority, West Zone 1, Tumkur Road, 6 PM.
> Let's see what the model says."

**SCREEN ACTION:**
- Set values in the form:
  - Event Type → `unplanned`
  - Event Cause → `vehicle_breakdown`
  - Priority → `High`
  - Zone → `West Zone 1`
  - Corridor → `Tumkur Road`
  - Hour → `18`
  - Road Closure → ✅ checked
- Click **"Predict Impact"**

> **SAY:**
> "Predicted clearance: 95 minutes typical, 145 worst-case.
> Impact: Critical.
> Confidence: 82%.
> Not a percentage score — an actionable forecast with uncertainty bands."

**SCREEN ACTION:**
- Hover over the p50/p90 metric cards so they're highlighted
- Pause 2 seconds on the result screen

> **SAY:**
> "Every prediction is automatically logged. That matters — I'll show you why in a moment."

---

### [SCREEN 2 — Resource Planner — 1:00–1:25]

> **SAY:**
> "Based on that prediction, here's the deployment plan."

**SCREEN ACTION:**
- Navigate to **Screen 2: Resource Planner** in the sidebar
- The resource table should auto-populate from Screen 1

> **SAY:**
> "10 officers, 8 barricades, 3 tow vehicles, diversion required.
> These aren't arbitrary numbers — they're derived directly from the impact level.
> An officer can read this and act. No guessing."

**SCREEN ACTION:**
- Expand the **"Deployment Rationale"** section briefly
- Let judges see the logic (2 seconds), then move on

---

### [SCREEN 3 — Historical Hotspots — 1:25–1:50]

> **SAY:**
> "The model is trained on 8,173 real Bengaluru traffic incidents from 2023 to 2024.
> These are the patterns it learned."

**SCREEN ACTION:**
- Navigate to **Screen 3: Historical Hotspots**
- Slowly scroll through the charts — don't rush

> **SAY:**
> "Vehicle breakdowns are the most common cause.
> But look at waterlogging — only 98 incidents, but average clearance of 240 minutes.
> That's what the model learns: severity isn't just frequency."

**SCREEN ACTION:**
- Point (hover) over the **"Avg Clearance by Cause"** chart, especially the waterlogging bar

> **SAY:**
> "Evening peak — 6 to 7 PM — has the highest incident density.
> West Zone 2 is the highest risk zone.
> These aren't assumptions — this comes directly from the data."

**SCREEN ACTION:**
- Quickly scroll to the **High Risk Zones** chart, pause on West Zone 2

---

### [SCREEN 5 — Scenario Simulator — 1:50–2:30]

> **SAY:**
> "Here's where Gridlock becomes a decision support tool.
> The Scenario Simulator lets you ask: what if I change one variable?"

**SCREEN ACTION:**
- Navigate to **Screen 5: Scenario Simulator**
- Set base event:
  - Cause → `accident`
  - Priority → `High`
  - Zone → `Central Zone 1`
  - Hour → `18`
  - Road Closure → ✅ Yes
- Choose scenario: **"Toggle Road Closure"**
- Click **"Run Scenario"**

> **SAY:**
> "Same event. Same priority. Same location.
> The only change: road closure — yes versus no.
> Impact drops from Critical to High.
> Clearance time: 145 minutes down to 95 minutes.
> 2 fewer officers needed. Diversion cancelled."

**SCREEN ACTION:**
- Point at (hover) the **Before/After side-by-side cards**
- Let the **Delta table** be visible — especially the "Clearance Time: -50 min" card

> **SAY:**
> "This is the question officers ask in real life: is it worth closing the road?
> Now they have a data-driven answer."

---

### [SCREEN 4 — Live Risk Map — 2:30–3:00]

> **SAY:**
> "The Live Risk Map shows real incidents across Bengaluru.
> Not fake markers — these are 50 incidents from our actual test set,
> with real GPS coordinates and real model predictions."

**SCREEN ACTION:**
- Navigate to **Screen 4: Live Risk Map**
- Let the map load fully before speaking
- Click on a **red (Critical) resolved marker**

> **SAY:**
> "Click any resolved incident and you see: predicted clearance versus actual clearance.
> This one: predicted 142 minutes, actual 158 minutes.
> Error: 16 minutes.
> That's the model being honest — not cherry-picked."

**SCREEN ACTION:**
- Hover over a few more markers briefly
- Toggle **"Show Heatmap"** to show the density overlay
- Turn it off again

> **SAY:**
> "This is how we validate the model in production.
> Predicted versus actual, incident by incident."

---

### [SCREEN 6 — Feedback & Retraining — 3:00–3:40]

> **SAY:**
> "Most hackathon teams say 'we'll add a feedback loop later.'
> We built it."

**SCREEN ACTION:**
- Navigate to **Screen 6: Feedback & Retraining**
- Let the accuracy report card load

> **SAY:**
> "Every prediction made in this app is stored in a local database.
>686 incidents logged. Median absolute error: 28.4 minutes.
> That's well within our baseline of 49.8 minutes from training."

**SCREEN ACTION:**
- Point at (hover) the green drift status banner: **"🟢 Model performing within baseline tolerance"**

> **SAY:**
> "Drift detection is automated.
> If the model's median error exceeds 59.8 minutes — that's a 20% degradation —
> this banner turns red and triggers a retrain recommendation."

**SCREEN ACTION:**
- Scroll down to the **Accuracy Trend Chart**
- Let judges see the baseline and retrain threshold lines

> **SAY:**
> "The trend chart shows accuracy over time.
> Green dashed line: our baseline.
> Red dashed line: retrain threshold.
> Right now we're well below both."

**SCREEN ACTION:**
- Scroll down to show the **Prediction Log table** briefly
- Show a few rows: event_id, event_cause, pred_p50, actual_minutes, abs_error

> **SAY:**
> "And here's the prediction log — every incident, what we forecasted, what actually happened.
> Retraining isn't automatic — a supervisor reviews the drift and approves it.
> That's intentional. In safety-critical systems, you don't retrain blindly."

---

### [CLOSE — 3:40–4:00]

> **SAY:**
> "Gridlock does three things:
> It forecasts. It recommends. And it learns.
> Not as a promise — as a working system, running right now."

**SCREEN ACTION:**
- Navigate back to **Screen 1: Event Impact Predictor**
- Let the full app be visible with sidebar showing all 6 screens

> **SAY:**
> "8,173 real incidents. No data leakage. Honest metrics.
> A feedback loop that gets smarter with every resolved event.
> This is Gridlock."

**SCREEN ACTION:**
- Slowly zoom in slightly on the sidebar showing all 6 screen names
- Fade to black / end recording

---

## 📋 SHOT LIST (At a Glance)

| Time | Screen | What to Show | Talking Point |
|------|--------|--------------|---------------|
| 0:00–0:20 | Screen 1 (idle) | Full app + all 6 screens in sidebar | Problem intro |
| 0:20–1:00 | Screen 1 | Fill form → Predict → p50/p90/Impact result | Real model, confidence bands |
| 1:00–1:25 | Screen 2 | Resource table + expand Rationale | Actionable numbers, not scores |
| 1:25–1:50 | Screen 3 | 4 charts: causes, clearance, peak hours, zones | Real data patterns |
| 1:50–2:30 | Screen 5 | Set base event → Toggle closure → Before/After | Decision support differentiator |
| 2:30–3:00 | Screen 4 | Click resolved marker → pred vs actual popup | Model validated on real data |
| 3:00–3:40 | Screen 6 | Accuracy report → Drift status → Trend chart → Log | Real feedback loop, production thinking |
| 3:40–4:00 | Screen 1 | Full app + sidebar | Closing pitch |

---

## ⚠️ COMMON MISTAKES TO AVOID

- ❌ **Don't say "89% accuracy"** — say "86% impact classification accuracy, median MAE 49.8 min"
- ❌ **Don't say "machine learning magic"** — say what the model does (quantile regression, p50/p90)
- ❌ **Don't rush Screen 6** — this is what makes you different from other teams
- ❌ **Don't forget to click a map marker** — that popup (pred vs actual) is a visual proof point
- ❌ **Don't say "future work"** — say "this is already running"
- ❌ **Don't scroll past charts too fast** — judges need 2–3 seconds to read each one

---

## 💡 OPTIONAL POWER MOVES (If You Have Extra Time)

### Power Move 1: Log a Prediction Live
- On Screen 1, make a new prediction
- Then go to Screen 6 → Prediction log → show the new entry appeared
- Say: *"That prediction I just made? It's already in the database."*

### Power Move 2: Record an Actual Outcome
- On Screen 1, expand **"Record Actual Outcome"**
- Enter actual time (e.g., 108 minutes)
- Navigate to Screen 6 → show log updated with `abs_error`
- Say: *"When the incident resolves, the officer enters the actual time. The system recalculates accuracy instantly."*

### Power Move 3: Change Hour on Scenario Simulator
- Set hour to `5` (off-peak) vs `18` (peak)
- Show how the same event has lower impact at 5 AM vs 6 PM
- Say: *"Same event, different time. The model accounts for peak traffic hours."*

---

## 🎙️ ONE-LINER CHEAT SHEET

Use these when judges ask questions mid-demo:

| Judge Question | Your Line |
|---|---|
| "Is this real data?" | "8,173 real Bengaluru incidents. Every GPS coordinate on that map is from the actual dataset." |
| "Is the feedback loop real?" | "Yes. That's gridlock_feedback.db on disk. You can open it. 686 records in there right now." |
| "Why not automatic retraining?" | "Safety-critical system. Wrong resource count to an incident isn't a recommendation error — it's a public safety risk." |
| "What's your accuracy?" | "86% impact classification. Median clearance error: 49.8 minutes. Those are honest numbers." |
| "What's different from Google Maps?" | "Google Maps tells you there's congestion. We tell you it's coming, how long it'll last, and how many officers to send." |
| "How do you handle uncertainty?" | "We report p50 and p90 — typical and worst case. Not a single number." |

---

## 🕒 TIMING GUIDE

```
0:00 ──── INTRO (20 sec)
  └─ Show app idle. Frame the problem.

0:20 ──── SCREEN 1: PREDICTOR (40 sec)
  └─ Fill form → predict → explain p50/p90/impact

1:00 ──── SCREEN 2: PLANNER (25 sec)
  └─ Resources auto-populated → explain numbers

1:25 ──── SCREEN 3: HOTSPOTS (25 sec)
  └─ Scroll charts → call out waterlogging + peak hours

1:50 ──── SCREEN 5: SCENARIO SIMULATOR (40 sec)  ← DEMO PEAK
  └─ Toggle road closure → Before/After → Delta table

2:30 ──── SCREEN 4: LIVE MAP (30 sec)
  └─ Click resolved marker → pred vs actual popup

3:00 ──── SCREEN 6: FEEDBACK & RETRAINING (40 sec)  ← DIFFERENTIATOR
  └─ Drift status → Trend chart → Prediction log

3:40 ──── CLOSE (20 sec)
  └─ Back to Screen 1, sidebar visible → pitch line

4:00 ──── END
```

---

## 🎬 RECORDING TIPS

- **Use OBS Studio** (free) or **Loom** for screen recording
- **Record in 1080p** — charts and map markers are legible
- **Add cursor highlight** (OBS: add filter, or use PowerToys) so judges can track what you're pointing at
- **Record audio separately** if your mic is poor — clean audio matters more than perfect video
- **Pause slightly after each screen navigation** — give the app 1–2 seconds to fully render before talking
- **One take or edit later** — Loom edits are easy; for OBS, just record clean takes

---

*Good luck. Show them the system, not just the model.* 🚦
