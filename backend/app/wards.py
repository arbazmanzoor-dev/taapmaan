"""Ward cells: demography, urban heat island downscaling, per-cell indices.

The pseudo-random draws use the same FNV-1a seed as the frontend, so a ward's
demography is byte-identical whether it was computed here or in the browser.
Replace `_attrs` with a Census/NFHS join and everything downstream still holds.
"""
from __future__ import annotations
import json, math, pathlib
from . import census, thermal as T

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "cities.json"
CITIES: dict = json.loads(DATA.read_text(encoding="utf-8"))

def seed(s: str) -> float:
    """FNV-1a, 32-bit, normalised to [0,1). Mirrors the frontend exactly."""
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h / 4294967295

def rnd(s: str, lo: float, hi: float) -> float:
    return lo + seed(s) * (hi - lo)

def jround(x: float) -> int:
    """JS Math.round: half away from zero upward, not banker's rounding."""
    return math.floor(x + 0.5)

def lattice(r: int):
    """Axial hex lattice. Production indexes on Uber H3 resolution 7 (~1.2 km)."""
    out = [(q, rr) for q in range(-r, r + 1) for rr in range(-r, r + 1)
           if (abs(q) + abs(q + rr) + abs(rr)) / 2 <= r]
    return sorted(out, key=lambda c: (c[1], c[0]))

CELLS = lattice(3)  # 37 cells

def day_record(key: str, d: int, live: dict | None) -> dict:
    """Driving weather for one day: live forecast if present, else the
    calibrated May peak-heatwave scenario."""
    c = CITIES[key]
    if live and d < len(live["days"]):
        return live["days"][d]
    b, dt = c["base"], c["trend"][d]
    return {"tmax": b["tmax"] + dt, "tmin": b["tmin"] + dt * 0.55,
            "rh": T.clamp(b["rh"] - dt * 0.7, 5, 97), "wind": b["wind"],
            "solar": b["solar"] - b["aod"] * 32, "hour": 15, "hourly": None}

def run_length(key: str, live: dict | None) -> int:
    """Consecutive forecast days meeting the IMD heatwave criterion."""
    c = CITIES[key]
    if not live:
        return c["run"]
    n = 0
    for d in live["days"]:
        if d["tmax"] >= c["hwT"]:
            n += 1
        else:
            break
    return n

def _attrs(key: str, name: str, pop: int) -> dict:
    """Fields with no source yet. Replace these with a real join and the
    provenance map in census.py flips them from 'modelled' automatically."""
    k = f"{key}|{name}"
    return {
        "green": rnd(k + "|g", 1.5, 34),
        "outdoor": rnd(k + "|o", 9, 44),
        "ac": rnd(k + "|a", 3, 68),
        "cooling_centres": max(0, jround(rnd(k + "|c", 0, 6))),
        "hospital_beds": jround(pop / 1000 * rnd(k + "|b", 0.4, 2.6)),
        "asha_workers": jround(pop / 2500 * rnd(k + "|as", 0.7, 1.4)),
    }

def demography(key: str) -> tuple[list[dict], dict]:
    """Per-ward demography, best available tier per field.

    Informal housing is anchored to this city's real Census 2011 slum share and
    the 60+ share to real urban-India Census 2011 -- ward values are dispersed
    around those anchors and average back to them exactly. A ward CSV in
    data/census/ overrides any field it supplies.
    """
    c = CITIES[key]
    names = c["wards"]

    shares = [rnd(n + "|pop", 0.55, 1.65) for n in names]
    tot = sum(shares)
    pops = [jround(c["pop"] * s / tot) for s in shares]

    rows = census.ward_csv(key)
    has_csv = bool(rows)
    if has_csv:
        for i, n in enumerate(names):
            r = rows.get(n.lower())
            if r and "population" in r:
                pops[i] = int(r["population"])

    facts = census.CITY.get(key, {})
    slum_target = facts.get("slum_pct", 20.0)
    eld_target = census.NATIONAL["elderly_60plus_pct"]["value"]

    informal = census.anchored(names, pops, slum_target, 0.85, 0.4, 92.0, seed, f"{key}|informal")
    elderly = census.anchored(names, pops, eld_target, 0.32, 3.0, 17.0, seed, f"{key}|elderly")

    INTS = {"cooling_centres", "hospital_beds", "asha_workers", "population"}
    coverage: dict[str, int] = {}
    out = []
    for i, n in enumerate(names):
        a = _attrs(key, n, pops[i])
        a["population"] = pops[i]
        a["informal"] = informal[i]
        a["elderly"] = elderly[i]
        r = rows.get(n.lower()) if has_csv else None
        if r:
            for field, v in r.items():
                coverage[field] = coverage.get(field, 0) + 1
                if field != "population":
                    a[field] = int(v) if field in INTS else v
        out.append(a)

    meta = {
        "provenance": census.provenance(coverage, len(names)),
        "anchors": {
            "informal_housing_pct": {
                "target": slum_target,
                "achieved": round(census.achieved_mean(informal, pops), 3),
                "source": "ward_csv" if has_csv else "census2011:city",
            },
            "elderly_60plus_pct": {
                "target": eld_target,
                "achieved": round(census.achieved_mean(elderly, pops), 3),
                "source": "ward_csv" if has_csv else "census2011:india_urban",
            },
        },
        "ward_csv_loaded": has_csv,
        "ward_csv_coverage": {f: f"{c}/{len(names)}" for f, c in sorted(coverage.items())},
        "census": census.city_facts(key),
    }
    return out, meta

def build(key: str, horizon: int, live: dict | None) -> list[dict]:
    c = CITIES[key]
    D = day_record(key, horizon, live)
    run = run_length(key, live)

    demo, meta = demography(key)

    out = []
    for i, name in enumerate(c["wards"]):
        k = f"{key}|{name}"
        a = demo[i]
        pop = a["population"]

        # Urban heat island: built fraction drives it up, canopy pulls it down.
        # The night-time island runs ~45 % hotter than the daytime one.
        uhi = T.clamp(2.9 * (1 - a["green"] / 36) + 1.6 * (a["informal"] / 60) - 0.7, -0.6, 4.3)

        tmax = D["tmax"] + uhi
        tmin = D["tmin"] + uhi * 1.45
        rh = T.clamp(D["rh"] + rnd(k + "|h", -9, 10), 6, 96)
        v10 = T.clamp(D["wind"] * rnd(k + "|w", 0.55, 1.35) - a["informal"] / 120, 0.4, 11)
        v2 = T.w10to2(v10)
        solar = T.clamp(D["solar"] * rnd(k + "|s", 0.90, 1.06), 0, 1100)

        wbgt = T.wbgt_c(tmax, rh, solar, v2)
        utci = T.utci_c(tmax, rh, solar, v10)
        hi = T.heat_index_c(tmax, rh)
        h = T.htsi(wbgt, utci, hi, tmin, run)
        vuln = T.vulnerability(a["elderly"], a["outdoor"], a["informal"], a["ac"], a["green"])

        cell = CELLS[i]
        out.append({
            "code": f"{c['corp']}-{i+1:02d}", "name": name, "population": pop,
            "cell": {"q": cell[0], "r": cell[1]},
            "weather": {"tmax_c": round(tmax, 2), "tmin_c": round(tmin, 2),
                        "rh_pct": round(rh, 1), "wind_10m_ms": round(v10, 2),
                        "wind_2m_ms": round(v2, 2), "solar_wm2": round(solar, 1),
                        "uhi_delta_c": round(uhi, 2), "peak_hour": D["hour"]},
            "indices": {"wbgt_c": round(wbgt, 2), "utci_c": round(utci, 2),
                        "heat_index_c": round(hi, 2), "wet_bulb_c": round(T.wet_bulb_c(tmax, rh), 2),
                        "htsi": round(h, 1), **T.band(h)},
            "risk": {**T.mortality(h, pop, vuln), "vulnerability": round(vuln, 3)},
            "demography": {kk: round(vv, 1) if isinstance(vv, float) else vv
                           for kk, vv in a.items()},
            "demography_provenance": meta["provenance"],
        })
    return out

def city_summary(key: str, wards: list[dict], horizon: int, live: dict | None) -> dict:
    pop = sum(w["population"] for w in wards)
    hw = sum(w["indices"]["htsi"] * w["population"] for w in wards) / pop
    over = [w for w in wards if w["indices"]["htsi"] >= 65]
    return {
        "htsi": round(hw, 1), **T.band(hw),
        "peak_wbgt_c": round(max(w["indices"]["wbgt_c"] for w in wards), 2),
        "peak_utci_c": round(max(w["indices"]["utci_c"] for w in wards), 2),
        "run_days": run_length(key, live),
        "wards_over_threshold": len(over),
        "population_exposed": sum(w["population"] for w in over),
        "excess_deaths": round(sum(w["risk"]["excess_deaths"] for w in wards), 1),
        "ed_presentations": round(sum(w["risk"]["ed_presentations"] for w in wards)),
        "ambulance_calls": round(sum(w["risk"]["ambulance_calls"] for w in wards)),
    }
