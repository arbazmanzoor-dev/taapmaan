<!-- Slide number: 1 -->

![sih_logo_deck.png](Picture2.jpg)
SMART INDIA HACKATHON 2026
Problem Statement ID – SIH26083
Problem Statement Title – Extreme Heatwave Early Warning and Human Thermal Stress Index
Theme – Disaster Management
PS Category – Software
Organisation – Ministry of Earth Sciences (MoES)
Team ID – ‹Team ID›
Team Name – ‹TEAM NAME›

HTSI
82

Tapman  ·  Heat Action Console
From what the weather will be — to what it will do to people.

### Notes:
Problem SIH26083 from the Ministry of Earth Sciences: heat warnings in India key off air temperature, but humidity, wind and sun decide what heat does to a body. Tapman turns the forecast into ward-level thermal stress, projected deaths and hospital load, and into actions each department owns. Replace ‹Team Name› and ‹Team ID› (Find & Replace) before submitting.

<!-- Slide number: 2 -->
IDEA: TAPMAN

![sih_logo_deck.png](Picture3.jpg)
‹TEAM NAME›
THE GAP — SAME THERMOMETER, DIFFERENT DANGER

![hero.jpg](Picture23.jpg)
Both cards: 40 °C air temperature, afternoon sun (800 W/m²), light breeze.

40 °C  ·  20 % humidity
40 °C  ·  70 % humidity
30.6 °C WBGT
39.2 °C WBGT
Heat Index 39 °C  ·  wet-bulb 22.7 °C
Heat Index 72 °C  ·  wet-bulb 34.9 °C
Below 31 °C — work with rest breaks
Above 31 °C — suspend outdoor work
WHY TODAY'S WARNINGS MISS IT

Air temperature only — humidity, wind and sun are ignored
District-level — misses the heat-island gap between wards
No health translation — '40 °C' does not say who ends up in hospital
No trigger — nothing tells departments what to do, or checks they did
Tapman console · Ahmedabad, May-peak drill · 37 ward cells coloured by HTSI
HOW IT WORKS — END TO END

1  Sense
2  Compute
3  Localise
4  Predict
5  Alert
6  Act
Open-Meteo hourly forecast, ERA5 history, Census 2011
WBGT, UTCI and Heat Index at the peak-stress hour
37 ward cells per city with heat-island downscaling
HTSI, excess deaths, ED load; D+1…D+5 learned forecast
Ward map, auto alerts, SMS/WhatsApp in EN · HI · GU
20 HAP actions with owners, deadlines, bulletin, audit

@SIH Idea submission- Template
2

### Notes:
Same 40 °C: at 20 % humidity WBGT is 30.6 °C; at 70 % it is 39.2 °C, wet-bulb 34.9 °C. That gap is the whole problem statement. Traditional warnings cannot see it. Tapman computes WBGT, UTCI and Heat Index for every ward, adds overnight non-recovery and multi-day accumulation into one Human Thermal Stress Index, links it to mortality, and hands departments actions.

<!-- Slide number: 3 -->
TECHNICAL APPROACH

![sih_logo_deck.png](Picture3.jpg)
‹TEAM NAME›
TECH STACK
ARCHITECTURE
WHAT OFFICIALS GET

Open-Meteo forecast + ERA5 archive · Census 2011 · NDMA HAP structure

![command.jpg](Picture51.jpg)
Data
Sources   Open-Meteo hourly · ERA5 archive · Census 2011

ingest.py   peak-stress-hour picker · 10-day history · 30-min scheduler
Stull wet-bulb · ISO 7243 WBGT · UTCI (Bröde 2012) · NWS Heat Index
Science

thermal.py   WBGT · UTCI · Heat Index · wet-bulb · HTSI
scikit-learn gradient boosting · 13 years of ERA5 · temporal split
ML
Command centre — actions, deadlines, resource gaps

wards.py + census.py   37 cells per city · heat-island downscaling · provenance

![bulletin.jpg](Picture53.jpg)

![broadcast.jpg](Picture54.jpg)
Python · FastAPI · SQLite · APScheduler · httpx
Backend

ml.py   D+1/3/5 gradient boosting · 13-year climatology
HTML/CSS/JS · SVG hex map · light & dark · no framework
Frontend

FastAPI + SQLite   24 API operations · actions · audit · subscribers
REST API + webhook · SMS/WhatsApp via MSG91/Twilio, dry-run by default
Alerts
Dashboard
Bulletin
Broadcast
Webhook
Daily bulletin (draft)
Gujarati WhatsApp advisory

Safe by design: drills can't reach the public, broadcasts are dry-run by default, and no endpoint can wipe live records.
Docker · Render blueprint · one-command run.sh
Deploy

HTSI (0–100) = 0.34·WBGT + 0.26·UTCI + 0.16·HI + 0.14·night minimum + 0.10·heat-run days, each normalised
Excess deaths = baseline × (e^(0.10·(HTSI−45)/10) − 1) × ward vulnerability

@SIH Idea submission- Template
3

### Notes:
Every index is a published formula — Stull 2011 wet-bulb, ISO 7243 WBGT, UTCI per Bröde 2012, NWS Heat Index — so a reviewer can audit the arithmetic. The backend pulls Open-Meteo every 30 minutes, finds each day's peak-STRESS hour rather than the hottest hour, downscales to 37 ward cells with Census 2011 anchors, and serves 24 documented API operations. Officials get the command centre, a signed bulletin and vernacular advisories.

<!-- Slide number: 4 -->
FEASIBILITY AND VIABILITY

![sih_logo_deck.png](Picture3.jpg)
‹TEAM NAME›

### Chart: Forecast error (MAE, °C) — lower is better

| Category | Tapman model | Persistence | Climatology |
|---|---|---|---|
| D+1 | 0.885 | 0.95 | 1.307 |
| D+3 | 1.213 | 1.418 | 1.307 |
| D+5 | 1.291 | 1.609 | 1.307 |FEASIBILITY — ALREADY BUILT AND RUNNING

5
185
23,740
cities on live forecasts
ward cells with Census 2011 anchors
city-days of ERA5 training data

24
20 × 11
0
API operations, documented at /docs
HAP actions × departments
paid APIs or licences
Held out in time: trained 2013–22, tested on 5,480 city-days of 2023–25. Skill vs persistence +6.8% / +14.5% / +19.8%.
SWOT
VIABILITY — PATH TO ADOPTION

Strengths
Weaknesses
1
2
3
4
Physics-based, auditable indices
Ward-level and mortality-linked
Open data; runs on one small server
Ward splits and capacity partly modelled
Mortality model parametric, not fitted
No sign-in yet
Pilot
Localise
Harden
Scale
One corporation's heat season, drills first
Ward boundaries, Census join, capacity register
Government SSO, state data-centre hosting
Every city with a Heat Action Plan

Opportunities
Threats
Any city = one config entry + Census join
Bias-correct with IMD station data
Link 108 and hospital feeds
Daily mortality data not public
Alert fatigue if thresholds untuned
SOPs need official sign-off

Running cost: open data and an open-source stack in one container. The only per-use cost is the SMS/WhatsApp gateway, billed per message — and every broadcast is a dry run until credentials are added.

@SIH Idea submission- Template
4

### Notes:
This is not a mock-up: five cities run on live forecasts today. The learned forecaster is trained on 13 years of ERA5 and tested on years it never saw; it beats both honest baselines at every horizon. Point at the shape, not the wins: skill over persistence grows with horizon, skill over climatology shrinks — predictability decays. The SWOT names our real gaps: modelled capacity data, a parametric mortality model, no sign-in yet.

<!-- Slide number: 5 -->
IMPACT AND BENEFITS

![sih_logo_deck.png](Picture3.jpg)
‹TEAM NAME›
WHY IT MATTERS — EVIDENCE
WHO BENEFITS

BENEFITS

1,344
Earlier — acts on the 72-hour peak, not the day of
Targeted — ward cells, not whole districts
Accountable — every action owned, timed, audited
Inclusive — advisories in English, Hindi, Gujarati
Affordable — open data, open-source, one server
Municipal
Commissioner
excess deaths in Ahmedabad in the May 2010 heat wave — all-cause mortality up 43.1%
Disaster
Mgmt Cell
Health dept
& hospitals
Azhar et al., PLOS ONE, 2014
≈1,190
Tapman
ASHA & 108
field staff
Labour
department
deaths avoided per year after Ahmedabad's Heat Action Plan (2014–15 vs 2007–10)

FUTURE SCOPE

Bias-correct forecasts with IMD station data
Real ward boundaries on an H3 grid
Government SSO; state data-centre hosting
Fit mortality to real daily deaths (DLNM)
Tamil, Marathi and more advisory languages
IVR and cell-broadcast delivery
Hess et al., J. Environ. Public Health, 2018

Heat action plans save lives. Tapman makes them ward-level, forecast-led and accountable.
Outdoor
workers
Power & water
utilities
Elderly &
vulnerable

@SIH Idea submission- Template
5

### Notes:
The evidence is Indian and local: the 2010 Ahmedabad heat wave killed 1,344 more people than normal, and after the city's heat action plan an estimated 1,190 deaths a year were avoided. Plans work — but they are city-wide, temperature-triggered and paper-driven. Tapman makes them ward-level, forecast-led and accountable, for every department in this circle.

<!-- Slide number: 6 -->
RESEARCH AND REFERENCES

![sih_logo_deck.png](Picture3.jpg)
‹TEAM NAME›

### Chart: Peak daily WBGT by city, °C — ERA5 2013–25

| Category | base | 5th–50th percentile | 50th–95th percentile |
|---|---|---|---|
| Delhi | 16.5 | 11.0 | 5.5 |
| Lucknow | 17.9 | 10.5 | 5.0 |
| Ahmedabad | 21.3 | 7.6 | 3.7 |
| Nagpur | 22.5 | 5.9 | 4.0 |
| Chennai | 25.6 | 4.3 | 3.1 |REFERENCES

| Source | Used for | Link |
| --- | --- | --- |
| Azhar et al. (2014), PLOS ONE 9(3): e91831 | Ahmedabad 2010 excess deaths | doi.org/10.1371/journal.pone.0091831 |
| Hess et al. (2018), J. Environ. Public Health | Heat Action Plan impact | doi.org/10.1155/2018/7973519 |
| Stull (2011), J. Appl. Meteor. Climatol. 50: 2267–69 | Wet-bulb formula | doi.org/10.1175/JAMC-D-11-0143.1 |
| Bröde et al. (2012), Int. J. Biometeorol. 56: 481–94 | UTCI procedure | doi.org/10.1007/s00484-011-0454-1 |
| ISO 7243:2017 | WBGT heat-stress index | standard (no public link) |
| Rothfusz (1990), NWS Technical Attachment SR 90-23 | Heat Index regression | standard (no public link) |
| NDMA heat-wave action plan guidelines (2016; rev. 2017, 2019) | HAP department structure | ndma.gov.in/images/guidelines/guidelines-heat-wave.pdf |
| Open-Meteo forecast & historical (ERA5) APIs | Live weather, 13-yr training data | open-meteo.com |
| Census of India 2011 city tables; PIB (PRID 1847436) | Slum share; 7.7% urban 60+ | census2011.co.in · pib.gov.in |
Bars run 5th→95th percentile (median at the colour change). Floors differ by 9.1 °C across cities: one national threshold cannot fit all.
EXISTING APPROACHES VS TAPMAN

| Approach | Measures | Scale | Health link | Acts |
| --- | --- | --- | --- | --- |
| IMD heat-wave warnings | Air temperature vs thresholds | District | No | Manual |
| City Heat Action Plans | Temperature triggers | City | Indirect | Manual |
| WBGT meters | WBGT at one site | Point | No | No |
| Tapman | WBGT + UTCI + HI + night + run → HTSI | Ward | Deaths & ED load | Auto + audited |
Every figure in this deck is computed by the Tapman code from these sources. Ward-level demography and capacity are partly modelled; the app labels each field's source (see /v1/census).

See it live: ./run.sh → localhost:8000 · API docs at /docs
Repo / demo video: ‹add link›

@SIH Idea submission- Template
6

### Notes:
Every formula comes from a peer-reviewed or standards source, and every number on these slides is computed by the code from these datasets. The chart is from our 13 years of ERA5 data: local climate defines what 'extreme' means, which is why Tapman scores each city against its own climatology. Replace ‹add link› with your repo or demo video before submitting.
