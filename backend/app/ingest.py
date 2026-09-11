"""Open-Meteo ingest.

Keyless and CORS-free from the server side. For each forecast day we walk all
24 hours, compute WBGT for each, and keep the *peak-stress* hour rather than the
peak-temperature hour -- in humid air they are different hours and the stress
one is what drives the health outcome.
"""
from __future__ import annotations
import asyncio, datetime as dt, json, logging, pathlib
import httpx
from . import thermal as T
from .wards import CITIES

log = logging.getLogger("taapmaan.ingest")
BASE = "https://api.open-meteo.com/v1/forecast"
HOURLY = "temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation"
PAST_DAYS = 10

# city key -> {"days": [...], "fetched_at": iso, "elevation": m}
CACHE: dict[str, dict] = {}
TTL = dt.timedelta(minutes=30)
CACHE_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "cache"
MIN_DAYS = 5                    # horizons the app serves, D0..D4
LAST_ERROR: dict[str, str] = {}

# Open-Meteo's free tier answers 429 with the limit it hit. While a limit is in
# force every call is wasted, so pause and probe again later with ONE request.
BLOCK: dict = {"until": None, "reason": None}

def blocked() -> bool:
    return BLOCK["until"] is not None and dt.datetime.now(dt.timezone.utc) < BLOCK["until"]

def _note_rate_limit(resp) -> str:
    try:
        reason = resp.json().get("reason") or "rate limited"
    except ValueError:
        reason = "rate limited"
    low, now = reason.lower(), dt.datetime.now(dt.timezone.utc)
    # a daily limit is probed hourly: the reset time is not published, and one
    # probe an hour costs nothing against the quota
    wait = dt.timedelta(minutes=1) if "minut" in low else dt.timedelta(hours=1) if ("daily" in low or "hour" in low) else dt.timedelta(minutes=15)
    BLOCK.update(until=now + wait, reason=reason)
    log.warning("Open-Meteo rate limit: %s -- pausing live ingest until %s UTC", reason, BLOCK["until"].strftime("%H:%M"))
    return reason

class IngestError(RuntimeError):
    pass

async def fetch_city(key: str, client: httpx.AsyncClient | None = None) -> dict:
    c = CITIES[key]
    params = {
        "latitude": c["lat"], "longitude": c["lon"],
        "daily": "temperature_2m_max,temperature_2m_min",
        "hourly": HOURLY, "wind_speed_unit": "ms",
        "timezone": "Asia/Kolkata", "forecast_days": 7,   # 7 so a cached copy still covers D0..D4 two days later
        # 10 days of history so the ML forecaster has its lag window.
        "past_days": PAST_DAYS,
    }
    if blocked():
        raise IngestError(f"paused: {BLOCK['reason']} (next try {BLOCK['until']:%H:%M} UTC)")
    own = client is None
    client = client or httpx.AsyncClient(timeout=12.0)
    try:
        r = await client.get(BASE, params=params)
        if r.status_code == 429:
            raise IngestError("rate-limited by Open-Meteo: " + _note_rate_limit(r))
        r.raise_for_status()
        j = r.json()
    except httpx.HTTPError as e:
        raise IngestError(f"open-meteo unreachable: {e}") from e
    finally:
        if own:
            await client.aclose()

    if "hourly" not in j or "daily" not in j:
        raise IngestError("unexpected payload shape")

    # Group hourly into calendar days, then reduce each to its peak-stress hour.
    H = j["hourly"]
    buckets: dict[str, list] = {}
    for i, ts in enumerate(H["time"]):
        d = ts[:10]
        t, rh = H["temperature_2m"][i], H["relative_humidity_2m"][i]
        v, sol = H["wind_speed_10m"][i], H["shortwave_radiation"][i]
        if None in (t, rh, v, sol):
            continue
        buckets.setdefault(d, []).append({
            "h": int(ts[11:13]), "T": t, "rh": rh, "wind": v, "solar": sol,
            "wbgt": round(T.wbgt_c(t, rh, sol, T.w10to2(v)), 2)})

    dmax = dict(zip(j["daily"]["time"], j["daily"]["temperature_2m_max"]))
    dmin = dict(zip(j["daily"]["time"], j["daily"]["temperature_2m_min"]))

    all_days = []
    for d in sorted(buckets):
        hrs = buckets[d]
        if len(hrs) < 20:
            continue
        peak = max(hrs, key=lambda x: x["wbgt"])
        all_days.append({
            "date": d,
            "tmax": peak["T"],                                  # driving temp at peak stress
            "tmax_daily": dmax.get(d, max(x["T"] for x in hrs)),
            "tmin": dmin.get(d, min(x["T"] for x in hrs)),
            "rh": peak["rh"], "wind": peak["wind"], "solar": peak["solar"],
            "hour": peak["h"], "hourly": hrs,
        })

    today = dt.date.today().isoformat()
    idx = next((i for i, d in enumerate(all_days) if d["date"] >= today), 0)
    days, history = all_days[idx:], all_days[:idx]
    if len(days) < MIN_DAYS:
        raise IngestError(f"forecast window too short ({len(days)} days)")

    payload = {"days": days, "history": history,
               "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
               "elevation": j.get("elevation"), "source": "open-meteo"}
    CACHE[key] = payload
    LAST_ERROR.pop(key, None); BLOCK.update(until=None, reason=None)
    _save(key, payload)
    log.info("ingested %s: %d forecast days + %d history, peak-stress hour %02d:00",
             key, len(days), len(history), days[0]["hour"])
    return payload

def _path(key: str) -> pathlib.Path:
    return CACHE_DIR / f"forecast_{key}.json"

def _save(key: str, payload: dict) -> None:
    """Persist the last good forecast so a rate limit or restart never blanks live mode."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path(key).with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8"); tmp.replace(_path(key))

def _reslice(payload: dict) -> dict | None:
    """Re-anchor a stored forecast on today's date. None once it no longer covers D0..D4:
    serving fewer days would silently mix forecast days with scenario days."""
    all_days = list(payload.get("history") or []) + list(payload.get("days") or [])
    today = dt.date.today().isoformat()
    idx = next((i for i, d in enumerate(all_days) if d["date"] >= today), None)
    if idx is None or len(all_days) - idx < MIN_DAYS:
        return None
    return {**payload, "history": all_days[:idx], "days": all_days[idx:]}

def load_disk_cache() -> dict:
    """At startup, restore each city's last good forecast -- served as stale, and labelled so."""
    out = {}
    for key in CITIES:
        f = _path(key)
        if not f.exists():
            continue
        try:
            p = _reslice(json.loads(f.read_text(encoding="utf-8")))
        except (ValueError, KeyError):
            p = None
        if p:
            p["from_disk"] = True; CACHE[key] = p; out[key] = p["fetched_at"]
    if out:
        log.info("restored cached forecasts from disk: %s", ", ".join(out))
    return out

def cached(key: str) -> dict | None:
    p = CACHE.get(key)
    if not p:
        return None
    if p["days"] and p["days"][0]["date"] < dt.date.today().isoformat():   # crossed midnight
        q = _reslice(p)
        if q is None:
            CACHE.pop(key, None); return None
        q["from_disk"] = p.get("from_disk", False); CACHE[key] = p = q
    return p

def status(key: str) -> dict:
    p, age = CACHE.get(key), age_seconds(key)
    return {"stale": bool(p) and (bool(p.get("from_disk")) or (age is not None and age > 2 * TTL.total_seconds())),
            "from_disk": bool(p and p.get("from_disk")), "age_seconds": age,
            "last_error": LAST_ERROR.get(key),
            "blocked_until": BLOCK["until"].isoformat() if blocked() else None,
            "block_reason": BLOCK["reason"] if blocked() else None}

def age_seconds(key: str) -> float | None:
    p = CACHE.get(key)
    if not p:
        return None
    return (dt.datetime.now(dt.timezone.utc)
            - dt.datetime.fromisoformat(p["fetched_at"])).total_seconds()

async def refresh_all() -> dict:
    """Scheduled job. One client, all cities, failures isolated per city."""
    out = {}
    async with httpx.AsyncClient(timeout=12.0) as client:
        for key in CITIES:
            try:
                await fetch_city(key, client)
                out[key] = "ok"
            except IngestError as e:
                out[key] = str(e); LAST_ERROR[key] = str(e)
                log.warning("ingest failed for %s: %s", key, e)
            await asyncio.sleep(0.25)   # be polite to a free endpoint
    return out
