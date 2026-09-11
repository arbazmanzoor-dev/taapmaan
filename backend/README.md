# Taapmaan backend

FastAPI + SQLite. No external services beyond Open-Meteo.

```
app/
  thermal.py   pure physics — WBGT, UTCI, Heat Index, HTSI, mortality model.
               Every function cites its source. No I/O, trivially unit-testable.
  wards.py     37 H3-style cells per city: demography, urban heat island
               downscaling, per-cell indices. Same FNV-1a seed as the frontend,
               so a ward's numbers match whichever side computed them.
  ingest.py    Open-Meteo client. Picks the peak-STRESS hour per day, not the
               peak-temperature hour. Last good forecast persisted to data/cache/ and
               served as stale (labelled) on restart or rate limit; pauses on 429.
  census.py    Census 2011 anchors, ward-CSV override, per-field provenance.
               Three tiers: ward_csv > census2011 > modelled, and every field
               reports which one it used. Partial CSV coverage is stated as
               'ward_csv:3/37, rest census2011:city' rather than rounded up.
  sop.py       Heat Action Plan catalogue: 20 actions x 11 departments, each
               with activation level, owner and deadline. ILLUSTRATIVE --
               replace with your city's notified plan.
  bulletin.py  Printable A4 daily heat bulletin, marked DRAFT until signed.
  store.py     SQLite: alerts, broadcasts, subscribers, trigger_events,
               actions (keyed by city + live/drill mode), audit.
  main.py      FastAPI routes, APScheduler job, advisory templates (EN/HI/GU).
data/
  cities.json  five cities, 185 wards, lat/lon, IMD heatwave thresholds
  census/
    india_census2011.json      real Census 2011 figures + source URLs
    wards_<city>.csv           optional: your real ward table, overrides all
    wards_ahmedabad.csv.example documented column list
```

## Run

```bash
../run.sh                  # from the repo root, creates the venv for you
```

or manually:

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn app.main:app --reload --port 8000
```

## Where to plug in real data

| Swap this | For this | Effect |
|---|---|---|
| drop `data/census/wards_<city>.csv` | your ward table | any field becomes real, no code change |
| `wards._attrs()` | NFHS-5 / Earth Engine join | the last modelled fields become real |
| `wards.CELLS` | ward GeoJSON → H3 r7 | cells become real polygons |
| `thermal.globe_temp_c()` | Liljegren (1990) solver | exact WBGT |
| `thermal.mortality()` | DLNM fitted to daily deaths | fitted, not parametric |

Nothing else has to change — every caller goes through these functions.
