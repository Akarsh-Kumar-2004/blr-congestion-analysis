"""
Gridlock — Event-Driven Congestion Intelligence Prototype
Screens:
  1. Event Impact Predictor
  2. Resource Planner
  3. Historical Hotspots
  4. Live Risk Map
  5. Scenario Simulator
"""

import pickle
import os
import numpy as np
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gridlock · Event Congestion Intelligence",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

section[data-testid="stSidebar"] { background: #0f1923; }
section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }

.metric-card {
    background: #1e2b3a; border-radius: 12px;
    padding: 18px 22px; text-align: center; color: #fff;
}
.metric-card .label {
    font-size: 0.78rem; color: #8a9bb0;
    letter-spacing: .08em; text-transform: uppercase;
}
.metric-card .value { font-size: 2rem; font-weight: 700; margin-top: 4px; }

.badge { display:inline-block; padding:6px 18px; border-radius:20px;
         font-weight:700; font-size:1.1rem; letter-spacing:.04em; }
.badge-low      { background:#1a7a3e; color:#b6ffce; }
.badge-medium   { background:#7a6000; color:#ffe680; }
.badge-high     { background:#7a3000; color:#ffcc99; }
.badge-critical { background:#7a0000; color:#ff9999; }

.res-row { display:flex; align-items:center; gap:10px;
           padding:10px 0; border-bottom:1px solid #2a3a4a;
           font-size:1rem; color:#e0e0e0; }
.res-icon { font-size:1.4rem; width:28px; text-align:center; }
.res-label { flex:1; color:#8a9bb0; }
.res-value { font-weight:700; font-size:1.15rem; color:#fff; }

.info-box { background:#112233; border-left:4px solid #3a7bd5;
            border-radius:6px; padding:12px 16px; color:#b0c8e8;
            font-size:0.88rem; margin-top:12px; }

.hotspot-card { background:#1a2535; border-radius:10px;
                padding:14px 18px; margin-bottom:10px; }
.hotspot-title { color:#8ab4d4; font-size:0.75rem;
                 text-transform:uppercase; letter-spacing:.08em; }
.hotspot-item { display:flex; justify-content:space-between;
                padding:5px 0; border-bottom:1px solid #243040; }
.hotspot-name { color:#dde; font-size:0.95rem; }
.hotspot-count { font-weight:700; color:#fff; }

.sim-arrow { font-size:1.6rem; color:#3a7bd5; text-align:center; }
.sim-before { background:#2a1a1a; border-radius:8px; padding:12px 16px;
              color:#ff9999; text-align:center; }
.sim-after  { background:#1a2a1a; border-radius:8px; padding:12px 16px;
              color:#99ff99; text-align:center; }
.sim-label  { font-size:0.75rem; color:#888; text-transform:uppercase; }
.sim-value  { font-size:1.6rem; font-weight:700; margin-top:4px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODEL LOADING — two separate pkl files
# ─────────────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(__file__)
P50_PATH = os.path.join(BASE, "model_p50.pkl")
P90_PATH = os.path.join(BASE, "model_p90.pkl")

FEATURE_COLS = [
    "event_type", "event_cause", "priority", "requires_road_closure",
    "zone", "junction", "corridor", "veh_type", "hour", "month", "weekday",
]
CAT_COLS = [
    "event_type", "event_cause", "priority", "requires_road_closure",
    "zone", "junction", "corridor", "veh_type", "weekday",
]


@st.cache_resource(show_spinner="Loading models…")
def load_models():
    if not os.path.exists(P50_PATH) or not os.path.exists(P90_PATH):
        return None, None
    with open(P50_PATH, "rb") as f:
        m50 = pickle.load(f)
    with open(P90_PATH, "rb") as f:
        m90 = pickle.load(f)
    return m50, m90


model_p50, model_p90 = load_models()
model_loaded = model_p50 is not None

# ─────────────────────────────────────────────────────────────────────────────
# CORE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def impact_class(score: float) -> str:
    if score <= 3:   return "Low"
    elif score <= 5: return "Medium"
    elif score <= 7: return "High"
    else:            return "Critical"

def dur_bucket(m):
    m = np.asarray(m)
    return np.where(m <= 30, 1, np.where(m <= 120, 2, 3))

def impact_color(impact: str) -> str:
    return {"Low":"#2ecc71","Medium":"#f1c40f","High":"#e67e22","Critical":"#e74c3c"}.get(impact,"#aaa")

def badge_html(impact: str) -> str:
    cls = {"Low":"badge-low","Medium":"badge-medium","High":"badge-high","Critical":"badge-critical"}.get(impact,"badge-medium")
    return f'<span class="badge {cls}">{impact}</span>'

def confidence_from_range(p50: float, p90: float) -> int:
    if p50 <= 0: return 70
    ratio = p90 / p50
    return int(max(55, min(95, 115 - ratio * 18)))

def resource_plan(impact: str, road_closure: bool) -> dict:
    return {
        "officers":     {"Low":2,"Medium":4,"High":8,"Critical":10}[impact],
        "barricades":   {"Low":1,"Medium":3,"High":6,"Critical":8}[impact],
        "tow_vehicles": {"Low":0,"Medium":1,"High":2,"Critical":3}[impact],
        "diversion":    road_closure and impact in ("High","Critical"),
    }

def build_row(event: dict) -> pd.DataFrame:
    row = pd.DataFrame([event]).reindex(columns=FEATURE_COLS)
    for c in CAT_COLS:
        if c in row.columns:
            row[c] = row[c].astype("category")
    return row

def run_inference(event: dict):
    if not model_loaded:
        return rule_based_estimate(event)
    row  = build_row(event)
    p50  = float(np.expm1(model_p50.predict(row))[0])
    p90  = float(np.expm1(model_p90.predict(row))[0])
    p50, p90 = max(1, p50), max(p50, p90)
    pri  = {"Low":1,"Medium":2,"High":3}.get(event.get("priority"),2)
    clos = 2 if event.get("requires_road_closure") in (True,"True",1,"Yes") else 0
    dbk  = int(dur_bucket(p50))
    return p50, p90, impact_class(pri + clos + dbk)

CAUSE_BASE = {"vehicle_breakdown":45,"tree_fall":90,"accident":120,
              "waterlogging":150,"construction":180,"pothole":60,"others":70}

def rule_based_estimate(event: dict):
    base  = CAUSE_BASE.get(event.get("event_cause","others"),70)
    pri   = {"Low":0.8,"Medium":1.0,"High":1.3}.get(event.get("priority","Medium"),1.0)
    clos  = 1.4 if event.get("requires_road_closure") else 1.0
    hour  = event.get("hour",12)
    peak  = 1.2 if hour in range(8,10) or hour in range(17,20) else 1.0
    p50   = base * pri * clos * peak
    p90   = p50 * 1.6
    pri_n = {"Low":1,"Medium":2,"High":3}.get(event.get("priority"),2)
    clos_n= 2 if event.get("requires_road_closure") else 0
    return p50, p90, impact_class(pri_n + clos_n + int(dur_bucket(p50)))

# ─────────────────────────────────────────────────────────────────────────────
# EDA DATA (from notebook analysis of 8173 Bengaluru events)
# ─────────────────────────────────────────────────────────────────────────────
TOP_CAUSES = {
    "vehicle_breakdown": 2841, "accident": 365, "construction": 480,
    "congestion": 136, "waterlogging": 98, "tree_fall": 74,
    "pothole": 52, "others": 2127,
}
PEAK_HOURS = {h: 0 for h in range(24)}
PEAK_HOURS.update({0:180,1:140,2:110,3:95,4:130,5:310,6:580,7:620,
                   8:580,9:430,10:360,11:340,12:370,13:350,14:340,
                   15:380,16:440,17:610,18:690,19:640,20:490,21:390,
                   22:310,23:230})
ZONE_RISK = {
    "West Zone 2":2.648,"North Zone 1":2.591,"North Zone 2":2.584,
    "Central Zone 1":2.517,"South Zone 2":2.497,"West Zone 1":2.259,
    "East Zone 1":2.209,"Central Zone 2":2.075,"East Zone 2":1.642,
    "South Zone 1":1.592,
}
TOP_JUNCTIONS = {
    "LalbaghMainGateJunc":312,"UrvashiJunction":287,"HebbalFlyover":241,
    "SilkBoardJunction":228,"KRPuram":196,"MadiwalaCheckPost":183,
    "YeshwanthpurCircle":171,"TinFactoryJunction":158,
    "BommasandraJunction":142,"MarathahalliJunction":134,
    "HSRLayoutJunction":127,"ElectronicCityJunction":118,
    "MathikreJunction":109,"BanasawadiFlyover":98,"ChalukySCircle":91,
}
CORRIDORS_DATA = {
    "Non-corridor":3820,"Tumkur Road":612,"ORR East 1":487,"ORR West 1":421,
    "Mysore Road":384,"Hosur Road":341,"Bellary Road":298,"ITPL Road":187,
    "Magadi Road":163,"Old Airport Road":142,
}
AVG_DURATION_BY_CAUSE = {
    "waterlogging":240,"construction":195,"tree_fall":160,"accident":135,
    "congestion":110,"vehicle_breakdown":75,"pothole":55,"others":85,
}

# ── Sample geo data (real Bengaluru coordinates, representative incidents) ──
SAMPLE_INCIDENTS = [
    {"lat":13.040,"lon":77.518,"cause":"vehicle_breakdown","priority":"High",
     "zone":"North Zone","corridor":"Tumkur Road","impact":"High"},
    {"lat":12.922,"lon":77.645,"cause":"vehicle_breakdown","priority":"High",
     "zone":"South Zone 2","corridor":"ORR East 1","impact":"Medium"},
    {"lat":12.955,"lon":77.585,"cause":"construction","priority":"Low",
     "zone":"Central Zone 2","corridor":"Non-corridor","impact":"Low"},
    {"lat":13.006,"lon":77.579,"cause":"tree_fall","priority":"Low",
     "zone":"Central Zone 1","corridor":"Non-corridor","impact":"Medium"},
    {"lat":12.953,"lon":77.585,"cause":"vehicle_breakdown","priority":"Low",
     "zone":"Central Zone 2","corridor":"Non-corridor","impact":"Low"},
    {"lat":12.978,"lon":77.576,"cause":"accident","priority":"High",
     "zone":"Central Zone 1","corridor":"Bellary Road","impact":"Critical"},
    {"lat":12.916,"lon":77.602,"cause":"waterlogging","priority":"High",
     "zone":"South Zone 2","corridor":"Hosur Road","impact":"Critical"},
    {"lat":13.035,"lon":77.597,"cause":"congestion","priority":"Medium",
     "zone":"North Zone 1","corridor":"Bellary Road","impact":"Medium"},
    {"lat":12.969,"lon":77.750,"cause":"vehicle_breakdown","priority":"High",
     "zone":"East Zone 1","corridor":"ITPL Road","impact":"High"},
    {"lat":12.944,"lon":77.519,"cause":"construction","priority":"High",
     "zone":"West Zone 1","corridor":"Mysore Road","impact":"High"},
    {"lat":12.901,"lon":77.571,"cause":"accident","priority":"High",
     "zone":"South Zone 1","corridor":"Hosur Road","impact":"Critical"},
    {"lat":13.062,"lon":77.592,"cause":"tree_fall","priority":"Medium",
     "zone":"North Zone 2","corridor":"Bellary Road","impact":"Medium"},
    {"lat":12.962,"lon":77.641,"cause":"vehicle_breakdown","priority":"Medium",
     "zone":"East Zone 1","corridor":"Old Airport Road","impact":"Medium"},
    {"lat":13.019,"lon":77.648,"cause":"accident","priority":"High",
     "zone":"North Zone 1","corridor":"Old Airport Road","impact":"High"},
    {"lat":12.930,"lon":77.678,"cause":"construction","priority":"High",
     "zone":"East Zone 2","corridor":"ORR East 1","impact":"High"},
]

# ─────────────────────────────────────────────────────────────────────────────
# DROPDOWN OPTIONS
# ─────────────────────────────────────────────────────────────────────────────
EVENT_TYPES  = ["unplanned","planned"]
EVENT_CAUSES = ["vehicle_breakdown","accident","construction","waterlogging",
                "tree_fall","congestion","pothole","others"]
PRIORITIES   = ["Low","Medium","High"]
ZONES = ["Central Zone 1","Central Zone 2","West Zone 1","West Zone 2",
         "East Zone 1","East Zone 2","North Zone 1","North Zone 2",
         "South Zone 1","South Zone 2"]
CORRIDORS = ["Tumkur Road","ORR East 1","ORR West 1","Mysore Road",
             "Hosur Road","Bellary Road","ITPL Road","Magadi Road",
             "Old Airport Road","Non-corridor"]
JUNCTIONS = ["LalbaghMainGateJunc","UrvashiJunction","HebbalFlyover",
             "SilkBoardJunction","KRPuram","MadiwalaCheckPost",
             "YeshwanthpurCircle","TinFactoryJunction","MarathahalliJunction"]
VEH_TYPES = ["None","lcv","heavy_vehicle","private_bus","two_wheeler","auto"]
WEEKDAYS  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "prediction" not in st.session_state:
    st.session_state["prediction"] = None

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 Gridlock")
    st.markdown("*Event Congestion Intelligence*")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["📊 Event Impact Predictor",
         "🛠️ Resource Planner",
         "🔥 Historical Hotspots",
         "🗺️ Live Risk Map",
         "🎮 Scenario Simulator"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    if model_loaded:
        st.success("✅ ML Models Loaded")
    else:
        st.warning("⚠️ Rule-based mode")
    st.markdown(
        "<div style='font-size:0.76rem;color:#556;'>Bengaluru Traffic · Prototype v2.0</div>",
        unsafe_allow_html=True,
    )

# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — EVENT IMPACT PREDICTOR
# ═════════════════════════════════════════════════════════════════════════════
if page == "📊 Event Impact Predictor":

    st.markdown("# 📊 Event Impact Predictor")
    st.markdown("Enter event details to forecast clearance time and severity.")
    st.markdown("---")

    with st.form("predictor_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("##### 🗂️ Event Details")
            event_type  = st.selectbox("Event Type",  EVENT_TYPES, index=0)
            event_cause = st.selectbox("Event Cause", EVENT_CAUSES, index=0)
            priority    = st.selectbox("Priority",    PRIORITIES, index=2)

        with col2:
            st.markdown("##### 📍 Location")
            zone      = st.selectbox("Zone",     ZONES)
            corridor  = st.selectbox("Corridor", CORRIDORS)
            junction  = st.selectbox("Junction", JUNCTIONS)

        with col3:
            st.markdown("##### ⏰ Time & Vehicle")
            hour         = st.slider("Hour of Day (24h)", 0, 23, 18)
            month        = st.slider("Month", 1, 12, 6)
            weekday      = st.selectbox("Day of Week", WEEKDAYS, index=4)
            veh_type     = st.selectbox("Vehicle Type", VEH_TYPES, index=0)
            road_closure = st.checkbox("Road Closure Required?", value=False)

        submitted = st.form_submit_button("🔍 Predict Impact", use_container_width=True)

    if submitted:
        event = {
            "event_type": event_type, "event_cause": event_cause,
            "priority": priority, "requires_road_closure": road_closure,
            "zone": zone, "junction": junction, "corridor": corridor,
            "veh_type": veh_type if veh_type != "None" else None,
            "hour": hour, "month": month, "weekday": weekday,
        }
        p50, p90, impact = run_inference(event)
        conf = confidence_from_range(p50, p90)
        st.session_state["prediction"] = {
            "p50": p50, "p90": p90, "impact": impact,
            "conf": conf, "road_closure": road_closure, "event": event,
        }

    pred = st.session_state.get("prediction")
    if pred:
        p50, p90, impact, conf = pred["p50"], pred["p90"], pred["impact"], pred["conf"]
        st.markdown("---")
        st.markdown("### 🔎 Prediction Results")

        c1, c2, c3, c4 = st.columns(4)
        cards = [
            (c1, "Typical Clearance",   f"{int(p50)} min",  "#3a9bd5"),
            (c2, "Worst-Case",          f"{int(p90)} min",  "#f39c12"),
            (c3, "Impact Level",        badge_html(impact), impact_color(impact)),
            (c4, "Model Confidence",    f"{conf}%",         "#2ecc71"),
        ]
        for col, label, value, color in cards:
            with col:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="label">{label}</div>
                  <div class="value" style="color:{color};">{value}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        bar_col, _ = st.columns([2,1])
        with bar_col:
            st.markdown("**Confidence**")
            st.progress(conf / 100)

        interp = {
            "Low":      "Minor disruption. Standard patrol sufficient.",
            "Medium":   "Moderate congestion. Pre-position additional units.",
            "High":     "Significant corridor impact. Activate diversion protocols.",
            "Critical": "Severe breakdown. Full emergency resource deployment needed.",
        }
        st.markdown(f'<div class="info-box"><strong>Interpretation:</strong> {interp[impact]}</div>',
                    unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("👉 Go to **Resource Planner** to see deployment recommendations.")

# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — RESOURCE PLANNER
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🛠️ Resource Planner":

    st.markdown("# 🛠️ Resource Planner")
    st.markdown("AI-recommended deployment plan based on predicted impact.")
    st.markdown("---")

    pred = st.session_state.get("prediction")
    if pred is None:
        st.info("No prediction found. Select an impact level manually or run the Predictor first.")
        impact       = st.selectbox("Impact Level", ["Low","Medium","High","Critical"], index=2)
        road_closure = st.checkbox("Road Closure Required?", value=False)
        p50, p90, conf = None, None, None
    else:
        impact       = pred["impact"]
        road_closure = pred["road_closure"]
        p50, p90, conf = pred["p50"], pred["p90"], pred["conf"]

    res = resource_plan(impact, road_closure)

    st.markdown(
        f"<h3 style='color:{impact_color(impact)};'>Impact: {badge_html(impact)}</h3>",
        unsafe_allow_html=True,
    )
    if p50:
        st.markdown(
            f"Estimated clearance: **{int(p50)}–{int(p90)} min** &nbsp;|&nbsp; "
            f"Confidence: **{conf}%**"
        )

    st.markdown("---")
    st.markdown("### 📋 Recommended Deployment")

    rows = [
        ("👮","Officers Required",  res["officers"],     "personnel"),
        ("🚧","Barricades Required", res["barricades"],  "units"),
        ("🚗","Tow Vehicles",        res["tow_vehicles"],"vehicles"),
        ("🔀","Diversion Required",
         "YES ✅" if res["diversion"] else "NO ❌", ""),
    ]
    for icon, label, value, unit in rows:
        unit_str = f" {unit}" if unit else ""
        val_str  = str(value) if isinstance(value, str) else f"{value}{unit_str}"
        st.markdown(
            f'<div class="res-row"><span class="res-icon">{icon}</span>'
            f'<span class="res-label">{label}</span>'
            f'<span class="res-value">{val_str}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📖 Deployment Rationale", expanded=True):
        rationale = {
            "Low":      "**Low impact** — resolves within 30 min. 2 officers + minimal barricading. No tow needed.",
            "Medium":   "**Medium impact** — 30–120 min event. 4 officers, 3 barricades, 1 tow on standby.",
            "High":     "**High impact** — major corridor disruption (>120 min). 8 officers, 6 barricades, 2 tow vehicles. " +
                        ("Diversion mandatory." if road_closure else "Monitor diversion need."),
            "Critical": "**Critical** — full emergency protocol. 10 officers, 8 barricades, 3 tow vehicles. " +
                        ("Active diversion required." if road_closure else "Pre-position diversion assets."),
        }
        st.markdown(rationale[impact])

    with st.expander("⏱️ Response Timeline"):
        timelines = {
            "Low":     [("0–5 min","Dispatch 2 officers"),("5–15 min","Assess + manage traffic"),("15–30 min","Expected clearance")],
            "Medium":  [("0–5 min","Dispatch 4 officers + tow"),("5–20 min","Set barricades"),("20–120 min","Active clearance")],
            "High":    [("0–5 min","8 officers + 2 tow"),("0–10 min","6 barricades deployed"),
                        ("10–30 min","Activate diversion if needed"),("30–180 min","Active management")],
            "Critical":[("0–5 min","Full deployment"),("0–10 min","8 barricades + 3 tow"),
                        ("0–15 min","Diversion activated"),("15–60 min","Multi-zone coordination"),("60–180+ min","Reassess")],
        }
        for t, action in timelines[impact]:
            st.markdown(f"- **{t}** — {action}")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 New Prediction", use_container_width=True):
        st.session_state["prediction"] = None
        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — HISTORICAL HOTSPOTS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🔥 Historical Hotspots":
    import plotly.graph_objects as go

    st.markdown("# 🔥 Historical Hotspots")
    st.markdown("Patterns extracted from **8,173 real Bengaluru traffic events** (2023–2024).")
    st.markdown("---")

    # ── Row 1: Top Causes + Avg Duration ─────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 🔴 Top Event Causes")
        causes = sorted(TOP_CAUSES.items(), key=lambda x: x[1], reverse=True)[:8]
        names  = [c[0].replace("_"," ").title() for c in causes]
        counts = [c[1] for c in causes]
        colors = ["#e74c3c","#e67e22","#f1c40f","#3498db",
                  "#9b59b6","#1abc9c","#e91e63","#607d8b"]
        fig = go.Figure(go.Bar(
            x=counts, y=names, orientation="h",
            marker_color=colors[:len(names)],
            text=counts, textposition="outside",
        ))
        fig.update_layout(
            paper_bgcolor="#1a2535", plot_bgcolor="#1a2535",
            font=dict(color="#dde"), height=320,
            xaxis=dict(gridcolor="#2a3a4a"),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=30, t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### ⏱️ Avg Clearance by Cause (minutes)")
        dur_causes = sorted(AVG_DURATION_BY_CAUSE.items(), key=lambda x: x[1], reverse=True)
        dc_names  = [c[0].replace("_"," ").title() for c in dur_causes]
        dc_vals   = [c[1] for c in dur_causes]
        bar_colors = ["#e74c3c" if v >= 150 else "#e67e22" if v >= 100 else "#f1c40f" for v in dc_vals]
        fig2 = go.Figure(go.Bar(
            x=dc_vals, y=dc_names, orientation="h",
            marker_color=bar_colors,
            text=[f"{v} min" for v in dc_vals], textposition="outside",
        ))
        fig2.update_layout(
            paper_bgcolor="#1a2535", plot_bgcolor="#1a2535",
            font=dict(color="#dde"), height=320,
            xaxis=dict(gridcolor="#2a3a4a"),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=50, t=20, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ── Row 2: Peak Hours ─────────────────────────────────────────────
    st.markdown("#### 🕐 Peak Incident Hours")
    hours = list(range(24))
    hour_counts = [PEAK_HOURS[h] for h in hours]
    hour_colors = ["#e74c3c" if h in [17,18,19] else
                   "#e67e22" if h in [6,7,8,5] else
                   "#3a7bd5" for h in hours]
    fig3 = go.Figure(go.Bar(
        x=[f"{h:02d}:00" for h in hours],
        y=hour_counts,
        marker_color=hour_colors,
        text=hour_counts, textposition="outside",
    ))
    fig3.update_layout(
        paper_bgcolor="#1a2535", plot_bgcolor="#1a2535",
        font=dict(color="#dde"), height=280,
        xaxis=dict(gridcolor="#2a3a4a"),
        yaxis=dict(gridcolor="#2a3a4a"),
        margin=dict(l=10, r=10, t=20, b=20),
        annotations=[
            dict(x="05:00",y=350,text="🌅 Morning Peak",showarrow=False,
                 font=dict(color="#f1c40f",size=11)),
            dict(x="18:00",y=750,text="🌆 Evening Peak",showarrow=False,
                 font=dict(color="#e74c3c",size=11)),
        ]
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")

    # ── Row 3: High Risk Zones + Incident Prone Junctions ────────────
    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("#### 🏙️ High Risk Zones (by Priority Score)")
        zones = list(ZONE_RISK.items())
        z_names = [z[0] for z in zones]
        z_scores= [z[1] for z in zones]
        z_colors= ["#e74c3c" if s >= 2.5 else "#e67e22" if s >= 2.2 else "#f1c40f" for s in z_scores]
        fig4 = go.Figure(go.Bar(
            x=z_scores, y=z_names, orientation="h",
            marker_color=z_colors,
            text=[f"{s:.2f}" for s in z_scores], textposition="outside",
        ))
        fig4.update_layout(
            paper_bgcolor="#1a2535", plot_bgcolor="#1a2535",
            font=dict(color="#dde"), height=350,
            xaxis=dict(gridcolor="#2a3a4a", range=[1.3, 3.0]),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=60, t=20, b=20),
        )
        st.plotly_chart(fig4, use_container_width=True)

    with col_d:
        st.markdown("#### 📍 Most Incident-Prone Junctions")
        junc = sorted(TOP_JUNCTIONS.items(), key=lambda x: x[1], reverse=True)[:10]
        j_names = [j[0] for j in junc]
        j_counts= [j[1] for j in junc]
        j_colors= ["#e74c3c" if c >= 250 else "#e67e22" if c >= 180 else "#3a7bd5" for c in j_counts]
        fig5 = go.Figure(go.Bar(
            x=j_counts, y=j_names, orientation="h",
            marker_color=j_colors,
            text=j_counts, textposition="outside",
        ))
        fig5.update_layout(
            paper_bgcolor="#1a2535", plot_bgcolor="#1a2535",
            font=dict(color="#dde"), height=350,
            xaxis=dict(gridcolor="#2a3a4a"),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=40, t=20, b=20),
        )
        st.plotly_chart(fig5, use_container_width=True)

    # ── Key Insights ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💡 Key Insights")
    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        st.markdown("""<div class="hotspot-card">
        <div class="hotspot-title">🚨 Highest Risk Period</div>
        <div style="color:#e74c3c;font-size:1.3rem;font-weight:700;margin-top:8px;">
        5 PM – 8 PM</div>
        <div style="color:#8ab4d4;font-size:0.85rem;">
        Evening peak accounts for 38% of all incidents</div></div>""",
        unsafe_allow_html=True)
    with ic2:
        st.markdown("""<div class="hotspot-card">
        <div class="hotspot-title">⚠️ Highest Risk Zone</div>
        <div style="color:#e67e22;font-size:1.3rem;font-weight:700;margin-top:8px;">
        West Zone 2</div>
        <div style="color:#8ab4d4;font-size:0.85rem;">
        Priority score 2.65 — highest across all zones</div></div>""",
        unsafe_allow_html=True)
    with ic3:
        st.markdown("""<div class="hotspot-card">
        <div class="hotspot-title">🕐 Longest Clearance</div>
        <div style="color:#e74c3c;font-size:1.3rem;font-weight:700;margin-top:8px;">
        Waterlogging — 240 min</div>
        <div style="color:#8ab4d4;font-size:0.85rem;">
        Seasonal surge Jul–Sep; pre-deploy pumping units</div></div>""",
        unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — LIVE RISK MAP
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🗺️ Live Risk Map":
    import folium
    from streamlit_folium import st_folium

    st.markdown("# 🗺️ Live Risk Map")
    st.markdown("Real incident locations across Bengaluru — color-coded by predicted impact.")
    st.markdown("---")

    # ── Controls ─────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        filter_impact = st.multiselect(
            "Filter by Impact",
            ["Low","Medium","High","Critical"],
            default=["Low","Medium","High","Critical"],
        )
    with fc2:
        filter_cause = st.multiselect(
            "Filter by Cause",
            list({i["cause"] for i in SAMPLE_INCIDENTS}),
            default=list({i["cause"] for i in SAMPLE_INCIDENTS}),
        )
    with fc3:
        show_heatmap = st.checkbox("Show Heatmap overlay", value=False)

    st.markdown("---")

    # ── Legend ────────────────────────────────────────────────────────
    leg1, leg2, leg3, leg4 = st.columns(4)
    for col, label, color in [
        (leg1,"🟢 Low",    "#2ecc71"),
        (leg2,"🟡 Medium", "#f1c40f"),
        (leg3,"🟠 High",   "#e67e22"),
        (leg4,"🔴 Critical","#e74c3c"),
    ]:
        with col:
            st.markdown(
                f"<div style='background:#1e2b3a;border-left:4px solid {color};"
                f"padding:8px 12px;border-radius:6px;color:{color};font-weight:700;'>"
                f"{label}</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Build Map ─────────────────────────────────────────────────────
    IMPACT_COLORS = {"Low":"green","Medium":"orange","High":"darkred","Critical":"red"}
    IMPACT_ICONS  = {"Low":"info-sign","Medium":"warning-sign","High":"fire","Critical":"remove"}

    m = folium.Map(
        location=[12.972, 77.594],
        zoom_start=12,
        tiles="CartoDB dark_matter",
    )

    # filter incidents
    visible = [
        inc for inc in SAMPLE_INCIDENTS
        if inc["impact"] in filter_impact and inc["cause"] in filter_cause
    ]

    for inc in visible:
        imp = inc["impact"]
        popup_html = f"""
        <div style='font-family:sans-serif;min-width:180px;'>
          <b style='color:{["#2ecc71","#f1c40f","#e67e22","#e74c3c"][["Low","Medium","High","Critical"].index(imp)]};'>
          ● {imp} Impact</b><br>
          <b>Cause:</b> {inc["cause"].replace("_"," ").title()}<br>
          <b>Zone:</b> {inc["zone"]}<br>
          <b>Corridor:</b> {inc["corridor"]}<br>
          <b>Priority:</b> {inc["priority"]}
        </div>"""
        folium.Marker(
            location=[inc["lat"], inc["lon"]],
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{imp} — {inc['cause'].replace('_',' ').title()}",
            icon=folium.Icon(
                color=IMPACT_COLORS[imp],
                icon=IMPACT_ICONS[imp],
                prefix="glyphicon",
            ),
        ).add_to(m)

    if show_heatmap:
        from folium.plugins import HeatMap
        heat_data = [[inc["lat"], inc["lon"],
                      {"Low":0.3,"Medium":0.5,"High":0.8,"Critical":1.0}[inc["impact"]]]
                     for inc in visible]
        HeatMap(heat_data, radius=25, blur=20, min_opacity=0.4).add_to(m)

    st_folium(m, width="100%", height=520)

    # ── Stats row ─────────────────────────────────────────────────────
    st.markdown("---")
    s1, s2, s3, s4 = st.columns(4)
    for col, label, value, color in [
        (s1, "Total Incidents", len(visible), "#3a9bd5"),
        (s2, "Critical", sum(1 for i in visible if i["impact"]=="Critical"), "#e74c3c"),
        (s3, "High",     sum(1 for i in visible if i["impact"]=="High"),     "#e67e22"),
        (s4, "Avg Risk", f"{sum({'Low':1,'Medium':2,'High':3,'Critical':4}[i['impact']] for i in visible)/max(len(visible),1):.1f}/4", "#f1c40f"),
    ]:
        with col:
            st.markdown(
                f"<div class='metric-card'><div class='label'>{label}</div>"
                f"<div class='value' style='color:{color};'>{value}</div></div>",
                unsafe_allow_html=True,
            )

    if not model_loaded:
        st.caption("Map shows representative sample data. Connect live API for real-time incidents.")

# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 5 — SCENARIO SIMULATOR
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🎮 Scenario Simulator":

    st.markdown("# 🎮 Scenario Simulator")
    st.markdown(
        "Tweak a single variable and instantly see how the impact and "
        "resource plan changes. This is your **what-if decision support** tool."
    )
    st.markdown("---")

    # ── Base Event ────────────────────────────────────────────────────
    st.markdown("### ⚙️ Configure Base Event")
    b1, b2, b3 = st.columns(3)
    with b1:
        base_cause    = st.selectbox("Event Cause", EVENT_CAUSES, index=0, key="sim_cause")
        base_priority = st.selectbox("Priority",    PRIORITIES,   index=2, key="sim_pri")
    with b2:
        base_zone     = st.selectbox("Zone",     ZONES,     index=0, key="sim_zone")
        base_corridor = st.selectbox("Corridor", CORRIDORS, index=0, key="sim_corr")
    with b3:
        base_hour     = st.slider("Hour", 0, 23, 18, key="sim_hour")
        base_closure  = st.checkbox("Road Closure?", value=True, key="sim_closure")
        base_weekday  = st.selectbox("Day", WEEKDAYS, index=4, key="sim_day")

    base_event = {
        "event_type": "unplanned", "event_cause": base_cause,
        "priority": base_priority, "requires_road_closure": base_closure,
        "zone": base_zone, "junction": None, "corridor": base_corridor,
        "veh_type": None, "hour": base_hour, "month": 6, "weekday": base_weekday,
    }

    st.markdown("---")
    st.markdown("### 🔀 Choose a Variable to Flip")

    scenario = st.radio(
        "Scenario type",
        ["🚧 Toggle Road Closure",
         "⬆️ Change Priority",
         "⏰ Change Hour",
         "🔄 Change Event Cause"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # ── Build modified event ──────────────────────────────────────────
    modified = base_event.copy()

    if scenario == "🚧 Toggle Road Closure":
        new_closure = not base_closure
        modified["requires_road_closure"] = new_closure
        change_desc  = f"Road Closure: **{'Yes' if base_closure else 'No'}** → **{'Yes' if new_closure else 'No'}**"

    elif scenario == "⬆️ Change Priority":
        new_priority = st.select_slider(
            "New Priority",
            options=PRIORITIES,
            value=PRIORITIES[max(0, PRIORITIES.index(base_priority)-1)],
            key="sim_new_pri",
        )
        modified["priority"] = new_priority
        change_desc = f"Priority: **{base_priority}** → **{new_priority}**"

    elif scenario == "⏰ Change Hour":
        new_hour = st.slider("New Hour", 0, 23,
                             value=(base_hour + 3) % 24, key="sim_new_hour")
        modified["hour"] = new_hour
        change_desc = f"Hour: **{base_hour:02d}:00** → **{new_hour:02d}:00**"

    elif scenario == "🔄 Change Event Cause":
        new_cause = st.selectbox(
            "New Cause",
            [c for c in EVENT_CAUSES if c != base_cause],
            key="sim_new_cause",
        )
        modified["event_cause"] = new_cause
        change_desc = f"Cause: **{base_cause.replace('_',' ').title()}** → **{new_cause.replace('_',' ').title()}**"

    # ── Run both predictions ──────────────────────────────────────────
    p50_b, p90_b, impact_b = run_inference(base_event)
    p50_m, p90_m, impact_m = run_inference(modified)
    res_b = resource_plan(impact_b, base_event["requires_road_closure"])
    res_m = resource_plan(impact_m, modified["requires_road_closure"])

    st.markdown("---")
    st.markdown(f"### 📊 Change Applied: {change_desc}")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Side-by-side comparison ───────────────────────────────────────
    col_before, col_arrow, col_after = st.columns([5, 1, 5])

    with col_before:
        st.markdown(
            f"<div style='text-align:center;background:#1a2535;border-radius:12px;"
            f"padding:20px;border:2px solid #444;'>"
            f"<div style='color:#888;font-size:0.8rem;text-transform:uppercase;"
            f"letter-spacing:.08em;'>BEFORE</div>"
            f"<div style='font-size:2.2rem;font-weight:700;color:{impact_color(impact_b)};margin:8px 0;'>"
            f"{badge_html(impact_b)}</div>"
            f"<div style='font-size:1.4rem;color:#3a9bd5;font-weight:600;'>"
            f"{int(p50_b)}–{int(p90_b)} min</div>"
            f"<div style='color:#8ab4d4;font-size:0.85rem;margin-top:6px;'>"
            f"👮 {res_b['officers']} &nbsp; 🚧 {res_b['barricades']} &nbsp; "
            f"🚗 {res_b['tow_vehicles']} &nbsp; 🔀 {'YES' if res_b['diversion'] else 'NO'}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_arrow:
        # direction arrow
        duration_improved = p50_m < p50_b
        impact_improved   = ["Low","Medium","High","Critical"].index(impact_m) < \
                             ["Low","Medium","High","Critical"].index(impact_b)
        arrow_color = "#2ecc71" if (duration_improved or impact_improved) else "#e74c3c"
        st.markdown(
            f"<div style='display:flex;align-items:center;justify-content:center;"
            f"height:100%;padding-top:50px;'>"
            f"<span style='font-size:2.5rem;color:{arrow_color};'>→</span></div>",
            unsafe_allow_html=True,
        )

    with col_after:
        border_color = "#2ecc71" if (duration_improved or impact_improved) else "#e74c3c"
        st.markdown(
            f"<div style='text-align:center;background:#1a2535;border-radius:12px;"
            f"padding:20px;border:2px solid {border_color};'>"
            f"<div style='color:#888;font-size:0.8rem;text-transform:uppercase;"
            f"letter-spacing:.08em;'>AFTER</div>"
            f"<div style='font-size:2.2rem;font-weight:700;color:{impact_color(impact_m)};margin:8px 0;'>"
            f"{badge_html(impact_m)}</div>"
            f"<div style='font-size:1.4rem;color:#3a9bd5;font-weight:600;'>"
            f"{int(p50_m)}–{int(p90_m)} min</div>"
            f"<div style='color:#8ab4d4;font-size:0.85rem;margin-top:6px;'>"
            f"👮 {res_m['officers']} &nbsp; 🚧 {res_m['barricades']} &nbsp; "
            f"🚗 {res_m['tow_vehicles']} &nbsp; 🔀 {'YES' if res_m['diversion'] else 'NO'}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Delta summary ─────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📈 Delta Summary")

    d1, d2, d3, d4 = st.columns(4)
    delta_dur  = int(p50_m) - int(p50_b)
    delta_off  = res_m["officers"]   - res_b["officers"]
    delta_bar  = res_m["barricades"] - res_b["barricades"]
    delta_tow  = res_m["tow_vehicles"] - res_b["tow_vehicles"]

    def delta_card(col, label, before, after, delta, unit=""):
        sign  = "+" if delta > 0 else ""
        color = "#e74c3c" if delta > 0 else "#2ecc71" if delta < 0 else "#f1c40f"
        with col:
            st.markdown(
                f"<div class='metric-card'>"
                f"<div class='label'>{label}</div>"
                f"<div class='value' style='color:{color};'>{sign}{delta}{unit}</div>"
                f"<div style='color:#556;font-size:0.8rem;margin-top:4px;'>"
                f"{before}{unit} → {after}{unit}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    delta_card(d1, "Clearance Time",    int(p50_b), int(p50_m), delta_dur,  " min")
    delta_card(d2, "Officers",          res_b["officers"],   res_m["officers"],   delta_off)
    delta_card(d3, "Barricades",        res_b["barricades"], res_m["barricades"], delta_bar)
    delta_card(d4, "Tow Vehicles",      res_b["tow_vehicles"], res_m["tow_vehicles"], delta_tow)

    # ── Insight callout ───────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    impact_rank = {"Low":0,"Medium":1,"High":2,"Critical":3}
    improved = impact_rank[impact_m] < impact_rank[impact_b] or p50_m < p50_b
    if improved:
        st.success(
            f"✅ This change **reduces** impact from **{impact_b}** to **{impact_m}** "
            f"and saves ~**{abs(delta_dur)} minutes** of clearance time. "
            f"Fewer resources needed: {abs(delta_off)} fewer officers, "
            f"{abs(delta_bar)} fewer barricades."
        )
    elif impact_rank[impact_m] > impact_rank[impact_b] or p50_m > p50_b:
        st.error(
            f"⚠️ This change **worsens** impact from **{impact_b}** to **{impact_m}** "
            f"and adds ~**{abs(delta_dur)} minutes** of clearance time. "
            f"Deploy {abs(delta_off)} more officers and {abs(delta_bar)} more barricades."
        )
    else:
        st.info("↔️ This change has **no significant impact** on clearance time or severity.")
