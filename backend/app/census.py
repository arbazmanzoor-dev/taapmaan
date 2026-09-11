"""Census 2011 demography, and honest bookkeeping about where each number came from.

Three tiers, best first:

  ward_csv        a real ward-level table you dropped in data/census/
  census2011:city a real Census figure for the city, dispersed across wards
  modelled        no source exists yet — a plausible value, labelled as such

Every field a ward carries reports its tier, and the API passes that through, so
nothing on screen can silently pass itself off as measured when it is not.
"""
from __future__ import annotations
import csv, json, pathlib
from .thermal import clamp

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "census"
CENSUS: dict = json.loads((DATA / "india_census2011.json").read_text(encoding="utf-8"))

CITY = CENSUS["cities"]
NATIONAL = CENSUS["national_urban"]

# Columns a ward CSV may supply. Anything missing falls back a tier.
CSV_FIELDS = {
    "population": "population",
    "elderly_60plus_pct": "elderly",
    "outdoor_worker_pct": "outdoor",
    "informal_housing_pct": "informal",
    "ac_ownership_pct": "ac",
    "canopy_cover_pct": "green",
    "cooling_centres": "cooling_centres",
    "hospital_beds": "hospital_beds",
    "asha_workers": "asha_workers",
}

def ward_csv(city: str) -> dict[str, dict]:
    """Real ward table, keyed by lowercased ward name. Empty when absent."""
    f = DATA / f"wards_{city}.csv"
    if not f.exists():
        return {}
    out: dict[str, dict] = {}
    with f.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("ward_name") or "").strip()
            if not name:
                continue
            rec = {}
            for col, field in CSV_FIELDS.items():
                v = (row.get(col) or "").strip()
                if v:
                    try:
                        rec[field] = float(v)
                    except ValueError:
                        pass
            if rec:
                out[name.lower()] = rec
    return out

def anchored(names: list[str], pops: list[float], target: float, dispersion: float,
             lo: float, hi: float, seedfn, tag: str) -> list[float]:
    """Disperse a real city-level share across wards.

    The result is population-weighted-mean-preserving: the ward values average
    back to the Census figure for the city. Dispersion controls how unequal the
    wards are, not what the city total is -- that stays fixed to the source.
    """
    total = sum(pops) or 1.0
    x = [target * (1 + (seedfn(f"{tag}|{n}") * 2 - 1) * dispersion) for n in names]
    for _ in range(80):
        x = [clamp(v, lo, hi) for v in x]
        m = sum(p * v for p, v in zip(pops, x)) / total
        if abs(m - target) < 1e-9 or m <= 0:
            break
        k = target / m
        x = [v * k for v in x]
    return [clamp(v, lo, hi) for v in x]

def achieved_mean(values: list[float], pops: list[float]) -> float:
    t = sum(pops) or 1.0
    return sum(p * v for p, v in zip(pops, values)) / t

def city_facts(city: str) -> dict:
    """Real Census figures for the city, for display and for the API."""
    c = CITY.get(city)
    if not c:
        return {}
    return {
        "census_unit": c["census_unit"],
        "population_2011": c["population_2011"],
        "child_0_6_pct": round(c["child_0_6"] / c["population_2011"] * 100, 2),
        "literacy_pct": c["literacy_pct"],
        "sex_ratio": c["sex_ratio"],
        "slum_population": c["slum_population"],
        "slum_pct": c["slum_pct"],
        "slum_households": c["slum_households"],
        "source": "Census of India 2011",
        "source_url": c["source_url"],
    }

FALLBACK_TIER = {
    "population":      "modelled:ward-split",
    "informal":        "census2011:city",
    "elderly":         "census2011:india_urban",
    "outdoor":         "modelled",
    "ac":              "modelled",
    "green":           "modelled",
    "cooling_centres": "modelled",
    "hospital_beds":   "modelled",
    "asha_workers":    "modelled",
}

def provenance(coverage: dict[str, int], n_wards: int) -> dict:
    """Which tier each field came from, honest about PARTIAL csv coverage.

    A CSV with 3 rows out of 37 wards does not make the field measured -- it
    makes it measured for 3 wards, and this says so.
    """
    out = {}
    for field, fallback in FALLBACK_TIER.items():
        got = coverage.get(field, 0)
        if got >= n_wards and n_wards:
            out[field] = "ward_csv"
        elif got:
            out[field] = f"ward_csv:{got}/{n_wards}, rest {fallback}"
        else:
            out[field] = fallback
    return out

LEGEND = {
    "ward_csv": "real ward-level table supplied in data/census/",
    "census2011:city": "real Census 2011 figure for this city, dispersed across wards (population-weighted mean preserved)",
    "census2011:india_urban": "real Census 2011 figure for urban India, applied as the city anchor",
    "modelled:ward-split": "city total is real; the split between wards is modelled",
    "modelled": "no source yet — plausible value, replace with a real join",
    "ward_csv:n/m, rest ...": "the CSV covered n of m wards for this field; the rest fell back to the tier named",
}
