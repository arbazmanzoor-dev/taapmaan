"""Train a gradient-boosted forecaster for peak heat stress at D+1/+3/+5.

    python scripts/train_model.py

Honest setup:
  * Temporal split in three parts, no shuffling -- shuffling a time series leaks
    tomorrow into today and inflates every metric:
        train      2013-2023   the model learns here
        calibrate  2024        sets the width of the 90% range; never trained on
        test       2025 -> the latest archived day; neither trained nor calibrated on
  * Confidence is stated as things that can be checked: R^2, how often the 90%
    range actually held on the test days, and how well it separates dangerous
    (WBGT >= 31 degC) days from safe ones (ROC AUC, balanced accuracy, Brier).
  * Climatology features are built from TRAINING YEARS ONLY, so the test set
    cannot see its own climate normals.
  * Scored against the two baselines that matter: persistence (assume D+h looks
    like D) and climatology (assume D+h is a normal day for that date). A model
    that cannot beat both of these is not worth deploying, and we report it
    either way.

Writes data/models/wbgt_dN.joblib and data/models/model_card.json
"""
from __future__ import annotations
import csv, json, math, pathlib, sys
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score, roc_auc_score
import joblib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app.wards import CITIES

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLIM = ROOT / "data" / "climate"
MODELS = ROOT / "data" / "models"
HORIZONS = (1, 3, 5)
CAL_FROM = "2024-01-01"
TEST_FROM = "2025-01-01"
CAUTION, DANGER = 28.0, 31.0        # WBGT degC: heavy-work limits / work suspension
LAGS = (0, 1, 2, 3, 6, 9)
CITY_IDX = {k: i for i, k in enumerate(CITIES)}

FEATURES = (["wbgt_lag%d" % l for l in LAGS]
            + ["tmax_lag%d" % l for l in LAGS[:4]]
            + ["tmin_lag0", "rh_lag0", "solar_lag0", "wind_lag0", "run_days",
               "wbgt_trend3", "wbgt_anom", "clim_wbgt_target",
               "doy_sin", "doy_cos", "city"])

def load(city: str) -> list[dict]:
    with (CLIM / f"{city}_daily.csv").open(encoding="utf-8") as f:
        rows = [{k: (v if k == "date" else float(v)) for k, v in r.items()}
                for r in csv.DictReader(f)]
    return rows

def train_climatology(rows: list[dict]) -> dict[int, float]:
    """Median peak WBGT by day-of-year, +/-7 day ring, TRAIN ROWS ONLY."""
    by = {}
    for r in rows:
        by.setdefault(int(r["doy"]), []).append(r["wbgt_peak"])
    out = {}
    for doy in range(1, 367):
        pool = []
        for off in range(-7, 8):
            pool += by.get(((doy - 1 + off) % 366) + 1, [])
        if pool:
            out[doy] = float(np.median(pool))
    return out

def build(city: str, rows: list[dict], horizon: int, clim: dict[int, float]):
    X, y, dates = [], [], []
    n = len(rows)
    for i in range(max(LAGS), n - horizon):
        tgt = rows[i + horizon]
        cur = rows[i]
        doy_t = int(tgt["doy"])
        ct = clim.get(doy_t)
        if ct is None:
            continue
        f = [rows[i - l]["wbgt_peak"] for l in LAGS]
        f += [rows[i - l]["tmax_daily"] for l in LAGS[:4]]
        f += [cur["tmin"], cur["rh_peak"], cur["solar_peak"], cur["wind_peak"],
              cur["run_days"],
              cur["wbgt_peak"] - rows[i - 3]["wbgt_peak"],
              cur["wbgt_peak"] - clim.get(int(cur["doy"]), cur["wbgt_peak"]),
              ct,
              math.sin(2 * math.pi * doy_t / 366), math.cos(2 * math.pi * doy_t / 366),
              CITY_IDX[city]]
        X.append(f); y.append(tgt["wbgt_peak"]); dates.append(tgt["date"])
    return np.array(X, float), np.array(y, float), dates

def metrics(pred, true):
    e = pred - true
    return {"mae": round(float(np.mean(np.abs(e))), 3),
            "rmse": round(float(np.sqrt(np.mean(e ** 2))), 3),
            "bias": round(float(np.mean(e)), 3)}

def extra_metrics(pred, pers, clm, y, p90):
    """Error BANDS (not a MAE dressed as one) and the days that matter:
    each city's hottest 10% of days, and days at or above 31 °C WBGT."""
    ae = np.abs(pred - y); hot = y >= p90
    mae = lambda v, m: round(float(np.mean(np.abs(v[m] - y[m]))), 3)
    def det(v):
        t, pp = y >= 31, v >= 31; tp = int((t & pp).sum())
        return round(tp / max(int(t.sum()), 1), 3), round(tp / max(int(pp.sum()), 1), 3)
    (rm, pm_), (rp, pp_) = det(pred), det(pers)
    return {
        "error_bands": {**{f"p{q}": round(float(np.quantile(ae, q / 100)), 2) for q in (50, 80, 90, 95)},
                        "share_within_mae": round(float(np.mean(ae <= ae.mean())), 3)},
        "hottest_10pct_days": {"n": int(hot.sum()), "model_mae": mae(pred, hot),
                               "model_bias": round(float(np.mean(pred[hot] - y[hot])), 3),
                               "persistence_mae": mae(pers, hot), "climatology_mae": mae(clm, hot),
                               "beats_persistence": bool(mae(pred, hot) < mae(pers, hot))},
        "days_at_or_above_31c": {"n": int((y >= 31).sum()), "model_recall": rm, "model_precision": pm_,
                                 "persistence_recall": rp, "persistence_precision": pp_},
    }

def danger_probability(pred, res):
    """P(WBGT >= 31) per forecast: the share of calibration errors (sorted, signed)
    that would carry the forecast to or over the line."""
    return 1 - np.searchsorted(res, DANGER - np.asarray(pred), side="left") / len(res)

def confidence(pred_cal, y_cal, pred, y, p90, base_rate):
    """How far a single forecast can be trusted. The range is sized on the
    calibration year, then checked on the test days, which it never saw."""
    res = np.sort(y_cal - pred_cal)
    ae = np.sort(np.abs(res)); n = len(ae)
    width = lambda c: float(ae[min(n - 1, int(np.ceil(c * (n + 1))) - 1)])   # split-conformal quantile
    w80, w90 = width(0.8), width(0.9)
    err, hot = np.abs(y - pred), y >= p90
    t, called = y >= DANGER, pred >= DANGER
    tp, tn = int((t & called).sum()), int((~t & ~called).sum())
    prob = danger_probability(pred, res)
    brier = float(np.mean((prob - t) ** 2))
    band = lambda v: np.digitize(v, (CAUTION, DANGER))        # 0 safe, 1 caution, 2 danger
    r4 = lambda v: round(float(v), 4)
    return {
        "n_calibrate": n, "n_test": int(len(y)),
        "r2": r4(r2_score(y, pred)),
        "interval_80_c": round(w80, 2), "interval_80_coverage": r4(np.mean(err <= w80)),
        "interval_90_c": round(w90, 2), "interval_90_coverage": r4(np.mean(err <= w90)),
        "interval_90_coverage_hottest_10pct": r4(np.mean(err[hot] <= w90)),
        "danger_days": {
            "threshold_c": DANGER, "share_of_test_days": r4(t.mean()),
            "roc_auc": r4(roc_auc_score(t, pred)),
            "accuracy": r4((tp + tn) / len(t)),
            "balanced_accuracy": r4(0.5 * (tp / max(t.sum(), 1) + tn / max((~t).sum(), 1))),
            "precision": r4(tp / max(called.sum(), 1)), "recall": r4(tp / max(t.sum(), 1)),
            "brier": r4(brier),
            "brier_skill_vs_base_rate": r4(1 - brier / np.mean((base_rate - t) ** 2)),
        },
        "band_accuracy": r4(np.mean(band(y) == band(pred))),
    }, res

def main():
    MODELS.mkdir(parents=True, exist_ok=True)
    per_city = {c: load(c) for c in CITIES}
    first = min(r[0]["date"] for r in per_city.values())
    last = min(r[-1]["date"] for r in per_city.values())
    card = {"target": "peak-stress-hour WBGT (deg C)",
            "data": f"ERA5 reanalysis via Open-Meteo archive, {first}..{last}",
            "data_through": last,
            "split": {"train": f"{first}..{CAL_FROM} (exclusive)",
                      "calibrate": f"{CAL_FROM}..{TEST_FROM} (exclusive)",
                      "test": f"{TEST_FROM}..{last}"},
            "algorithm": "HistGradientBoostingRegressor (scikit-learn)",
            "features": FEATURES, "horizons": {},
            "confidence_explained": {
                "r2": "share of the day-to-day variation in peak WBGT that the forecast explains (1 = perfect)",
                "interval_90_c": "every forecast carries a +/- range, sized on the calibration year so that 90% of "
                                 "days should land inside it; interval_90_coverage is how often they actually did on the test days",
                "danger_days.roc_auc": "chance that a random dangerous day (WBGT >= 31 degC) gets a higher forecast than a random safer day",
                "danger_days.brier_skill_vs_base_rate": "how much better the per-day danger probability is than always "
                                                        "quoting the historical rate (0 = no better, 1 = perfect)",
                "band_accuracy": "share of test days put in the right band: safe (<28), caution (28-31), danger (>=31)",
            }}
    wl0, ci = FEATURES.index("wbgt_lag0"), FEATURES.index("clim_wbgt_target")

    for h in HORIZONS:
        part = {"train": ([], []), "cal": ([], []), "test": ([], [])}
        base_pers_te, base_clim_te = [], []
        clims, p90te = {}, []
        for city, rows in per_city.items():
            tr_rows = [r for r in rows if r["date"] < CAL_FROM]
            clim = train_climatology(tr_rows)          # train-only climatology
            clims[city] = clim
            X, y, dates = build(city, rows, h, clim)
            d = np.array(dates)
            m = d >= TEST_FROM
            for k, sel in (("train", d < CAL_FROM), ("cal", (d >= CAL_FROM) & ~m), ("test", m)):
                part[k][0].append(X[sel]); part[k][1].append(y[sel])
            p90te.append(np.full(int(m.sum()), np.percentile([r["wbgt_peak"] for r in tr_rows], 90)))
            # baselines on the same test rows
            base_pers_te.append(X[m][:, wl0])
            base_clim_te.append(X[m][:, ci])
        (Xtr, ytr), (Xca, yca), (Xte, yte) = [(np.vstack(a), np.concatenate(b)) for a, b in part.values()]
        pers = np.concatenate(base_pers_te); clm = np.concatenate(base_clim_te)

        model = HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.06, max_depth=6,
            min_samples_leaf=30, l2_regularization=1.0, random_state=0,
            categorical_features=[FEATURES.index("city")])
        model.fit(Xtr, ytr)
        pred = model.predict(Xte)
        conf, res = confidence(model.predict(Xca), yca, pred, yte, np.concatenate(p90te),
                               float(np.mean(ytr >= DANGER)))

        mm, mp, mc = metrics(pred, yte), metrics(pers, yte), metrics(clm, yte)
        skill_p = round(1 - mm["mae"] / mp["mae"], 4)
        skill_c = round(1 - mm["mae"] / mc["mae"], 4)
        card["horizons"][f"d{h}"] = {
            "n_train": int(len(ytr)), "n_test": int(len(yte)),
            "model": mm, "baseline_persistence": mp, "baseline_climatology": mc,
            "skill_vs_persistence": skill_p, "skill_vs_climatology": skill_c,
            "beats_both": bool(mm["mae"] < mp["mae"] and mm["mae"] < mc["mae"]),
        }
        card["horizons"][f"d{h}"].update(extra_metrics(pred, pers, clm, yte, np.concatenate(p90te)))
        card["horizons"][f"d{h}"]["confidence"] = conf
        # Ship the training climatology inside the bundle: inference must see
        # the same normals the model was fitted against, or the feature shifts
        # under it at serve time.
        joblib.dump({"model": model, "features": FEATURES, "lags": LAGS,
                     "city_index": CITY_IDX, "horizon": h,
                     # calibration-year errors: size the 90% range and the danger probability at serve time
                     "interval_90": conf["interval_90_c"], "danger_threshold_c": DANGER,
                     "residuals": [round(float(r), 3) for r in res],
                     "climatology": {c: {int(k): float(v) for k, v in cl.items()}
                                     for c, cl in clims.items()}},
                    MODELS / f"wbgt_d{h}.joblib")
        print(f"  D+{h}: MAE model {mm['mae']:.3f} | persistence {mp['mae']:.3f} "
              f"| climatology {mc['mae']:.3f}  ->  skill {skill_p:+.1%} / {skill_c:+.1%}"
              f"  ({len(ytr):,} train, {len(yte):,} test)")

    card["caveats"] = [
        "Trained on ERA5 reanalysis, not station observations. It learns ERA5's world.",
        "IT FORECASTS FROM HISTORY ONLY. It sees past days, never an NWP forecast, so it "
        "cannot know a weather system is inbound. Where it disagrees with the physics path "
        "(which uses a real Open-Meteo forecast), trust the physics path. This model is a "
        "statistical benchmark for what history alone can achieve -- not a replacement for NWP.",
        "The genuinely valuable ML here would be bias-correcting the NWP forecast against "
        "station observations. That needs observation data we do not have.",
        "Predicts peak-stress WBGT for the CITY. Ward downscaling is still the deterministic UHI model, not learned.",
        "It does NOT predict mortality. No daily death counts were available, so the mortality layer stays parametric.",
        "Reanalysis has no forecast error, so real operational skill at D+3 will be worse than these numbers.",
    ]
    h3 = card["horizons"]["d3"]["hottest_10pct_days"]
    card["caveats"].insert(1, f"On each city's hottest 10% of days the model reads {abs(h3['model_bias']):.1f} °C low at D+3 and is "
                              f"less accurate than persistence ({h3['model_mae']:.2f} vs {h3['persistence_mae']:.2f} °C). It must not be "
                              "used to call heatwave days; the physics forecast does that.")
    c3 = card["horizons"]["d3"]["confidence"]
    card["caveats"].insert(2, f"The 90% range is one width for every day, sized on {CAL_FROM[:4]}. On each city's hottest 10% "
                              f"of test days it held on {c3['interval_90_coverage_hottest_10pct']:.0%} of days at D+3 "
                              f"(vs {c3['interval_90_coverage']:.0%} overall), so on the hottest days it is too narrow.")

    print(f"\nConfidence on {card['split']['test']} -- days never trained or calibrated on:")
    for h in HORIZONS:
        c = card["horizons"][f"d{h}"]["confidence"]; dd = c["danger_days"]
        print(f"  D+{h}: R^2 {c['r2']:.3f} | 90% range +/-{c['interval_90_c']:.2f} C held on {c['interval_90_coverage']:.1%} "
              f"(hottest 10%: {c['interval_90_coverage_hottest_10pct']:.1%}) | danger-day AUC {dd['roc_auc']:.3f}, "
              f"balanced acc {dd['balanced_accuracy']:.1%}, Brier skill {dd['brier_skill_vs_base_rate']:+.2f} "
              f"| band accuracy {c['band_accuracy']:.1%}")
    (MODELS / "model_card.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
    print("wrote", MODELS / "model_card.json")

if __name__ == "__main__":
    main()
