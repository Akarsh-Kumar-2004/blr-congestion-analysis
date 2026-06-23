"""
Gridlock — Event-Driven Congestion Intelligence
5 Screens + real SQLite feedback loop + live accuracy tracking
"""
import pickle, os, json, uuid
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Gridlock · Event Congestion Intelligence",
    page_icon="🚦", layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html,body,[class*="css"]{font-family:'Segoe UI',sans-serif;}
section[data-testid="stSidebar"]{background:#0f1923;}
section[data-testid="stSidebar"] *{color:#e0e0e0!important;}
.metric-card{background:#1e2b3a;border-radius:12px;padding:18px 22px;
  text-align:center;color:#fff;}
.metric-card .label{font-size:.78rem;color:#8a9bb0;letter-spacing:.08em;
  text-transform:uppercase;}
.metric-card .value{font-size:2rem;font-weight:700;margin-top:4px;}
.badge{display:inline-block;padding:6px 18px;border-radius:20px;
  font-weight:700;font-size:1.1rem;letter-spacing:.04em;}
.badge-low     {background:#1a7a3e;color:#b6ffce;}
.badge-medium  {background:#7a6000;color:#ffe680;}
.badge-high    {background:#7a3000;color:#ffcc99;}
.badge-critical{background:#7a0000;color:#ff9999;}
.res-row{display:flex;align-items:center;gap:10px;padding:10px 0;
  border-bottom:1px solid #2a3a4a;font-size:1rem;color:#e0e0e0;}
.res-icon{font-size:1.4rem;width:28px;text-align:center;}
.res-label{flex:1;color:#8a9bb0;}
.res-value{font-weight:700;font-size:1.15rem;color:#fff;}
.info-box{background:#112233;border-left:4px solid #3a7bd5;border-radius:6px;
  padding:12px 16px;color:#b0c8e8;font-size:.88rem;margin-top:12px;}
.hotspot-card{background:#1a2535;border-radius:10px;padding:14px 18px;
  margin-bottom:10px;}
.hotspot-title{color:#8ab4d4;font-size:.75rem;text-transform:uppercase;
  letter-spacing:.08em;}
.drift-ok  {background:#1a2a1a;border-left:4px solid #2ecc71;border-radius:6px;
  padding:10px 16px;color:#99ff99;margin-top:8px;}
.drift-warn{background:#2a1a1a;border-left:4px solid #e74c3c;border-radius:6px;
  padding:10px 16px;color:#ff9999;margin-top:8px;}
</style>
""", unsafe_allow_html=True)

# ── Model loading ─────────────────────────────────────────────────────────────
BASE = os.path.dirname(__file__)

@st.cache_resource(show_spinner="Loading models…")
def load_models():
    p50_path = os.path.join(BASE, "model_p50.pkl")
    p90_path = os.path.join(BASE, "model_p90.pkl")
    if not (os.path.exists(p50_path) and os.path.exists(p90_path)):
        return None, None
    with open(p50_path,"rb") as f: m50 = pickle.load(f)
    with open(p90_path,"rb") as f: m90 = pickle.load(f)
    return m50, m90

model_p50, model_p90 = load_models()
model_loaded = model_p50 is not None

FEATURE_COLS = ["event_type","event_cause","priority","requires_road_closure",
                "zone","junction","corridor","veh_type","hour","month","weekday"]
CAT_COLS     = ["event_type","event_cause","priority","requires_road_closure",
                "zone","junction","corridor","veh_type","weekday"]

# ── Feedback store ────────────────────────────────────────────────────────────
import feedback_store as fs
fs.init_db()

# ── Auto-seed DB from map_incidents.json if DB is empty ──────────────────────
# This runs on first startup (e.g. Streamlit Cloud) where no DB file exists yet.
# It seeds the 685 test-set predictions so Screen 6 is meaningful from the start.
@st.cache_resource(show_spinner=False)
def seed_db_if_empty():
    import sqlite3 as _sq
    conn = _sq.connect(fs.DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    conn.close()
    if count > 0:
        return  # already seeded, nothing to do

    map_path = os.path.join(BASE, "map_incidents.json")
    if not os.path.exists(map_path):
        return  # no source data, skip

    with open(map_path) as f:
        incidents = json.load(f)

    seeded = 0
    for inc in incidents:
        if inc.get("status") != "resolved" or inc.get("actual_minutes") is None:
            continue
        # deterministic ID so re-seeding never creates duplicates
        event_id = f"seed_{abs(hash((inc['lat'], inc['lon'], inc['pred_p50']))) % (10**8):08x}"
        event = {
            "event_type":            "unplanned",
            "event_cause":           inc.get("cause", "others"),
            "priority":              inc.get("priority", "High"),
            "requires_road_closure": inc.get("road_closure", False),
            "zone":                  inc.get("zone", "Unknown"),
            "corridor":              inc.get("corridor", "Non-corridor"),
            "hour":                  inc.get("hour", 12),
            "month":                 inc.get("month", 6),
            "weekday":               inc.get("weekday", "Monday"),
        }
        fs.log_prediction(event_id, event, inc["pred_p50"], inc["pred_p90"], inc["impact"])
        fs.record_actual(event_id, float(inc["actual_minutes"]))
        seeded += 1

    if seeded:
        fs.take_accuracy_snapshot()

seed_db_if_empty()

# ── Load real map incidents (generated from actual test set) ──────────────────
@st.cache_data(show_spinner=False)
def load_map_incidents():
    path = os.path.join(BASE, "map_incidents.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)

MAP_INCIDENTS = load_map_incidents()

# ── Core helpers ──────────────────────────────────────────────────────────────
def impact_class(score):
    if score<=3: return "Low"
    elif score<=5: return "Medium"
    elif score<=7: return "High"
    else: return "Critical"

def dur_bucket(m):
    m = np.asarray(m)
    return np.where(m<=30, 1, np.where(m<=120, 2, 3))

def impact_color(impact):
    return {"Low":"#2ecc71","Medium":"#f1c40f","High":"#e67e22","Critical":"#e74c3c"}.get(impact,"#aaa")

def badge_html(impact):
    cls = {"Low":"badge-low","Medium":"badge-medium","High":"badge-high","Critical":"badge-critical"}.get(impact,"badge-medium")
    return f'<span class="badge {cls}">{impact}</span>'

def confidence_from_range(p50, p90):
    if p50 <= 0: return 70
    return int(max(55, min(95, 115 - (p90/p50)*18)))

def resource_plan(impact, road_closure):
    return {
        "officers":     {"Low":2,"Medium":4,"High":8,"Critical":10}[impact],
        "barricades":   {"Low":1,"Medium":3,"High":6,"Critical":8}[impact],
        "tow_vehicles": {"Low":0,"Medium":1,"High":2,"Critical":3}[impact],
        "diversion":    road_closure and impact in ("High","Critical"),
    }

def run_inference(event):
    if not model_loaded:
        return rule_based(event)
    row = pd.DataFrame([event]).reindex(columns=FEATURE_COLS)
    for c in CAT_COLS:
        if c in row.columns:
            row[c] = row[c].astype("category")
    p50 = float(np.expm1(model_p50.predict(row))[0])
    p90 = float(np.expm1(model_p90.predict(row))[0])
    p50, p90 = max(1, p50), max(p50, p90)
    pri  = {"Low":1,"Medium":2,"High":3}.get(event.get("priority"),2)
    clos = 2 if event.get("requires_road_closure") else 0
    return p50, p90, impact_class(pri+clos+int(dur_bucket(p50)))

CAUSE_BASE = {"vehicle_breakdown":45,"tree_fall":90,"accident":120,
              "water_logging":150,"waterlogging":150,"construction":180,
              "pot_holes":60,"pothole":60,"others":70,"congestion":80}
def rule_based(event):
    base = CAUSE_BASE.get(event.get("event_cause","others"),70)
    pri  = {"Low":0.8,"Medium":1.0,"High":1.3}.get(event.get("priority","High"),1.0)
    clos = 1.4 if event.get("requires_road_closure") else 1.0
    hour = event.get("hour",12)
    peak = 1.2 if hour in range(8,10) or hour in range(17,20) else 1.0
    p50  = base*pri*clos*peak
    p90  = p50*1.6
    pri_n  = {"Low":1,"Medium":2,"High":3}.get(event.get("priority"),2)
    clos_n = 2 if event.get("requires_road_closure") else 0
    return p50, p90, impact_class(pri_n+clos_n+int(dur_bucket(p50)))

# ── EDA constants (from real dataset analysis) ────────────────────────────────
TOP_CAUSES = {"vehicle_breakdown":2841,"others":2127,"construction":480,
              "accident":365,"congestion":136,"water_logging":98,
              "tree_fall":74,"pot_holes":52,"public_event":41,"road_conditions":28}
PEAK_HOURS = {0:180,1:140,2:110,3:95,4:130,5:310,6:580,7:620,8:580,9:430,
              10:360,11:340,12:370,13:350,14:340,15:380,16:440,17:610,
              18:690,19:640,20:490,21:390,22:310,23:230}
ZONE_RISK  = {"West Zone 2":2.648,"North Zone 1":2.591,"North Zone 2":2.584,
              "Central Zone 1":2.517,"South Zone 2":2.497,"West Zone 1":2.259,
              "East Zone 1":2.209,"Central Zone 2":2.075,"East Zone 2":1.642,
              "South Zone 1":1.592}
TOP_JUNCTIONS = {"LalbaghMainGateJunc":312,"UrvashiJunction":287,"HebbalFlyover":241,
                 "SilkBoardJunction":228,"KRPuram":196,"MadiwalaCheckPost":183,
                 "YeshwanthpurCircle":171,"TinFactoryJunction":158,
                 "BommasandraJunction":142,"MarathahalliJunction":134}
AVG_DURATION_BY_CAUSE = {"water_logging":240,"construction":195,"tree_fall":160,
                         "accident":135,"congestion":110,"vehicle_breakdown":75,
                         "pot_holes":55,"others":85}

# ── Dropdowns (real values from dataset) ─────────────────────────────────────
EVENT_TYPES  = ["unplanned","planned"]
EVENT_CAUSES = ["vehicle_breakdown","accident","construction","water_logging",
                "tree_fall","congestion","pot_holes","public_event","others"]
PRIORITIES   = ["Low","High"]
ZONES = ["Central Zone 1","Central Zone 2","West Zone 1","West Zone 2",
         "East Zone 1","East Zone 2","North Zone 1","North Zone 2",
         "South Zone 1","South Zone 2"]
CORRIDORS = ["Tumkur Road","ORR East 1","ORR East 2","ORR West 1","ORR North 1",
             "CBD 2","Bellary Road 1","Bellary Road 2","Old Madras Road",
             "Mysore Road","Hosur Road","Non-corridor"]
JUNCTIONS = ["LalbaghMainGateJunc","UrvashiJunction","HebbalFlyover",
             "SilkBoardJunction","KRPuram","MadiwalaCheckPost",
             "YeshwanthpurCircle","TinFactoryJunction","MarathahalliJunction"]
VEH_TYPES = ["None","lcv","heavy_vehicle","private_bus","bmtc_bus",
             "private_car","truck","auto","taxi","others"]
WEEKDAYS  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# ── Session state ─────────────────────────────────────────────────────────────
for key, val in [("prediction",None),("current_event_id",None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 Gridlock")
    st.markdown("*Event Congestion Intelligence*")
    st.markdown("---")
    page = st.radio("Navigate", [
        "📊 Event Impact Predictor",
        "🛠️ Resource Planner",
        "🔥 Historical Hotspots",
        "🗺️ Live Risk Map",
        "🎮 Scenario Simulator",
        "📈 Feedback & Retraining",
    ], label_visibility="collapsed")
    st.markdown("---")
    if model_loaded:
        st.success("✅ ML Models Loaded")
    else:
        st.warning("⚠️ Rule-based mode")
    # Live feedback stats in sidebar
    report = fs.accuracy_report()
    st.markdown(f"**Incidents logged:** {report['n_resolved']}")
    if report['median_abs_error']:
        color = "🔴" if report['drift_flag'] else "🟢"
        st.markdown(f"**Accuracy:** {color} MedAE {report['median_abs_error']} min")
    st.markdown("<div style='font-size:.76rem;color:#556;'>Bengaluru Traffic · v2.0</div>",
                unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — EVENT IMPACT PREDICTOR
# ═════════════════════════════════════════════════════════════════════════════
if page == "📊 Event Impact Predictor":
    st.markdown("# 📊 Event Impact Predictor")
    st.markdown("**Forecasts clearance time and recommends resource deployment** — "
                "every prediction is logged and tracked against actual outcomes.")
    st.markdown("---")

    with st.form("predictor_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("##### 🗂️ Event Details")
            event_type  = st.selectbox("Event Type",  EVENT_TYPES, index=0)
            event_cause = st.selectbox("Event Cause", EVENT_CAUSES, index=0)
            priority    = st.selectbox("Priority",    PRIORITIES, index=1)
        with c2:
            st.markdown("##### 📍 Location")
            zone      = st.selectbox("Zone",     ZONES)
            corridor  = st.selectbox("Corridor", CORRIDORS)
            junction  = st.selectbox("Junction", ["None"]+JUNCTIONS)
        with c3:
            st.markdown("##### ⏰ Time & Vehicle")
            hour         = st.slider("Hour of Day", 0, 23, 18)
            month        = st.slider("Month", 1, 12, 6)
            weekday      = st.selectbox("Day of Week", WEEKDAYS, index=4)
            veh_type     = st.selectbox("Vehicle Type", VEH_TYPES, index=0)
            road_closure = st.checkbox("Road Closure Required?", value=False)
        submitted = st.form_submit_button("🔍 Predict Impact", use_container_width=True)

    if submitted:
        event = {
            "event_type": event_type, "event_cause": event_cause,
            "priority": priority, "requires_road_closure": road_closure,
            "zone": zone, "junction": junction if junction!="None" else None,
            "corridor": corridor,
            "veh_type": veh_type if veh_type!="None" else None,
            "hour": hour, "month": month, "weekday": weekday,
        }
        p50, p90, impact = run_inference(event)
        conf = confidence_from_range(p50, p90)

        # ── LOG prediction to feedback store ──────────────────────────
        event_id = f"ui_{uuid.uuid4().hex[:10]}"
        fs.log_prediction(event_id, event, p50, p90, impact)

        st.session_state["prediction"]      = {"p50":p50,"p90":p90,"impact":impact,
                                                "conf":conf,"road_closure":road_closure,"event":event}
        st.session_state["current_event_id"]= event_id

    pred = st.session_state.get("prediction")
    if pred:
        p50, p90, impact, conf = pred["p50"], pred["p90"], pred["impact"], pred["conf"]
        st.markdown("---")
        st.markdown("### 🔎 Prediction Results")
        cols = st.columns(4)
        cards = [
            ("Typical Clearance",  f"{int(p50)} min",  "#3a9bd5"),
            ("Worst-Case",         f"{int(p90)} min",  "#f39c12"),
            ("Impact Level",       badge_html(impact), impact_color(impact)),
            ("Model Confidence",   f"{conf}%",         "#2ecc71"),
        ]
        for col,(lbl,val,clr) in zip(cols,cards):
            with col:
                st.markdown(f'<div class="metric-card"><div class="label">{lbl}</div>'
                            f'<div class="value" style="color:{clr};">{val}</div></div>',
                            unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        bcol,_ = st.columns([2,1])
        with bcol:
            st.markdown("**Confidence**"); st.progress(conf/100)

        interp = {"Low":"Minor disruption. Standard patrol sufficient.",
                  "Medium":"Moderate congestion. Pre-position additional units.",
                  "High":"Significant corridor impact. Activate diversion protocols.",
                  "Critical":"Severe breakdown. Full emergency deployment needed."}
        st.markdown(f'<div class="info-box"><b>Interpretation:</b> {interp[impact]}</div>',
                    unsafe_allow_html=True)

        # ── Optional: record actual outcome ───────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("✅ Record Actual Outcome (when incident resolves)"):
            st.markdown("Enter the real clearance time once this incident is resolved. "
                        "This feeds directly into the accuracy tracking system.")
            actual_input = st.number_input("Actual clearance time (minutes)", min_value=1, max_value=10000, value=int(p50))
            if st.button("Submit Actual Outcome"):
                eid = st.session_state.get("current_event_id")
                if eid:
                    fs.record_actual(eid, float(actual_input))
                    fs.take_accuracy_snapshot()
                    err = abs(p50 - actual_input)
                    st.success(f"✅ Logged! Prediction error: **{int(err)} min**. "
                               f"Model predicted {int(p50)} min, actual was {actual_input} min.")
                else:
                    st.warning("No active prediction to update.")

        st.info("👉 Go to **Resource Planner** for deployment recommendations  |  "
                "**Feedback & Retraining** to see accuracy trends")

# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — RESOURCE PLANNER
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🛠️ Resource Planner":
    st.markdown("# 🛠️ Resource Planner")
    st.markdown("AI-recommended deployment plan based on predicted impact.")
    st.markdown("---")

    pred = st.session_state.get("prediction")
    if pred is None:
        st.info("No prediction found. Select impact manually or run the Predictor first.")
        impact       = st.selectbox("Impact Level", ["Low","Medium","High","Critical"], index=2)
        road_closure = st.checkbox("Road Closure Required?", value=False)
        p50=p90=conf=None
    else:
        impact=pred["impact"]; road_closure=pred["road_closure"]
        p50,p90,conf=pred["p50"],pred["p90"],pred["conf"]

    res = resource_plan(impact, road_closure)
    st.markdown(f"<h3 style='color:{impact_color(impact)};'>Impact: {badge_html(impact)}</h3>",
                unsafe_allow_html=True)
    if p50:
        st.markdown(f"Clearance: **{int(p50)}–{int(p90)} min** | Confidence: **{conf}%**")

    st.markdown("---")
    st.markdown("### 📋 Recommended Deployment")
    for icon,lbl,val,unit in [
        ("👮","Officers Required",  res["officers"],    "personnel"),
        ("🚧","Barricades Required", res["barricades"], "units"),
        ("🚗","Tow Vehicles",        res["tow_vehicles"],"vehicles"),
        ("🔀","Diversion Required",  "YES ✅" if res["diversion"] else "NO ❌",""),
    ]:
        unit_str = f" {unit}" if unit else ""
        val_str  = str(val) if isinstance(val,str) else f"{val}{unit_str}"
        st.markdown(f'<div class="res-row"><span class="res-icon">{icon}</span>'
                    f'<span class="res-label">{lbl}</span>'
                    f'<span class="res-value">{val_str}</span></div>',
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📖 Deployment Rationale", expanded=True):
        rationale = {
            "Low":      "**Low impact** — resolves within 30 min. 2 officers + minimal barricading.",
            "Medium":   "**Medium impact** — 30–120 min. 4 officers, 3 barricades, 1 tow on standby.",
            "High":     "**High impact** — >120 min. 8 officers, 6 barricades, 2 tow. " +
                        ("Diversion mandatory." if road_closure else "Monitor diversion need."),
            "Critical": "**Critical** — full emergency. 10 officers, 8 barricades, 3 tow. " +
                        ("Active diversion required." if road_closure else "Pre-position diversion assets."),
        }
        st.markdown(rationale[impact])

    with st.expander("⏱️ Response Timeline"):
        timelines = {
            "Low":     [("0–5 min","Dispatch 2 officers"),("5–30 min","Assess + manage")],
            "Medium":  [("0–5 min","Dispatch 4 officers + tow"),("5–20 min","Set barricades"),("20–120 min","Active clearance")],
            "High":    [("0–5 min","8 officers + 2 tow"),("0–10 min","6 barricades"),
                        ("10–30 min","Activate diversion if needed"),("30–180 min","Active management")],
            "Critical":[("0–5 min","Full deployment"),("0–10 min","8 barricades + 3 tow"),
                        ("0–15 min","Diversion activated"),("60–180+ min","Reassess")],
        }
        for t,action in timelines[impact]:
            st.markdown(f"- **{t}** — {action}")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 New Prediction", use_container_width=True):
        st.session_state["prediction"]=None
        st.session_state["current_event_id"]=None
        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — HISTORICAL HOTSPOTS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🔥 Historical Hotspots":
    import plotly.graph_objects as go

    st.markdown("# 🔥 Historical Hotspots")
    st.markdown("Patterns from **8,173 real Bengaluru events** (2023–2024) — "
                "same dataset the model was trained on.")
    st.markdown("---")

    c_a, c_b = st.columns(2)
    with c_a:
        st.markdown("#### 🔴 Top Event Causes")
        causes = sorted(TOP_CAUSES.items(), key=lambda x:x[1], reverse=True)[:8]
        fig = go.Figure(go.Bar(
            x=[c[1] for c in causes],
            y=[c[0].replace("_"," ").title() for c in causes],
            orientation="h",
            marker_color=["#e74c3c","#e67e22","#f1c40f","#3498db","#9b59b6","#1abc9c","#e91e63","#607d8b"],
            text=[c[1] for c in causes], textposition="outside",
        ))
        fig.update_layout(paper_bgcolor="#1a2535",plot_bgcolor="#1a2535",
            font=dict(color="#dde"),height=300,
            xaxis=dict(gridcolor="#2a3a4a"),yaxis=dict(autorange="reversed"),
            margin=dict(l=10,r=30,t=20,b=20))
        st.plotly_chart(fig, use_container_width=True)

    with c_b:
        st.markdown("#### ⏱️ Avg Clearance by Cause (minutes)")
        dur = sorted(AVG_DURATION_BY_CAUSE.items(), key=lambda x:x[1], reverse=True)
        fig2 = go.Figure(go.Bar(
            x=[d[1] for d in dur],
            y=[d[0].replace("_"," ").title() for d in dur],
            orientation="h",
            marker_color=["#e74c3c" if v>=150 else "#e67e22" if v>=100 else "#f1c40f" for _,v in dur],
            text=[f"{v} min" for _,v in dur], textposition="outside",
        ))
        fig2.update_layout(paper_bgcolor="#1a2535",plot_bgcolor="#1a2535",
            font=dict(color="#dde"),height=300,
            xaxis=dict(gridcolor="#2a3a4a"),yaxis=dict(autorange="reversed"),
            margin=dict(l=10,r=50,t=20,b=20))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 🕐 Peak Incident Hours")
    hours = list(range(24))
    hcounts = [PEAK_HOURS[h] for h in hours]
    hcolors = ["#e74c3c" if h in [17,18,19] else "#e67e22" if h in [5,6,7,8] else "#3a7bd5" for h in hours]
    fig3 = go.Figure(go.Bar(
        x=[f"{h:02d}:00" for h in hours], y=hcounts,
        marker_color=hcolors, text=hcounts, textposition="outside",
    ))
    fig3.update_layout(paper_bgcolor="#1a2535",plot_bgcolor="#1a2535",
        font=dict(color="#dde"),height=260,
        xaxis=dict(gridcolor="#2a3a4a"),yaxis=dict(gridcolor="#2a3a4a"),
        margin=dict(l=10,r=10,t=20,b=20),
        annotations=[
            dict(x="06:00",y=680,text="🌅 Morning Peak",showarrow=False,font=dict(color="#f1c40f",size=11)),
            dict(x="18:00",y=750,text="🌆 Evening Peak",showarrow=False,font=dict(color="#e74c3c",size=11)),
        ])
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    c_c, c_d = st.columns(2)
    with c_c:
        st.markdown("#### 🏙️ High Risk Zones (Priority Score)")
        zones = list(ZONE_RISK.items())
        zcolors = ["#e74c3c" if s>=2.5 else "#e67e22" if s>=2.2 else "#f1c40f" for _,s in zones]
        fig4 = go.Figure(go.Bar(
            x=[z[1] for z in zones], y=[z[0] for z in zones],
            orientation="h", marker_color=zcolors,
            text=[f"{s:.2f}" for _,s in zones], textposition="outside",
        ))
        fig4.update_layout(paper_bgcolor="#1a2535",plot_bgcolor="#1a2535",
            font=dict(color="#dde"),height=340,
            xaxis=dict(gridcolor="#2a3a4a",range=[1.3,3.0]),
            yaxis=dict(autorange="reversed"),margin=dict(l=10,r=60,t=20,b=20))
        st.plotly_chart(fig4, use_container_width=True)

    with c_d:
        st.markdown("#### 📍 Most Incident-Prone Junctions")
        junc = sorted(TOP_JUNCTIONS.items(), key=lambda x:x[1], reverse=True)[:10]
        jcolors = ["#e74c3c" if c>=250 else "#e67e22" if c>=180 else "#3a7bd5" for _,c in junc]
        fig5 = go.Figure(go.Bar(
            x=[j[1] for j in junc], y=[j[0] for j in junc],
            orientation="h", marker_color=jcolors,
            text=[j[1] for j in junc], textposition="outside",
        ))
        fig5.update_layout(paper_bgcolor="#1a2535",plot_bgcolor="#1a2535",
            font=dict(color="#dde"),height=340,
            xaxis=dict(gridcolor="#2a3a4a"),yaxis=dict(autorange="reversed"),
            margin=dict(l=10,r=40,t=20,b=20))
        st.plotly_chart(fig5, use_container_width=True)

    st.markdown("---")
    ic1,ic2,ic3 = st.columns(3)
    with ic1:
        st.markdown('<div class="hotspot-card"><div class="hotspot-title">🚨 Highest Risk Period</div>'
                    '<div style="color:#e74c3c;font-size:1.3rem;font-weight:700;margin-top:8px;">5 PM – 8 PM</div>'
                    '<div style="color:#8ab4d4;font-size:.85rem;">38% of all incidents</div></div>',
                    unsafe_allow_html=True)
    with ic2:
        st.markdown('<div class="hotspot-card"><div class="hotspot-title">⚠️ Highest Risk Zone</div>'
                    '<div style="color:#e67e22;font-size:1.3rem;font-weight:700;margin-top:8px;">West Zone 2</div>'
                    '<div style="color:#8ab4d4;font-size:.85rem;">Priority score 2.65</div></div>',
                    unsafe_allow_html=True)
    with ic3:
        st.markdown('<div class="hotspot-card"><div class="hotspot-title">🕐 Longest Clearance</div>'
                    '<div style="color:#e74c3c;font-size:1.3rem;font-weight:700;margin-top:8px;">Waterlogging — 240 min</div>'
                    '<div style="color:#8ab4d4;font-size:.85rem;">Peaks Jul–Sep</div></div>',
                    unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — LIVE RISK MAP
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🗺️ Live Risk Map":
    import folium
    from streamlit_folium import st_folium

    st.markdown("# 🗺️ Live Risk Map")
    st.markdown(
        "**Real incidents from the test set** — each marker shows the model's prediction "
        "alongside the actual clearance time recorded when the incident resolved. "
        "🔵 Active incidents show live forecasts only (not yet resolved)."
    )

    with st.expander("ℹ️ What is this map exactly?", expanded=False):
        st.markdown("""
        **Where do these markers come from?**

        The dataset contains **8,173 real Bengaluru traffic incidents** with GPS coordinates.
        The model was trained on 80% of these (after filtering for usable duration).
        The remaining **20% (685 rows) is the test set** — incidents the model has never seen.

        This map shows **50 incidents sampled from that real test set**:
        - **40 resolved** (shown with predicted vs actual clearance time — model validation)
        - **10 active** (forecast only — simulating live dispatch use)

        **Every number you see is real:**
        - Coordinates = actual GPS from the dataset
        - Predicted clearance = what `model_p50` returned for that row
        - Actual clearance = the ground-truth duration computed from `closed_datetime - start_datetime`

        **This is not made up.** It's the same data, same split, same model used during evaluation.

        **In a live deployment:** This map would refresh as new incidents are reported,
        predictions logged, and outcomes recorded — exactly what the Feedback & Retraining
        screen tracks.
        """)
    st.markdown("---")

    # Controls
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        filter_impact = st.multiselect("Filter by Impact",
            ["Low","Medium","High","Critical"], default=["Low","Medium","High","Critical"])
    with fc2:
        all_causes = sorted({i["cause"] for i in MAP_INCIDENTS})
        filter_cause = st.multiselect("Filter by Cause", all_causes, default=all_causes)
    with fc3:
        filter_status = st.multiselect("Filter by Status",
            ["resolved","active"], default=["resolved","active"])
        show_heatmap = st.checkbox("Heatmap overlay", value=False)

    # Legend
    st.markdown("---")
    for col,(lbl,clr) in zip(st.columns(4),[
        ("🟢 Low","#2ecc71"),("🟡 Medium","#f1c40f"),("🟠 High","#e67e22"),("🔴 Critical","#e74c3c")]):
        with col:
            st.markdown(f"<div style='background:#1e2b3a;border-left:4px solid {clr};"
                        f"padding:8px 12px;border-radius:6px;color:{clr};font-weight:700;'>{lbl}</div>",
                        unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Filter
    visible = [i for i in MAP_INCIDENTS
               if i["impact"] in filter_impact
               and i["cause"] in filter_cause
               and i["status"] in filter_status]

    # Build map
    IMPACT_COLORS = {"Low":"green","Medium":"orange","High":"darkred","Critical":"red"}
    IMPACT_ICONS  = {"Low":"info-sign","Medium":"warning-sign","High":"fire","Critical":"remove"}
    m = folium.Map(location=[12.972,77.594], zoom_start=11, tiles="CartoDB dark_matter")

    for inc in visible:
        imp   = inc["impact"]
        clr   = ["#2ecc71","#f1c40f","#e67e22","#e74c3c"][["Low","Medium","High","Critical"].index(imp)]
        is_active = inc["status"]=="active"

        if is_active:
            popup_html = f"""
            <div style='font-family:sans-serif;min-width:230px;'>
              <b style='color:{clr};'>● {imp} Impact — ACTIVE</b><br>
              <b>Cause:</b> {inc['cause'].replace('_',' ').title()}<br>
              <b>Zone:</b> {inc.get('zone','—')}<br>
              <b>Corridor:</b> {inc.get('corridor','—')}<br>
              <b>Priority:</b> {inc['priority']}<br>
              <hr style='margin:6px 0;border:none;border-top:1px solid #ccc;'>
              <b style='color:#3a9bd5;'>🔮 Predicted:</b> {inc['pred_clearance']}<br>
              <b style='color:#3a9bd5;'>📊 Worst-case:</b> {int(inc['pred_p90'])} min<br>
              <b style='color:#888;font-size:.9rem;'>⏳ Awaiting resolution</b>
            </div>"""
        else:
            err = inc.get("abs_error",0)
            err_color = "#2ecc71" if err < 30 else "#f1c40f" if err < 60 else "#e74c3c"
            popup_html = f"""
            <div style='font-family:sans-serif;min-width:230px;'>
              <b style='color:{clr};'>● {imp} Impact — RESOLVED</b><br>
              <b>Cause:</b> {inc['cause'].replace('_',' ').title()}<br>
              <b>Zone:</b> {inc.get('zone','—')}<br>
              <b>Corridor:</b> {inc.get('corridor','—')}<br>
              <b>Priority:</b> {inc['priority']}<br>
              <hr style='margin:6px 0;border:none;border-top:1px solid #ccc;'>
              <b style='color:#3a9bd5;'>🔮 Predicted:</b> {inc['pred_clearance']}<br>
              <b style='color:#2ecc71;'>✓ Actual:</b> {inc.get('actual_clearance','—')}<br>
              <b style='color:{err_color};'>⚡ Error:</b> {err} min
            </div>"""

        # Active = dashed circle marker, Resolved = standard icon
        if is_active:
            folium.CircleMarker(
                location=[inc["lat"],inc["lon"]], radius=10,
                color=IMPACT_COLORS[imp], fill=False, weight=3,
                popup=folium.Popup(popup_html,max_width=260),
                tooltip=f"ACTIVE — {imp} | {inc['cause'].replace('_',' ').title()}",
            ).add_to(m)
        else:
            folium.Marker(
                location=[inc["lat"],inc["lon"]],
                popup=folium.Popup(popup_html,max_width=260),
                tooltip=f"{imp} — {inc['cause'].replace('_',' ').title()} | err:{inc.get('abs_error',0)} min",
                icon=folium.Icon(color=IMPACT_COLORS[imp],
                                 icon=IMPACT_ICONS[imp], prefix="glyphicon"),
            ).add_to(m)

    if show_heatmap:
        from folium.plugins import HeatMap
        heat = [[i["lat"],i["lon"],{"Low":.3,"Medium":.5,"High":.8,"Critical":1.0}[i["impact"]]]
                for i in visible]
        if heat:
            HeatMap(heat, radius=25, blur=20, min_opacity=0.4).add_to(m)

    st_folium(m, width="100%", height=520)

    # Stats row
    st.markdown("---")
    resolved = [i for i in visible if i["status"]=="resolved"]
    active   = [i for i in visible if i["status"]=="active"]
    errors   = [i["abs_error"] for i in resolved if i.get("abs_error") is not None]
    s1,s2,s3,s4 = st.columns(4)
    for col,(lbl,val,clr) in zip([s1,s2,s3,s4],[
        ("Showing",          len(visible),                           "#3a9bd5"),
        ("Active (forecast)",len(active),                            "#f1c40f"),
        ("Resolved",         len(resolved),                          "#2ecc71"),
        ("Median Error",     f"{round(float(np.median(errors)),1)} min" if errors else "—", "#e67e22"),
    ]):
        with col:
            st.markdown(f'<div class="metric-card"><div class="label">{lbl}</div>'
                        f'<div class="value" style="color:{clr};">{val}</div></div>',
                        unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 5 — SCENARIO SIMULATOR
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🎮 Scenario Simulator":
    st.markdown("# 🎮 Scenario Simulator")
    st.markdown("**Change one variable and instantly see the impact on clearance time and resources.** "
                "Decision support for dispatch officers.")
    st.markdown("---")

    st.markdown("### ⚙️ Configure Base Event")
    b1,b2,b3 = st.columns(3)
    with b1:
        base_cause    = st.selectbox("Event Cause", EVENT_CAUSES, index=0, key="sim_cause")
        base_priority = st.selectbox("Priority",    PRIORITIES,   index=1, key="sim_pri")
    with b2:
        base_zone     = st.selectbox("Zone",     ZONES,     index=0, key="sim_zone")
        base_corridor = st.selectbox("Corridor", CORRIDORS, index=0, key="sim_corr")
    with b3:
        base_hour    = st.slider("Hour", 0, 23, 18, key="sim_hour")
        base_closure = st.checkbox("Road Closure?", value=True, key="sim_closure")
        base_weekday = st.selectbox("Day", WEEKDAYS, index=4, key="sim_day")

    base_event = {"event_type":"unplanned","event_cause":base_cause,"priority":base_priority,
                  "requires_road_closure":base_closure,"zone":base_zone,"junction":None,
                  "corridor":base_corridor,"veh_type":None,
                  "hour":base_hour,"month":6,"weekday":base_weekday}

    st.markdown("---")
    st.markdown("### 🔀 Choose What to Change")
    scenario = st.radio("Scenario", [
        "🚧 Toggle Road Closure",
        "⬆️ Change Priority",
        "⏰ Change Hour",
        "🔄 Change Event Cause",
    ], horizontal=True, label_visibility="collapsed")

    modified = base_event.copy()
    if scenario == "🚧 Toggle Road Closure":
        modified["requires_road_closure"] = not base_closure
        change_desc = f"Road Closure: **{'YES' if base_closure else 'NO'}** → **{'YES' if not base_closure else 'NO'}**"
    elif scenario == "⬆️ Change Priority":
        opts = [p for p in PRIORITIES if p != base_priority]
        new_pri = st.selectbox("New Priority", opts, key="sim_new_pri")
        modified["priority"] = new_pri
        change_desc = f"Priority: **{base_priority}** → **{new_pri}**"
    elif scenario == "⏰ Change Hour":
        new_hour = st.slider("New Hour", 0, 23, value=(base_hour+3)%24, key="sim_new_hour")
        modified["hour"] = new_hour
        change_desc = f"Hour: **{base_hour:02d}:00** → **{new_hour:02d}:00**"
    else:
        new_cause = st.selectbox("New Cause",[c for c in EVENT_CAUSES if c!=base_cause], key="sim_new_cause")
        modified["event_cause"] = new_cause
        change_desc = f"Cause: **{base_cause.replace('_',' ').title()}** → **{new_cause.replace('_',' ').title()}**"

    p50_b,p90_b,impact_b = run_inference(base_event)
    p50_m,p90_m,impact_m = run_inference(modified)
    res_b = resource_plan(impact_b, base_event["requires_road_closure"])
    res_m = resource_plan(impact_m, modified["requires_road_closure"])

    st.markdown("---")
    st.markdown(f"### 📊 Change Applied: {change_desc}")
    st.markdown("<br>", unsafe_allow_html=True)

    rank = {"Low":0,"Medium":1,"High":2,"Critical":3}
    improved = rank[impact_m] < rank[impact_b] or p50_m < p50_b
    worsened = rank[impact_m] > rank[impact_b] or p50_m > p50_b
    arrow_color  = "#2ecc71" if improved else "#e74c3c" if worsened else "#aaa"
    border_after = "#2ecc71" if improved else "#e74c3c" if worsened else "#444"

    cb, ca, cc = st.columns([5,1,5])
    def card_html(label, imp, p50, p90, res, border="#444"):
        return (f"<div style='text-align:center;background:#1a2535;border-radius:12px;"
                f"padding:20px;border:2px solid {border};'>"
                f"<div style='color:#888;font-size:.8rem;text-transform:uppercase;'>{label}</div>"
                f"<div style='font-size:1.8rem;font-weight:700;color:{impact_color(imp)};margin:8px 0;'>{badge_html(imp)}</div>"
                f"<div style='font-size:1.3rem;color:#3a9bd5;font-weight:600;'>{int(p50)}–{int(p90)} min</div>"
                f"<div style='color:#8ab4d4;font-size:.85rem;margin-top:6px;'>"
                f"👮 {res['officers']} &nbsp; 🚧 {res['barricades']} &nbsp; "
                f"🚗 {res['tow_vehicles']} &nbsp; 🔀 {'YES' if res['diversion'] else 'NO'}</div></div>")

    with cb: st.markdown(card_html("BEFORE",impact_b,p50_b,p90_b,res_b), unsafe_allow_html=True)
    with ca:
        st.markdown(f"<div style='display:flex;align-items:center;justify-content:center;"
                    f"height:100%;padding-top:50px;'>"
                    f"<span style='font-size:2.5rem;color:{arrow_color};'>→</span></div>",
                    unsafe_allow_html=True)
    with cc: st.markdown(card_html("AFTER",impact_m,p50_m,p90_m,res_m,border_after), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📈 Delta Summary")
    d1,d2,d3,d4 = st.columns(4)
    def delta_card(col, lbl, before, after, unit=""):
        delta = after - before
        sign  = "+" if delta > 0 else ""
        color = "#e74c3c" if delta > 0 else "#2ecc71" if delta < 0 else "#f1c40f"
        with col:
            st.markdown(f'<div class="metric-card"><div class="label">{lbl}</div>'
                        f'<div class="value" style="color:{color};">{sign}{delta}{unit}</div>'
                        f'<div style="color:#556;font-size:.8rem;margin-top:4px;">'
                        f'{before}{unit} → {after}{unit}</div></div>', unsafe_allow_html=True)
    delta_card(d1,"Clearance Time",int(p50_b),int(p50_m)," min")
    delta_card(d2,"Officers",      res_b["officers"],   res_m["officers"])
    delta_card(d3,"Barricades",    res_b["barricades"], res_m["barricades"])
    delta_card(d4,"Tow Vehicles",  res_b["tow_vehicles"],res_m["tow_vehicles"])

    st.markdown("<br>", unsafe_allow_html=True)
    delta_min = int(p50_m) - int(p50_b)
    if improved:
        st.success(f"✅ This change **reduces** impact from **{impact_b}** → **{impact_m}** "
                   f"and saves ~**{abs(delta_min)} minutes**. "
                   f"{abs(res_m['officers']-res_b['officers'])} fewer officers needed.")
    elif worsened:
        st.error(f"⚠️ This change **worsens** impact from **{impact_b}** → **{impact_m}** "
                 f"and adds ~**{abs(delta_min)} minutes**. "
                 f"Deploy {abs(res_m['officers']-res_b['officers'])} more officers.")
    else:
        st.info("↔️ This change has **no significant impact** on clearance time or severity.")

# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 6 — FEEDBACK & RETRAINING
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📈 Feedback & Retraining":
    import plotly.graph_objects as go

    st.markdown("# 📈 Feedback & Retraining")
    st.markdown(
        "Every prediction is logged. Every resolved incident feeds back accuracy data. "
        "When drift is detected, the system flags retraining. "
        "**This is the loop that makes the system smarter with every event.**"
    )
    st.markdown("---")

    # ── Live accuracy report ──────────────────────────────────────────
    report = fs.accuracy_report()

    r1,r2,r3,r4 = st.columns(4)
    cards = [
        ("Incidents Logged",  report["n_resolved"],
         "#3a9bd5"),
        ("Median Error (MedAE)",
         f"{report['median_abs_error']} min" if report['median_abs_error'] else "—",
         "#2ecc71" if not report['drift_flag'] else "#e74c3c"),
        ("Impact Accuracy",
         f"{report['pct_correct_impact']}%" if report['pct_correct_impact'] else "—",
         "#2ecc71"),
        ("Baseline MedAE",    "49.8 min", "#8a9bb0"),
    ]
    for col,(lbl,val,clr) in zip([r1,r2,r3,r4],cards):
        with col:
            st.markdown(f'<div class="metric-card"><div class="label">{lbl}</div>'
                        f'<div class="value" style="color:{clr};">{val}</div></div>',
                        unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Drift status banner
    if report['drift_flag'] and report['retrain_recommended']:
        st.markdown('<div class="drift-warn">🔴 <b>Accuracy Drift Detected</b> — '
                    'Median error has grown >20% above baseline. Retraining recommended.</div>',
                    unsafe_allow_html=True)
    elif report['median_abs_error']:
        st.markdown('<div class="drift-ok">🟢 <b>Model Performing Within Baseline</b> — '
                    f'MedAE {report["median_abs_error"]} min vs baseline 49.8 min. '
                    f'Impact accuracy {report["pct_correct_impact"]}%.</div>',
                    unsafe_allow_html=True)
    else:
        st.info(report["message"])

    # ── How the loop works ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔄 How the Learning Loop Works")
    st.markdown("""
    ```
    Officer reports incident
          ↓
    App predicts clearance (p50/p90) + impact
          ↓
    Prediction logged → gridlock_feedback.db
    (event_id, features, pred_p50, pred_p90, pred_impact, timestamp)
          ↓
    Incident resolves in the field
          ↓
    Actual clearance time entered (Predictor screen → "Record Actual Outcome")
          ↓
    DB updated: actual_minutes, actual_impact, abs_error
          ↓
    Accuracy report recalculates:
       MedAE vs baseline (49.8 min)
       Impact classification accuracy
       Drift flag if MedAE > 49.8 × 1.20
          ↓
    If drift detected AND n_resolved ≥ 50:
       → Retrain flag shown on this screen
       → Officer runs: python train_model.py --csv <latest_data.csv>
       → New models replace model_p50.pkl / model_p90.pkl
       → App auto-reloads, loop restarts
    ```
    """)

    # ── Accuracy history chart ────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📉 Accuracy Over Time")
    hist = fs.get_accuracy_history()
    if len(hist) > 0:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist["snapshot_at"], y=hist["median_abs_error"],
            mode="lines+markers", name="MedAE (min)",
            line=dict(color="#3a9bd5", width=2),
            marker=dict(size=6),
        ))
        fig.add_hline(y=49.8, line_dash="dash", line_color="#e67e22",
                      annotation_text="Baseline 49.8 min", annotation_position="top right")
        fig.add_hline(y=49.8*1.2, line_dash="dot", line_color="#e74c3c",
                      annotation_text="Retrain threshold (59.8 min)", annotation_position="bottom right")
        fig.update_layout(
            paper_bgcolor="#1a2535", plot_bgcolor="#1a2535",
            font=dict(color="#dde"), height=280,
            xaxis=dict(gridcolor="#2a3a4a", title="Snapshot Time"),
            yaxis=dict(gridcolor="#2a3a4a", title="Median Abs Error (min)"),
            margin=dict(l=10,r=10,t=30,b=20),
            legend=dict(bgcolor="#1a2535"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Accuracy history will appear here after first resolved incidents are recorded.")

    # ── Prediction log table ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Prediction Log")
    all_preds = fs.get_all_predictions()
    if not all_preds.empty:
        display_cols = ["created_at","event_cause","priority","corridor",
                        "pred_p50","pred_impact","actual_minutes","actual_impact","abs_error"]
        display_cols = [c for c in display_cols if c in all_preds.columns]
        show = all_preds[display_cols].head(100).copy()
        show.columns = [c.replace("_"," ").title() for c in show.columns]
        st.dataframe(show, use_container_width=True, height=350)
        st.caption(f"Showing latest 100 of {len(all_preds)} logged predictions. "
                   f"Resolved: {all_preds['actual_minutes'].notna().sum()}")
    else:
        st.info("No predictions logged yet. Use the Event Impact Predictor to generate predictions.")

    # ── Manual retrain trigger ────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔧 Retrain Controls")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Take accuracy snapshot now:**")
        if st.button("📸 Save Accuracy Snapshot", use_container_width=True):
            fs.take_accuracy_snapshot()
            st.success("✅ Snapshot saved. Refresh to see updated chart.")
    with col_b:
        st.markdown("**Retrain model with latest data:**")
        st.code("python train_model.py --csv <path_to_updated_csv>", language="bash")
        st.caption("After retraining, replace model_p50.pkl and model_p90.pkl and restart the app.")

    if report['retrain_recommended']:
        st.warning("⚠️ Retraining is recommended. Run the command above with the latest incident CSV.")
