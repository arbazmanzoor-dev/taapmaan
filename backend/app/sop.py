"""Heat Action Plan standard operating procedures, by department and alert level.

The structure follows NDMA's guidance for city heat action plans: every line
department holds pre-agreed actions that switch on at a colour-coded alert
level, each with a named owner and a deadline. The SPECIFIC actions, owners and
deadlines below are illustrative -- replace them with your city's notified HAP
before any real use. Nothing here is copied from a particular city's plan.
"""
from __future__ import annotations

LEVELS = ["GREEN", "YELLOW", "ORANGE", "RED", "MAGENTA"]
LEVEL_NAME = {"GREEN": "Normal", "YELLOW": "Watch", "ORANGE": "Alert",
              "RED": "Warning", "MAGENTA": "Emergency"}

def rank(code: str) -> int:
    return LEVELS.index(code) if code in LEVELS else 0

DEPARTMENTS = [
    {"id": "dm",        "name": "Disaster Management Cell", "owner": "HAP Nodal Officer"},
    {"id": "health",    "name": "Health",                   "owner": "Chief Medical Officer"},
    {"id": "municipal", "name": "Municipal wards",          "owner": "Deputy Municipal Commissioner"},
    {"id": "labour",    "name": "Labour",                   "owner": "Deputy Labour Commissioner"},
    {"id": "power",     "name": "Power (Discom)",           "owner": "Superintending Engineer"},
    {"id": "water",     "name": "Water supply",             "owner": "Executive Engineer (Water)"},
    {"id": "education", "name": "Education",                "owner": "District Education Officer"},
    {"id": "transport", "name": "Transport",                "owner": "Depot Manager"},
    {"id": "police",    "name": "Police & traffic",         "owner": "DCP Traffic"},
    {"id": "ems",       "name": "Fire & 108 EMS",           "owner": "Chief Fire Officer"},
    {"id": "info",      "name": "Public information",       "owner": "Public Relations Officer"},
]
DEPT = {d["id"]: d for d in DEPARTMENTS}

# (id, department, activates-at level, deadline in hours, title, detail)
_RAW = [
    ("dm-bulletin",   "dm",        "YELLOW",  3,  "Issue daily heat bulletin",
     "Circulate the signed bulletin to every line department and the district collector."),
    ("dm-meeting",    "dm",        "ORANGE",  2,  "Convene HAP coordination meeting",
     "All department nodal officers; confirm readiness against this checklist."),
    ("dm-eoc",        "dm",        "RED",     1,  "Activate Emergency Operations Centre 24x7",
     "Staff the control room round the clock until the alert drops below RED."),
    ("hl-stock",      "health",    "YELLOW",  12, "Stock ORS, IV fluids and ice packs",
     "Every PHC, UHC and CHC to report stock levels by end of day."),
    ("hl-rooms",      "health",    "ORANGE",  6,  "Open heat-stroke rooms",
     "Cold-water immersion and cooling bays ready at CHCs and the district hospital."),
    ("hl-asha",       "health",    "ORANGE",  12, "ASHA door-to-door checks",
     "Visit residents aged 60+, bedridden and pregnant women in wards above HTSI 65."),
    ("hl-leave",      "health",    "RED",     4,  "Cancel non-emergency leave",
     "Medical and paramedical staff at all public facilities."),
    ("hl-idsp",       "health",    "RED",     24, "Daily heat-illness reporting",
     "Line list of heat-stroke cases and deaths to IDSP every 24 hours."),
    ("mu-water",      "municipal", "YELLOW",  8,  "Drinking water and ORS points",
     "Markets, bus stands, construction clusters and major junctions."),
    ("mu-cooling",    "municipal", "ORANGE",  4,  "Open cooling centres",
     "Every ward above HTSI 65; power backup and drinking water mandatory."),
    ("mu-parks",      "municipal", "RED",     8,  "Extend shaded public spaces",
     "Keep parks, gardens and community halls open through the afternoon."),
    ("lb-break",      "labour",    "ORANGE",  6,  "Mandatory work breaks 12:00-16:00",
     "Construction sites, brick kilns and MGNREGA-type works; site inspections."),
    ("lb-suspend",    "labour",    "RED",     4,  "Suspend outdoor work 11:00-17:00",
     "Issue the order and deploy inspectors to high-density outdoor-work wards."),
    ("pw-outage",     "power",     "ORANGE",  6,  "Defer planned outages",
     "Priority feeders for hospitals and cooling centres; no maintenance shutdowns."),
    ("wt-supply",     "water",     "ORANGE",  8,  "Uninterrupted supply to deficit wards",
     "Tankers to wards with informal housing above 30% and no piped supply."),
    ("ed-timing",     "education", "RED",     12, "Morning-only school sessions",
     "Cancel outdoor assemblies and sports; move exams out of 11:00-16:00."),
    ("tr-depots",     "transport", "ORANGE",  12, "Water and shade at depots and stops",
     "Drinking water at every depot; shade nets at high-footfall stops."),
    ("po-traffic",    "police",    "RED",     6,  "Protect traffic personnel",
     "Shade canopies, water and duty rotation for pointsmen at open junctions."),
    ("em-108",        "ems",       "RED",     4,  "Pre-position 108 ambulances",
     "Stage units near the highest-risk wards during 11:00-17:00."),
    ("in-advisory",   "info",      "YELLOW",  4,  "Publish public advisory",
     "Press note, social media and FM radio in English and the local language."),
]

ACTIONS = [
    {"id": i, "department": d, "department_name": DEPT[d]["name"],
     "owner": DEPT[d]["owner"], "level": lv, "level_name": LEVEL_NAME[lv],
     "deadline_hours": h, "title": t, "detail": x}
    for (i, d, lv, h, t, x) in _RAW
]
ACTION = {a["id"]: a for a in ACTIONS}

STATUSES = ["pending", "acknowledged", "in_progress", "done"]

CAVEAT = ("Structure follows NDMA's city heat action plan guidance (department roles "
          "by colour-coded alert level). Specific actions, owners and deadlines are "
          "illustrative -- replace them with your city's notified Heat Action Plan.")
