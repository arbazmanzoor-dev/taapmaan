"""Inference for the D+1/+3/+5 heat-stress forecaster, and the climatology layer.

Loads the joblib bundles written by scripts/train_model.py. If they are absent
the whole module reports unavailable and the API keeps working without it --
the physics path never depends on the model being there.
"""
from __future__ import annotations
import bisect, datetime as dt, json, math, pathlib
from . import thermal as T
from .wards import CITIES

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = ROOT / "data" / "models"
CLIM = ROOT / "data" / "climate"

_bundles: dict[int, dict] = {}
_clim: dict[str, dict] = {}
_card: dict | None = None
AVAILABLE = False

def load() -> bool:
    """Best-effort load. Never raises -- a missing model is not an outage."""
    global AVAILABLE, _card
    try:
        import joblib
    except ImportError:
        return False
    for h in (1, 3, 5):
        f = MODELS / f"wbgt_d{h}.joblib"
        if f.exists():
            try:
                _bundles[h] = joblib.load(f)
            except Exception:
                pass
    for c in CITIES:
        f = CLIM / f"{c}_climatology.json"
        if f.exists():
            _clim[c] = json.loads(f.read_text(encoding="utf-8"))
    f = MODELS / "model_card.json"
    if f.exists():
        _card = json.loads(f.read_text(encoding="utf-8"))
    AVAILABLE = bool(_bundles)
    return AVAILABLE

def card() -> dict | None:
    return _card

def _wbgt_of(day: dict) -> float:
    return max((h["wbgt"] for h in day.get("hourly") or []), default=
               T.wbgt_c(day["tmax"], day["rh"], day["solar"], T.w10to2(day["wind"])))

def series(live: dict) -> list[dict]:
    """History + today, oldest first. Index -1 is today."""
    return list(live.get("history") or []) + [live["days"][0]]

def features(city: str, live: dict, horizon: int, bundle: dict):
    s = series(live)
    lags = bundle["lags"]
    need = max(lags) + 1
    if len(s) < need:
        return None, f"need {need} days of history, have {len(s)}"

    wb = [_wbgt_of(d) for d in s]
    tx = [d["tmax_daily"] for d in s]
    cur = s[-1]

    hw = CITIES[city]["hwT"]
    run = 0
    for d in reversed(s):
        if d["tmax_daily"] >= hw:
            run += 1
        else:
            break

    target_date = dt.date.fromisoformat(cur["date"]) + dt.timedelta(days=horizon)
    doy_t = int(target_date.strftime("%j"))
    doy_c = int(dt.date.fromisoformat(cur["date"]).strftime("%j"))
    clim = bundle.get("climatology", {}).get(city, {})
    ct = clim.get(doy_t) or clim.get(str(doy_t))
    cc = clim.get(doy_c) or clim.get(str(doy_c)) or wb[-1]
    if ct is None:
        return None, "no climatology for target day"

    f = [wb[-1 - l] for l in lags]
    f += [tx[-1 - l] for l in lags[:4]]
    f += [cur["tmin"], cur["rh"], cur["solar"], cur["wind"], run,
          wb[-1] - wb[-4], wb[-1] - cc, ct,
          math.sin(2 * math.pi * doy_t / 366), math.cos(2 * math.pi * doy_t / 366),
          bundle["city_index"][city]]
    return ([f], {"target_date": target_date.isoformat(), "climatology_wbgt": round(ct, 2),
                  "persistence_wbgt": round(wb[-1], 2), "run_days": run})

def predict(city: str, live: dict, horizon: int) -> dict:
    """ML forecast for peak-stress WBGT, always reported beside its baselines."""
    if horizon == 0:
        return {"available": False, "reason": "nothing to forecast at horizon 0 — today is observed, not predicted"}
    if horizon not in _bundles:
        return {"available": False,
                "reason": f"no model trained for horizon {horizon} (available: {sorted(_bundles)})"}
    b = _bundles[horizon]
    X, meta = features(city, live, horizon, b)
    if X is None:
        return {"available": False, "reason": meta}
    yhat = float(b["model"].predict(X)[0])
    hz = (_card or {}).get("horizons", {}).get(f"d{horizon}", {})
    phys = _wbgt_of(live["days"][horizon]) if horizon < len(live["days"]) else None
    out = {
        "available": True, "horizon_days": horizon,
        "predicted_wbgt_c": round(yhat, 2),
        "baseline_persistence_c": meta["persistence_wbgt"],
        "baseline_climatology_c": meta["climatology_wbgt"],
        "physics_forecast_wbgt_c": round(phys, 2) if phys is not None else None,
        "anomaly_vs_climatology_c": round(yhat - meta["climatology_wbgt"], 2),
        "target_date": meta["target_date"],
        "test_mae_c": hz.get("model", {}).get("mae"),
        # an error BAND, not a MAE dressed up as one: 80% of held-out days fell inside this
        "p80_abs_error_c": hz.get("error_bands", {}).get("p80"),
        "p90_abs_error_c": hz.get("error_bands", {}).get("p90"),
        "hot_day_bias_c": hz.get("hottest_10pct_days", {}).get("model_bias"),
        "hot_day_mae_c": hz.get("hottest_10pct_days", {}).get("model_mae"),
        "hot_day_persistence_mae_c": hz.get("hottest_10pct_days", {}).get("persistence_mae"),
    }
    if phys is not None:
        out["ml_minus_physics_c"] = round(yhat - phys, 2)
    w90, res = b.get("interval_90"), b.get("residuals")
    if w90 is not None:
        # sized on a calibration year the model never trained on; 90% of test days landed inside
        out["interval_90_c"] = [round(yhat - w90, 2), round(yhat + w90, 2)]
    if res:
        # share of calibration-year errors that would carry this forecast to >= 31 degC
        out["danger_probability"] = round(1 - bisect.bisect_left(res, b["danger_threshold_c"] - yhat) / len(res), 3)
    if hz.get("confidence"):
        out["confidence"] = hz["confidence"]
        out["tested_on"] = (_card or {}).get("split", {}).get("test")
        out["data_through"] = (_card or {}).get("data_through")
    return out

def percentile(city: str, value: float, date_iso: str, var: str = "wbgt") -> dict:
    """Where today's value sits in this city's own climate for this date.

    'Extreme' has to mean extreme *here*: 34 C WBGT is routine in Chennai and
    unheard of in Delhi in January.
    """
    c = _clim.get(city)
    if not c:
        return {"available": False}
    doy = str(int(dt.date.fromisoformat(date_iso).strftime("%j")))
    rec = (c.get("doy") or {}).get(doy)
    if not rec or var not in rec:
        return {"available": False}
    ps = rec[var]
    band, exceeded = "below normal", None
    for p in (50, 75, 90, 95, 97, 99):
        v = ps.get(f"p{p}")
        if v is not None and value >= v:
            exceeded = p
    if exceeded is not None:
        band = {50: "above normal", 75: "warm", 90: "hot",
                95: "very hot", 97: "extreme", 99: "record territory"}[exceeded]
    return {"available": True, "variable": var, "value": round(value, 2),
            "percentile_at_least": exceeded, "band": band,
            "normal_p50": ps.get("p50"), "p90": ps.get("p90"), "p97": ps.get("p97"),
            "anomaly_vs_normal_c": round(value - ps["p50"], 2) if ps.get("p50") else None,
            "reference_period": c.get("period"), "samples": rec.get("n")}
