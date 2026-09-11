"""Pull ERA5 reanalysis from Open-Meteo's archive and reduce it to daily
peak-heat-stress records, then derive day-of-year climatology.

    python scripts/build_climate.py [--start 2013-01-01] [--end 2025-12-31]
    python scripts/build_climate.py --append     # add every day since the last run

Writes  data/climate/<city>_daily.csv        one row per day, 2013 onwards
        data/climate/<city>_climatology.json day-of-year percentiles

ERA5 is reanalysis, not station observation: it is a physically consistent
best estimate on a ~9 km grid. Good enough to define what "unusual for this
date in this city" means, which is the job here.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, json, pathlib, sys, time, urllib.parse, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app import thermal as T
from app.wards import CITIES

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "climate"

def fetch(city_key: str, start: str, end: str) -> dict:
    c = CITIES[city_key]
    q = urllib.parse.urlencode({
        "latitude": c["lat"], "longitude": c["lon"],
        "start_date": start, "end_date": end,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation",
        "wind_speed_unit": "ms", "timezone": "Asia/Kolkata",
    })
    with urllib.request.urlopen(f"{ARCHIVE}?{q}", timeout=180) as r:
        return json.load(r)

def to_daily(city_key: str, payload: dict, run0: int = 0) -> list[dict]:
    """Collapse hourly ERA5 to one record per day, keyed on the peak-STRESS
    hour (max WBGT), which is not always the hottest hour. `run0` is the
    heatwave-run count on the day before the first one fetched."""
    H = payload["hourly"]
    days: dict[str, list] = {}
    for i, ts in enumerate(H["time"]):
        d, hh = ts.split("T")
        t, rh = H["temperature_2m"][i], H["relative_humidity_2m"][i]
        v, s = H["wind_speed_10m"][i], H["shortwave_radiation"][i]
        if None in (t, rh, v, s):
            continue
        days.setdefault(d, []).append({
            "h": int(hh[:2]), "T": t, "rh": rh, "wind": v, "solar": s,
            "wbgt": T.wbgt_c(t, rh, s, T.w10to2(v)),
        })

    hw = CITIES[city_key]["hwT"]
    out, run = [], run0
    for d in sorted(days):
        hrs = days[d]
        if len(hrs) < 20:
            continue
        peak = max(hrs, key=lambda x: x["wbgt"])
        tmax_daily = max(x["T"] for x in hrs)
        tmin = min(x["T"] for x in hrs)
        run = run + 1 if tmax_daily >= hw else 0
        utci = T.utci_c(peak["T"], peak["rh"], peak["solar"], peak["wind"])
        hi = T.heat_index_c(peak["T"], peak["rh"])
        out.append({
            "date": d,
            "doy": int(time.strftime("%j", time.strptime(d, "%Y-%m-%d"))),
            "peak_hour": peak["h"],
            "tmax_peak": round(peak["T"], 2), "tmax_daily": round(tmax_daily, 2),
            "tmin": round(tmin, 2), "rh_peak": round(peak["rh"], 1),
            "wind_peak": round(peak["wind"], 2), "solar_peak": round(peak["solar"], 1),
            "wbgt_peak": round(peak["wbgt"], 3),
            "utci_peak": round(utci, 2), "hi_peak": round(hi, 2),
            "run_days": run,
            "htsi": round(T.htsi(peak["wbgt"], utci, hi, tmin, run), 2),
        })
    return out

def percentiles(vals: list[float], ps=(50, 75, 90, 95, 97, 99)) -> dict:
    v = sorted(vals)
    n = len(v)
    def q(p):
        if not n:
            return None
        k = (n - 1) * p / 100
        lo, hi = int(k), min(int(k) + 1, n - 1)
        return round(v[lo] + (v[hi] - v[lo]) * (k - lo), 3)
    return {f"p{p}": q(p) for p in ps}

def climatology(rows: list[dict], window: int = 7) -> dict:
    """Day-of-year distribution using a +/- `window` day ring, so each date has
    ~15 days x N years of samples instead of N."""
    by_doy: dict[int, list[dict]] = {}
    for r in rows:
        by_doy.setdefault(r["doy"], []).append(r)
    out = {}
    for doy in range(1, 367):
        pool = []
        for off in range(-window, window + 1):
            d = ((doy - 1 + off) % 366) + 1
            pool += by_doy.get(d, [])
        if not pool:
            continue
        out[str(doy)] = {
            "n": len(pool),
            "wbgt": percentiles([p["wbgt_peak"] for p in pool]),
            "htsi": percentiles([p["htsi"] for p in pool]),
            "tmax": percentiles([p["tmax_daily"] for p in pool]),
        }
    return out

def _numeric(r: dict) -> dict:
    return {k: (v if k == "date" else int(float(v)) if k == "doy" else float(v)) for k, v in r.items()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2013-01-01")
    ap.add_argument("--end", default=None,
                    help="last day to fetch (default: 2025-12-31, or yesterday with --append)")
    ap.add_argument("--append", action="store_true",
                    help="fetch only the days after each city's last stored row and add them")
    a = ap.parse_args()
    end = a.end or ((dt.date.today() - dt.timedelta(days=1)).isoformat() if a.append else "2025-12-31")
    OUT.mkdir(parents=True, exist_ok=True)

    for key in CITIES:
        path, old, start = OUT / f"{key}_daily.csv", [], a.start
        if a.append and path.exists():
            with path.open(encoding="utf-8") as f:
                old = list(csv.DictReader(f))
            start = (dt.date.fromisoformat(old[-1]["date"]) + dt.timedelta(days=1)).isoformat()
            if start > end:
                print(f"  {key:10s} already up to {old[-1]['date']}")
                continue
        print(f"  {key:10s} fetching {start}..{end} ...", end="", flush=True)
        payload = fetch(key, start, end)
        # carry the heatwave-run count across the join so day 1 of the new block is not a reset
        new = to_daily(key, payload, run0=int(float(old[-1]["run_days"])) if old else 0)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list((old or new)[0].keys()))
            w.writeheader()
            w.writerows(old + new)            # stored rows go back exactly as they were read
        rows = [_numeric(r) for r in old] + new
        clim = climatology(rows)
        (OUT / f"{key}_climatology.json").write_text(json.dumps({
            "city": key, "source": "ERA5 via Open-Meteo archive API",
            "window_days": 7, "period": f"{rows[0]['date']}..{rows[-1]['date']}",
            "n_days": len(rows), "doy": clim,
        }, indent=1), encoding="utf-8")
        print(f" +{len(new)} days, now {rows[0]['date']}..{rows[-1]['date']} ({len(rows)} days)")
        time.sleep(1.0)
    print("done ->", OUT)

if __name__ == "__main__":
    main()
