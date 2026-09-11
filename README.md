# Taapmaan — Heat Action Console

Ward-level extreme-heat early warning. Shifts the forecast from *what the weather
will be* to *what the weather will do to people*.

## Run it

**Whole stack** (backend + dashboard, one command):

```bash
./run.sh
```

Then open <http://localhost:8000>. API docs at <http://localhost:8000/docs>.
First boot creates the virtualenv, pulls Open-Meteo for all five cities and
starts a 30-minute refresh scheduler.

**Frontend only** — no Python needed, still fetches live weather in the browser:

```bash
open index.html
```

## Architecture

```
Open-Meteo ──► ingest.py ──► thermal.py ──► wards.py ──► FastAPI ──► dashboard
 (hourly)      peak-stress    WBGT/UTCI/     H3 cells +   /v1/*      index.html
               hour picker    HI/HTSI        Census join            (SVG, no deps)
                                  │
                              store.py ──► SQLite: alerts, broadcasts,
                                           subscribers, trigger_events
```

The dashboard tries three sources in order and always names which one it got:

| Pill | Meaning |
|---|---|
| `LIVE · TAAPMAAN API` | backend up, indices computed server-side |
| `LIVE · OPEN-METEO` | no backend, browser fetched and computed |
| `MAY PEAK SCENARIO` | no network at all, calibrated scenario |

Nothing breaks when a layer is missing — it degrades and says so. `heatguard.html` is the same page
without the `<html>/<head>/<body>` wrapper (that is the version published as a
hosted artifact). Edit `heatguard.html`, then regenerate `index.html` by wrapping
it — or just edit `index.html` directly if you prefer one file.

---

## 1. Data collection — what to pull and from where

Four layers. Only the first is what conventional forecasting uses; the other
three are what turn a forecast into a *health* forecast.

### Layer A — Weather (the input variables)

| Source | What you get | Access | Cadence |
|---|---|---|---|
| **Open-Meteo** `api.open-meteo.com/v1/forecast` | temp, RH, wind, **direct + diffuse shortwave radiation**, 7-day hourly, any lat/lon | free, no key, CORS-enabled | hourly |
| **IMD AWS / city bulletins** `mausam.imd.gov.in` | official station obs + the warning colour code you must stay consistent with | scrape / RTI-grade public data | 3-hourly |
| **ERA5-Land** (Copernicus CDS) | 1950–present reanalysis, 9 km | free API, needs registration | monthly batch |
| **NASA POWER** `power.larc.nasa.gov/api` | long-run solar irradiance + meteorology, no key | free | daily |
| **MOSDAC / INSAT-3D** | land surface temperature, insolation, 4 km | ISRO registration | 30 min |

> **Use Open-Meteo for the hackathon.** It is the only one that hands you
> `shortwave_radiation` and `windspeed_10m` in the same free call — and you need
> radiation for WBGT/UTCI. Everything else is a nice-to-have slide.

### Layer B — Static vulnerability (the multiplier)

**Already wired in.** `backend/data/census/india_census2011.json` carries real
Census of India 2011 figures for all five cities, retrieved 2026-09-10:

| City (municipal corporation) | Pop 2011 | Slum pop | Slum % | Literacy | Sex ratio |
|---|---:|---:|---:|---:|---:|
| Ahmedabad | 55,77,940 | 2,50,681 | 4.49 % | 88.29 % | 898 |
| Delhi (MCD) | 1,10,34,555 | 16,17,239 | 14.66 % | 87.59 % | 876 |
| Nagpur | 24,05,665 | 8,59,487 | **35.73 %** | 91.92 % | 963 |
| Chennai | 46,46,732 | 13,42,337 | 28.89 % | 90.18 % | 989 |
| Lucknow | 28,17,105 | 3,64,941 | 12.95 % | 82.50 % | 928 |

Plus the 60+ share of urban India, **7.7 %** (Census 2011; rural 8.4 %, national
8.2 %). The model uses **60+**, not 65+, because that is the Indian statistical
definition of elderly and the one the Census actually publishes.

**Why this matters.** Vulnerability now orders the cities the way the data does:
Ahmedabad 34.7 → Lucknow 38.3 → Delhi 38.1 → Chennai 42.0 → Nagpur 44.9. Nagpur
comes out most vulnerable because 35.7 % of it genuinely lives in slums. That is
a finding, not a random seed.

#### How ward values relate to the city figure

No public ward-level slum table exists for these cities, so ward values are
**dispersed around the real city anchor and average back to it exactly** —
population-weighted-mean-preserving. `GET /v1/census?city=nagpur` returns
`{"target": 35.73, "achieved": 35.73}` so you can prove it on stage.

#### Every field says where it came from

`GET /v1/census` returns a provenance tier for all nine demography fields, and
the ward panel marks each one `census` or `model` on screen:

| Tier | Meaning | Fields today |
|---|---|---|
| `ward_csv` | real ward-level table you supplied | none yet |
| `census2011:city` | real Census figure for this city | informal housing |
| `census2011:india_urban` | real Census figure for urban India | 60+ share |
| `modelled:ward-split` | city total real, ward split modelled | population |
| `modelled` | no source yet | outdoor workers, AC, canopy, capacity |

Partial coverage is reported honestly as `ward_csv:3/37, rest census2011:city` —
three CSV rows do not make a field measured for all 37 wards.

#### Dropping in real ward data

Copy `backend/data/census/wards_ahmedabad.csv.example` to
`wards_<city>.csv` and fill what you have. Columns:

```
ward_code, ward_name, population, elderly_60plus_pct, outdoor_worker_pct,
informal_housing_pct, ac_ownership_pct, canopy_cover_pct,
cooling_centres, hospital_beds, asha_workers
```

`ward_name` must match `data/cities.json` (case-insensitive). Any column you
omit falls back a tier; any ward you omit keeps its anchored value. No code
changes, no restart logic — the provenance map updates itself.

#### Still to source

| Field | Where it lives | Why not yet |
|---|---|---|
| Outdoor worker % | Census 2011 B-series | needs ward-level worker tables |
| AC ownership | NFHS-5 district factsheets | per-district PDFs, manual extraction |
| Canopy cover | Sentinel-2 NDVI (Earth Engine) | needs a GEE account + export |
| Ward population split | Census 2011 ward PCA | published per corporation, not centrally |

### Layer C — Health outcomes (the label you train on)

This is the hard one and the one that wins the round if you get *any* of it.

- **Civil Registration System (CRS)** annual all-cause deaths by district.
- **SRS Bulletin** crude death rate — use it to synthesise a daily baseline when
  you cannot get daily counts: `baseline_deaths/day = pop × CDR / 1000 / 365`.
- **NCDC / IDSP heat-stroke line list** (`ncdc.mohfw.gov.in`) — state-wise
  heat-stroke cases and deaths, published through summer.
- **108 EMRI ambulance dispatch logs** — the highest-resolution proxy that
  actually exists; some states publish aggregates.
- **Ahmedabad Heat Action Plan evaluations** (NRDC/IIPH, 2013–2018) — published
  all-cause mortality by day for 2010 and 2014. This is your validation set.

### Layer D — Geography

- Ward boundary GeoJSON: **DataMeet** (`github.com/datameet/indian_village_boundaries`),
  city open-data portals, or OSM `admin_level=9/10` via Overpass.
- Index everything on **Uber H3 resolution 7** (~1.2 km edge). Compute per hex,
  aggregate to ward. This is what makes it "hyper-local" rather than "city-level
  with a ward label stuck on".

---

## 2. The index stack (all of it is implemented in `heatguard.html`)

Run these in order. Each one is exact — no black box, and judges can audit them.

1. **Wet-bulb temperature** — Stull (2011) closed form.
2. **Globe temperature** — radiative gain vs. forced convection. Full form is
   Liljegren (1990); the browser uses a documented approximation.
3. **Mean radiant temperature** — ISO 7726 from the globe reading.
4. **WBGT (outdoor)** — `0.7·Tnw + 0.2·Tg + 0.1·Ta`, ISO 7243. Work/rest ratios
   key off this: >31 °C = stop outdoor work.
5. **Heat Index** — NWS Rothfusz regression with both adjustment terms.
6. **UTCI** — the full 6th-order polynomial of the UTCI operational procedure
   (Bröde et al. 2012), vendored from pythermalcomfort (MIT) into both the Python
   and JavaScript code. An earlier linear shortcut measured **2.5 °C mean error**
   against it on 13 years of real ERA5 days and has been removed.
7. **HTSI (0–100)** — the composite this problem statement is asking you to
   invent. Weighted: WBGT 0.34 · UTCI 0.26 · HI 0.16 · **overnight minimum 0.14**
   · **consecutive-day run 0.10**.

   The last two are the differentiator. Almost every team will average the three
   standard indices and stop. Overnight non-recovery and multi-day accumulation
   are the strongest predictors in the epidemiological literature, and no
   standard index contains them.

8. **Mortality Risk Index** — exposure–response, not a guess:
   ```
   excess    = max(0, HTSI − 45) / 10
   RR        = exp(0.10 × excess)          # +10% all-cause risk per 10 HTSI pts
   V         = 0.65 + vulnerability        # ward multiplier, 0.65–1.65
   deaths    = pop × CDR/1000/365 × (RR−1) × V
   ```
   Vulnerability weights: elderly 0.30, outdoor workers 0.25, informal housing
   0.20, no-AC 0.15, no-canopy 0.10.

---

## 3. The ML layer (built, trained, measured)

Two things ship: a **climatology layer** and a **learned forecaster**. Both run
off 13 years of ERA5 reanalysis pulled from Open-Meteo's archive API (free,
keyless) — 23,740 city-days across the five cities.

```bash
cd backend
python scripts/build_climate.py    # pull ERA5 2013-2025, derive climatology
python scripts/build_climate.py --append   # add every day since, up to yesterday
python scripts/train_model.py      # train D+1/+3/+5, write the model card
```

### Climatology — what counts as extreme *here*

34 °C WBGT is routine in Chennai and unheard of in Delhi in January, so a fixed
threshold is the wrong instrument. `build_climate.py` computes day-of-year
percentiles (p50/75/90/95/97/99) over a ±7-day ring, giving ~195 samples per
date. The dashboard shows the anomaly against the normal for that exact date,
and `GET /v1/climatology` returns the full distribution. This is what IMD-style
warnings actually key off, and it is statistics, not ML.

### Learned forecaster — honest numbers

`HistGradientBoostingRegressor`, predicting peak-stress-hour WBGT. **Temporal
split**: train 2013–2022, test 2023–2025, never shuffled — shuffling a time
series leaks tomorrow into today and inflates everything. Climatology features
are built from **training years only**, and the training climatology is shipped
inside the model bundle so inference sees exactly what the model was fitted on.

Measured on 5,480 held-out days:

| Horizon | Model MAE | Persistence | Climatology | Skill vs persistence | Skill vs climatology |
|---|---:|---:|---:|---:|---:|
| D+1 | **0.885 °C** | 0.950 | 1.307 | +6.8 % | +32.3 % |
| D+3 | **1.213 °C** | 1.418 | 1.307 | +14.5 % | +7.2 % |
| D+5 | **1.291 °C** | 1.609 | 1.307 | +19.8 % | +1.2 % |

It beats both baselines at all three horizons. Read the shape, not just the
wins: skill over persistence *grows* with horizon (persistence decays fast),
while skill over climatology *shrinks* — at D+5 the model is barely better than
saying "a normal day for this date." That is real predictability decay, and it
is the honest thing to point at.

### On the hottest days — read this before presenting

Averaged over all days the model wins. On each city's **hottest 10% of days** it
does not: it reads about 1.1–1.7 °C low (regression to the mean) and is less
accurate than simply assuming tomorrow = today. On days above 31 °C WBGT it catches
fewer than persistence. Error bands are published honestly in the model card
(`GET /v1/model`): at D+3, 80% of held-out days fall within ±1.9 °C. **The model
never drives a warning** — the ward map, alerts and actions come from the physics
forecast.

### What this model is not

**It forecasts from history only.** It never sees an NWP forecast, so it cannot
know a weather system is inbound. Where it disagrees with the physics path —
which uses the real Open-Meteo forecast — trust the physics path. This model is
a benchmark for what history alone can achieve, not a replacement for NWP.

The genuinely valuable ML here would be **bias-correcting NWP against station
observations**. That needs observation data we do not have. If your ML teammate
can get IMD AWS station records, that is the highest-value model to build next.

It also does **not** predict mortality. No daily death counts were available, so
the mortality layer stays parametric — see §2. Do not let anyone describe this
system as "an ML mortality model."

`GET /v1/model` returns the full model card: features, split, every metric above,
and all six caveats.

## 4. Suggested split for a 4-person team

| Role | Deliverable |
|---|---|
| **You — frontend** | this console. Already done. Spend your remaining time on the demo script. |
| Backend | FastAPI, 4 endpoints (the contract is in the *Alert API* panel), Postgres + PostGIS, APScheduler pulling Open-Meteo every 30 min |
| ML | **done** — climatology + D+1/3/5 forecaster with measured skill. Next: bias-correct NWP against IMD station obs |
| Data/GIS | ward GeoJSON → H3, Census + NFHS join, the vulnerability table |

---

## 5. Live data — two modes

The console runs in two modes, switched in the command bar:

| Mode | Source | Use it for |
|---|---|---|
| **Live** | real Open-Meteo fetch on load, per city, cached | proving the pipeline is real |
| **May peak** | calibrated peak-heatwave climatology | the dramatic part of the demo |

The fetch is keyless, CORS-enabled and needs no proxy:

```
GET https://api.open-meteo.com/v1/forecast
  ?latitude=23.03&longitude=72.58
  &daily=temperature_2m_max,temperature_2m_min
  &hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation
  &wind_speed_unit=ms&timezone=Asia%2FKolkata&forecast_days=5
```

For each of the 5 days the page walks all 24 hours, computes WBGT for each, and
picks the **peak-stress hour** — not the peak-temperature hour. In humid
conditions these are different hours, and the peak-stress one is what actually
matters. That hour's temperature, RH, wind and radiation drive every index; the
real hourly series also drives the diurnal WBGT curve.

Two details worth defending to a judge:

- **10 m → 2 m wind.** Open-Meteo reports wind at 10 m. WBGT and the globe
  balance are 2 m quantities, so the page converts with the neutral log law
  (`z0 = 0.01 m`, factor ≈ 0.75). UTCI is *defined* against the 10 m wind, so it
  keeps the raw value. Skipping this understates WBGT by roughly half a degree.
- **Heatwave run length** is counted from the live forecast against the IMD
  criterion — 40 °C for plains, 37 °C for coastal (Chennai).

**Failure is graceful and honest.** Timeout is 9 s; on any failure the page falls
back to the scenario and the source pill reads `OFFLINE · SCENARIO`. It never
shows stale or invented numbers as live.

> ⚠️ **The hosted artifact link cannot fetch.** The claude.ai artifact sandbox
> blocks cross-origin requests by policy, so that link always shows
> `OFFLINE · SCENARIO`. **Live mode works when you open `index.html` locally, or
> from any dev server or host you deploy to.** Demo from the local file.

### Rate limits and the forecast cache

Open-Meteo's free tier has daily, hourly and per-minute limits, counted per IP
address. When it answers 429 the backend stops calling, probes again with a single
request later, and reports the reason in `/health` and every response's
`provenance`. Every good forecast is also written to `backend/data/cache/`, so a
restart or a rate limit serves the last forecast, **labelled as cached with its
age**. With nothing cached, live mode shows the May-peak scenario labelled
"NO LIVE DATA · SCENARIO" — and refuses to issue live bulletins, live broadcasts or
live department actions from it.

### The API

Full interactive docs at `/docs` (FastAPI generates them from the code).

| Endpoint | Does |
|---|---|
| `GET /health` | liveness + per-city ingest age |
| `GET /v1/cities` | the five cities, with lat/lon and IMD thresholds |
| `GET /v1/forecast?city=&horizon=` | 37 ward cells: weather, indices, risk, demography |
| `GET /v1/forecast/timeline?city=` | 5-day city outlook — the dashboard strip |
| `GET /v1/ward/{code}?city=&horizon=` | one ward + its 24-hour WBGT curve |
| `GET /v1/census?city=` | which demography is real, and from where |
| `GET /v1/forecast/ml?city=&horizon=` | learned WBGT forecast + both baselines |
| `GET /v1/model` | model card: split, features, metrics, caveats |
| `GET /v1/climatology?city=&horizon=` | percentile vs 13-year local climate |
| `GET /v1/command?city=&mode=` | department action board at the operating level |
| `POST /v1/command/action` | move an action through its statuses (audited) |
| `POST /v1/command/reset-drill` | clear a drill — drill records only, no live equivalent |
| `GET /v1/gaps?city=&horizon=&mode=` | cooling, hospital and ASHA capacity gaps |
| `GET /v1/audit?city=&mode=` · `/v1/audit.csv` | audit trail, JSON or RTI-ready CSV |
| `GET /bulletin?city=&horizon=&mode=` | printable A4 daily heat bulletin (DRAFT) |
| `GET /v1/alerts?city=&horizon=` | auto-generated alert console items |
| `GET /v1/hap?city=&horizon=` | Heat Action Plan triggers, crossings logged |
| `POST /v1/broadcast` | record an advisory as a dry run (real sends are refused, see below) |
| `GET /v1/broadcast/preview` | exactly what a broadcast would say and reach — writes nothing |
| `GET /v1/broadcasts` | broadcast audit log |
| `POST /v1/subscribe` | register a number for ward-targeted alerts |
| `POST /v1/ingest/refresh` | force a re-pull |
| `GET /v1/config` | browser settings: the Google Maps key, if one is set |
| `POST /v1/auth/login` · `/logout` · `GET /v1/auth/me` | official sign-in (12-hour HttpOnly session cookie) |
| `GET`/`POST /v1/users` · `PATCH /v1/users/{username}` | account management (administrators only) |

Safety properties worth stating to a judge:

- **Broadcasts cannot escape, and are never faked.** `dry_run` defaults to `true`
  and the dashboard only sends dry runs. A real send (`dry_run:false`) must pass,
  in order: an operator token (`TAAPMAAN_BROADCAST_TOKEN`, sent as `X-Taapmaan-Token`;
  503 if unset, 401 if wrong), non-drill data (400), a live forecast (409) and a
  configured provider (503) — and then returns **501**, because delivery is not
  built: subscriber numbers are stored as one-way hashes, so there is no number to
  send to. Building it means storing numbers encrypted, a send queue and delivery
  receipts. Until then nothing is ever recorded as "queued" that will not arrive.
- **Targeting is real.** Recipients are the subscribers matching the audience
  ("all residents" = every audience), the targeted wards (plus city-wide
  subscribers) and the message language; other-language matches are reported,
  not counted. With no subscribers yet, reach is a census estimate over the
  targeted wards' population.
- **SMS cost is counted the way gateways bill.** °, •, — and Indic scripts force
  UCS-2 at 70 characters a part, so the standard advisory is 6 SMS parts, not 3.
  Operator overrides are capped at 670 characters (10 parts).
- **The approved text is the sent text.** The dashboard preview is rendered by
  `GET /v1/broadcast/preview`, the same code path as the send, and the delivery
  log confirms the recorded message matches it.
- **Phone numbers are never stored.** `POST /v1/subscribe` keeps a salted
  SHA-256 hash only. Set `TAAPMAAN_SALT` in production — the default is a known
  dev string.

### Street map (Google Maps or OpenStreetMap)

The ward map has a **Street map** view: every ward drawn at its real centre, sized by
population, coloured by the selected layer, with a card listing all of its figures.
Ward centres come from OpenStreetMap's geocoder (`backend/scripts/geocode_wards.py`, run
once at 1 request per 2 s; result in `data/ward_geo.json`, embedded in the page). Wards
it cannot place stay in the hex grid only. Boundaries are not drawn: there are no
official ward polygons in the app yet, and a made-up outline would mislead.

- **Google Maps:** create a *Maps JavaScript API* key in Google Cloud (billing must be
  enabled), restrict it to your domain, then add `GOOGLE_MAPS_API_KEY=...` to
  `backend/.env` (`run.sh` loads it) or to your host's environment. `GET /v1/config`
  hands it to the page. The browser sees this key by design; the domain restriction is
  what protects it.
- **Without a key:** the same view uses OpenStreetMap tiles through Leaflet. No account needed.

## 5b. Deploying it

Any Docker host works. Cheapest paths:

**Render** (free tier, blueprint included):

1. Push this folder to GitHub (a private repo is fine).
2. Render → **New → Blueprint** → pick the repo. `render.yaml` builds the Docker
   image and generates two secrets: `TAAPMAAN_SALT` and `TAAPMAAN_OPERATOR_TOKEN`.
3. Service → **Environment**: `TAAPMAAN_OPERATOR_TOKEN` is the password of the demo
   official accounts (`commissioner`, `control.room`, `health.officer`,
   `water.officer`, `collector`). Add `GOOGLE_MAPS_API_KEY` there too if you have one.

On the public link anyone can browse, run May-peak drills and send drill dry runs;
changing live records needs a signed-in official with the right role (administrator,
control-room operator, or an officer of that action's department; see
`backend/app/auth.py`), and the audit trail records who. Free instances sleep after 15 min idle (the first
visit then takes ~30 s), so open the URL once before you present. Their disk is
temporary: the SQLite action history resets on every restart or deploy. Attach a
Render disk, or move to Postgres, before relying on the audit trail.

**Railway / Fly / any container host**: the `Dockerfile` is self-contained.

```bash
docker build -t taapmaan . && docker run -p 8000:8000 taapmaan
```

**Ngrok**, if you just need a public URL for the demo:

```bash
./run.sh &
ngrok http 8000
```

Once deployed, the dashboard is served by the backend at `/`, and finds the API
on its own origin — no config, no CORS problem.

## 5c. Command centre — for city administration

The Monitor view tells a commissioner *what is happening*. The **Command centre**
tab tells them *who is doing what about it* — a Heat Action Plan is a
coordination problem across departments, and officials run on documents and
accountability, not dashboards.

**Department action board.** 20 standard actions across 11 departments (Health,
Labour, Discom, Water, Education, Police, 108 EMS…), each switching on at a
colour-coded level with a named owner and a deadline. Officers move them
Pending → Acknowledged → In progress → Done; overdue ones turn red and the tab
badge counts them from anywhere in the app.

- **Operating level** is the peak city HTSI over the next 72 hours, not today —
  a heat action plan exists to move *before* the peak.
- **The scheduler activates actions**, so a deadline starts when the level is
  crossed, not when someone happens to open the dashboard.
- The structure follows NDMA's city heat action plan guidance. **The specific
  actions, owners and deadlines are illustrative** — load your city's notified
  HAP before real use (`backend/app/sop.py`).

**Resource gaps.** Severe wards with no cooling centre; hospitals where projected
heat cases exceed 10 per 100 beds; days for ASHA workers to reach every resident
60+. Click any row to jump to that ward. Capacity figures are modelled until the
municipal register is joined, and the panel says so.

**Printable daily bulletin** (`/bulletin`). A4, black on white, no logos. Situation,
5-day outlook, highest-risk wards, department action status, public advisory in
English and the local language, and a signature block. Marked **DRAFT** until the
nodal officer signs — a machine-generated page must never pass for an issued
order. Chennai and Nagpur say plainly that a Tamil / Marathi template is missing
rather than substituting Hindi.

**Audit trail + CSV export.** Every activation, status change, broadcast, bulletin
and drill reset, with actor and time (UTC and IST). The CSV is for RTI replies and
the post-season review.

**Drills.** In *May peak* mode the command centre runs a drill: separate records,
a DRILL banner on screen and on the bulletin, and a reset button. Two hard rules
in the API: drill data **cannot be broadcast for real** (400), and there is **no
endpoint that wipes live records** — only drills reset.

**Security details that were tested:** operator names are escaped before
rendering (a `<img onerror>` name shows as text), and CSV cells beginning
`= + - @` are neutralised so the RTI export cannot run formulas in Excel.

**Not done — say so if asked:** there is no sign-in. Operator names are
self-declared, so the trail is a working log, not evidence, until SSO is added.

## 6. Demo script (3 minutes — rehearse it)

0. Open in **Live** mode. "This is real Open-Meteo data for Ahmedabad right now,
   pulled on page load — 37 ward cells, five days." Point at the source pill.
   Then switch to **May peak** for the rest of the demo.
1. On **Ahmedabad, +72 h**: "Traditional bulletin says 44 °C. Here is what
   that does to a body."
2. Switch the layer to **Night minimum**. "Eight wards never drop below 31 °C.
   No cooling window. This is the variable that actually kills, and no current
   Indian bulletin reports it."
3. Switch city to **Chennai** — 38.9 °C dry bulb, six degrees cooler than Delhi,
   and it lands within three points of Delhi's stress index. **This single click
   is your entire pitch.** Humidity closes a 6 °C gap.
4. Click the darkest hex → ward panel: 41% outdoor workers, 4% canopy,
   two cooling centres, projected excess deaths.
5. **Broadcast alert** → switch language to ગુજરાતી → Send. Watch the delivery log.
6. Open **Command centre** (still in May peak, so it's a drill). "At EMERGENCY,
   20 actions across 11 departments switched on, each with an owner and a
   deadline." Acknowledge one under your name; show it land in the audit trail.
7. Point at **Resource gaps** — "these severe wards have no cooling centre" —
   and click one to jump to it on the map.
8. **Print bulletin**. "This is what the nodal officer signs every morning. It's
   marked draft until they do." End there: the system produces the document
   the government actually runs on.

---

## 7. Known limits — state these before a judge finds them

- Weather is real. Slum share and 60+ share are real Census 2011. **Outdoor
  worker share, AC ownership, canopy cover and the ward population split are
  still modelled** — the ward panel and `/v1/census` label every one of them,
  so don't claim more than that on stage.
- Slum definitions differ between the Census, state slum boards and PMAY. Other
  published figures for the same city will not match. Cite the source in
  `india_census2011.json`, which is the one the numbers came from.
- No sign-in: command centre operator names are self-declared. Needs SSO before
  the audit trail can carry evidentiary weight.
- Heat Action Plan actions, owners and deadlines are illustrative, not a real
  city's notified plan.
- Ward cells are a synthetic H3 lattice, not real polygons. Swap in DataMeet
  GeoJSON to make it literal.
- UTCI now uses the full published polynomial. An earlier version shipped a linear
  shortcut documented here as "±1.5 °C"; that figure was an estimate, and when
  measured the shortcut was 2.5 °C off on average and changed the warning band on
  7% of days. It has been replaced.
- Globe temperature (WBGT's radiant term) is an approximation of Liljegren and has
  **not** been validated against a reference implementation.
- The mortality coefficient is parametric, calibrated to published Ahmedabad
  figures — not fitted to daily data.
