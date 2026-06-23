"""
build_map_data.py
-----------------
Runs the exact same train/test split as the notebook (random_state=42),
gets real model predictions for the test set, and saves map_incidents.json.

Also seeds gridlock_feedback.db with the resolved test rows so the
feedback loop starts with real data.

Run: python build_map_data.py
"""
import pandas as pd, numpy as np, pickle, json, os, sys
from sklearn.model_selection import train_test_split

BASE = os.path.dirname(os.path.abspath(__file__))
CSV  = os.path.join(BASE, "Astram event data_anonymized - Astram event data_anonymizedb40ac87 (1).csv")

if not os.path.exists(CSV):
    sys.exit(f"CSV not found at: {CSV}")

print("Loading dataset...")
df = pd.read_csv(CSV)

for col in ['start_datetime','end_datetime','closed_datetime','resolved_datetime']:
    df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)

end_best = df['closed_datetime'].fillna(df['end_datetime']).fillna(df['resolved_datetime'])
df['duration_minutes_clean'] = (end_best - df['start_datetime']).dt.total_seconds() / 60
df.loc[df['duration_minutes_clean'] <= 0, 'duration_minutes_clean'] = np.nan
df['hour']    = df['start_datetime'].dt.hour
df['month']   = df['start_datetime'].dt.month
df['weekday'] = df['start_datetime'].dt.day_name()

FEATURE_COLS = ['event_type','event_cause','priority','requires_road_closure',
                'zone','junction','corridor','veh_type','hour','month','weekday']
CAT_COLS     = ['event_type','event_cause','priority','requires_road_closure',
                'zone','junction','corridor','veh_type','weekday']

q99 = df['duration_minutes_clean'].quantile(0.99)
d   = df[df['duration_minutes_clean'].between(1, q99)].copy()
d['log_dur'] = np.log1p(d['duration_minutes_clean'])

features = [f for f in FEATURE_COLS if f in d.columns]
X = d[features].copy()
for c in CAT_COLS:
    if c in X.columns:
        X[c] = X[c].astype('category')
y = d['log_dur']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Test set: {len(X_test)} rows")

print("Loading models...")
with open(os.path.join(BASE, 'model_p50.pkl'), 'rb') as f: m50 = pickle.load(f)
with open(os.path.join(BASE, 'model_p90.pkl'), 'rb') as f: m90 = pickle.load(f)

pred50 = np.expm1(m50.predict(X_test))
pred90 = np.expm1(m90.predict(X_test))
actual = np.expm1(y_test)

def impact_class(pri, clos, minutes):
    dbk = 1 if minutes <= 30 else (2 if minutes <= 120 else 3)
    s   = pri + clos + dbk
    if s <= 3:   return 'Low'
    elif s <= 5: return 'Medium'
    elif s <= 7: return 'High'
    else:        return 'Critical'

# Assemble test rows with predictions + actual
test_rows = d.loc[X_test.index].copy()
test_rows['pred_p50']   = pred50
test_rows['pred_p90']   = pred90
test_rows['actual_min'] = actual.values
test_rows['pri_n']      = test_rows['priority'].map({'Low':1,'Medium':2,'High':3}).fillna(2)
test_rows['clos_n']     = np.where(test_rows['requires_road_closure'] == True, 2, 0)
test_rows['pred_impact']   = [impact_class(r.pri_n, r.clos_n, r.pred_p50)  for _, r in test_rows.iterrows()]
test_rows['actual_impact'] = [impact_class(r.pri_n, r.clos_n, r.actual_min) for _, r in test_rows.iterrows()]
test_rows['abs_error']     = (test_rows['pred_p50'] - test_rows['actual_min']).abs()

# Keep only valid Bengaluru lat/lon
geo_ok = (
    test_rows['latitude'].between(12.7, 13.3) &
    test_rows['longitude'].between(77.3, 77.8)
)
test_rows = test_rows[geo_ok].copy()
print(f"Rows with valid Bengaluru coordinates: {len(test_rows)}")

# Sample 40 resolved + 10 active  (stratify by predicted impact for variety)
resolved_sample = (
    test_rows.groupby('pred_impact', group_keys=False)
    .apply(lambda g: g.sample(min(len(g), 10), random_state=42))
    .head(40)
)
active_sample = (
    test_rows[~test_rows.index.isin(resolved_sample.index)]
    .sample(min(10, len(test_rows) - len(resolved_sample)), random_state=7)
)
print("Impact distribution (resolved):", resolved_sample['pred_impact'].value_counts().to_dict())
print(f"Active incidents: {len(active_sample)}")

# Build JSON list
def make_inc(r, status):
    inc = {
        'lat':          round(float(r['latitude']), 6),
        'lon':          round(float(r['longitude']), 6),
        'cause':        str(r['event_cause'])  if pd.notna(r.get('event_cause'))  else 'others',
        'priority':     str(r['priority'])     if pd.notna(r.get('priority'))     else 'High',
        'zone':         str(r['zone'])         if pd.notna(r.get('zone'))         else 'Unknown',
        'corridor':     str(r['corridor'])     if pd.notna(r.get('corridor'))     else 'Non-corridor',
        'junction':     str(r['junction'])     if pd.notna(r.get('junction'))     else None,
        'impact':       r['pred_impact'],
        'pred_p50':     round(float(r['pred_p50']), 1),
        'pred_p90':     round(float(r['pred_p90']), 1),
        'pred_clearance': f"{int(r['pred_p50'])} min",
        'road_closure': bool(r['requires_road_closure']),
        'hour':         int(r['hour']),
        'month':        int(r['month']),
        'weekday':      str(r['weekday']),
        'status':       status,
    }
    if status == 'resolved':
        inc['actual_minutes']  = round(float(r['actual_min']), 1)
        inc['actual_impact']   = r['actual_impact']
        inc['abs_error']       = round(float(r['abs_error']), 1)
        inc['actual_clearance']= f"{int(r['actual_min'])} min"
    else:
        inc['actual_minutes']  = None
        inc['actual_impact']   = None
        inc['abs_error']       = None
        inc['actual_clearance']= None
    return inc

incidents = (
    [make_inc(r, 'resolved') for _, r in resolved_sample.iterrows()] +
    [make_inc(r, 'active')   for _, r in active_sample.iterrows()]
)

out = os.path.join(BASE, 'map_incidents.json')
with open(out, 'w') as f:
    json.dump(incidents, f, indent=2)
print(f"\nSaved {len(incidents)} incidents -> map_incidents.json")

errors = [i['abs_error'] for i in incidents if i['abs_error'] is not None]
print(f"Median absolute error (map data): {round(float(np.median(errors)), 1)} min")
print(f"Mean absolute error  (map data): {round(float(np.mean(errors)), 1)} min")

# ── Seed feedback_store with the resolved test rows ──────────────────────────
print("\nSeeding feedback database with resolved test rows...")
sys.path.insert(0, BASE)
import feedback_store as fs
fs.init_db()

# Check how many seed rows already exist — don't re-seed if already done.
import sqlite3 as _sqlite3
_conn = _sqlite3.connect(fs.DB_PATH)
existing_seed_count = _conn.execute(
    "SELECT COUNT(*) FROM predictions WHERE event_id LIKE 'seed_%'"
).fetchone()[0]
_conn.close()

if existing_seed_count > 0:
    print(f"DB already has {existing_seed_count} seed rows — skipping re-seed to preserve existing predictions.")
    print("(Delete gridlock_feedback.db and re-run this script if you want a fresh seed.)")
else:
    all_resolved = [make_inc(r, 'resolved') for _, r in test_rows.iterrows()
                    if r['pred_impact'] is not None]

    import uuid
    seeded = 0
    for inc in all_resolved:
        # Use a deterministic event_id based on row index so re-runs don't duplicate
        row_idx = inc.get('_row_idx', seeded)
        event_id = f"seed_{abs(hash((inc['lat'], inc['lon'], inc['pred_p50']))) % (10**8):08x}"
        event = {
            'event_type':           'unplanned',
            'event_cause':          inc['cause'],
            'priority':             inc['priority'],
            'requires_road_closure':inc['road_closure'],
            'zone':                 inc['zone'],
            'corridor':             inc['corridor'],
            'hour':                 inc['hour'],
            'month':                inc['month'],
            'weekday':              inc['weekday'],
        }
        fs.log_prediction(event_id, event, inc['pred_p50'], inc['pred_p90'], inc['impact'])
        fs.record_actual(event_id, inc['actual_minutes'])
        seeded += 1

    print(f"Seeded {seeded} records into feedback DB")
report = fs.accuracy_report()
print("\nInitial accuracy report:")
for k, v in report.items():
    print(f"  {k}: {v}")

fs.take_accuracy_snapshot()
print("\nInitial accuracy snapshot saved.")
print("\nDone! Run: streamlit run app.py")
