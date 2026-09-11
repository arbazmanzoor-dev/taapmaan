"""Look up an approximate centre point for every ward, once, from OpenStreetMap.

The ward names are real localities, but the hex lattice places them
schematically. A street map must use real positions, so this resolves each name
with Nominatim (OpenStreetMap's geocoder) and writes data/ward_geo.json.

Run it rarely. Nominatim allows at most one request per second and asks bulk
users to cache results: this script waits 2 s between calls, backs off for a
minute on "429 Too many requests", stops for good on a second 429, and on a
rerun only retries names it has not resolved yet.

    python scripts/geocode_wards.py
"""
from __future__ import annotations
import json, math, pathlib, re, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CITIES = json.loads((ROOT / "data" / "cities.json").read_text(encoding="utf-8"))
OUT = ROOT / "data" / "ward_geo.json"
UA = "Taapmaan-heat-console/2.4 (one-off ward geocoding build script)"
PAUSE_S = 2.0
MAX_KM = 35              # a hit further than this from the city centre is a different place
STATE_NAME = {"NCT": "Delhi"}   # Nominatim does not know the abbreviation

class RateLimited(RuntimeError):
    pass

def km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(a))

def lookup(q: str) -> list[dict]:
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "jsonv2", "limit": 3, "countrycodes": "in"})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    for attempt in (1, 2):
        time.sleep(PAUSE_S)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                print(f"    ! {q}: {e}")
                return []
            if attempt == 2:
                raise RateLimited(q)
            print("    ! 429 Too many requests -- backing off 60 s")
            time.sleep(60)
        except Exception as e:                  # one bad lookup must not lose the rest
            print(f"    ! {q}: {e}")
            return []
    return []

def resolve(name: str, c: dict) -> dict:
    state = STATE_NAME.get(c["state"], c["state"])
    base = re.sub(r"\s+(N|S|E|W|North|South|East|West)$", "", name)
    queries = [(f"{name}, {c['name']}, {state}, India", "nominatim"),
               (f"{name}, {c['name']}, India", "nominatim")]
    if base != name:                            # "Shahdara N": fall back to the locality itself
        queries.append((f"{base}, {c['name']}, India", "nominatim_base_name"))
    for q, src in queries:
        for h in lookup(q):
            lat, lon = float(h["lat"]), float(h["lon"])
            if km(c["lat"], c["lon"], lat, lon) <= MAX_KM:
                return {"lat": round(lat, 5), "lon": round(lon, 5), "source": src,
                        "match": (h.get("display_name") or "")[:140]}
    return {"source": "not_found"}

def main():
    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    try:
        for key, c in CITIES.items():
            got = out.setdefault(key, {})
            for name in c["wards"]:
                if got.get(name, {}).get("source", "").startswith("nominatim"):
                    continue
                got[name] = r = resolve(name, c)
                print(f"  {key:10} {name:24} {r['source']:20} {r.get('lat', ''):>9} {r.get('lon', ''):>9}")
    except RateLimited as e:
        print(f"stopped: Nominatim rate-limited twice (at {e}); rerun later to finish")
    finally:
        OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    found = sum(1 for c in out.values() for w in c.values() if w["source"] != "not_found")
    total = sum(len(c) for c in out.values())
    print(f"{found}/{total} wards located -> {OUT}")

if __name__ == "__main__":
    main()
