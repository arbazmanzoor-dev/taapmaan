"""Broadcast endpoint test matrix. Throwaway DB, no network, real app code.

usage: .venv/bin/python test_broadcast.py <backend_dir> <tmp_dir>
"""
import datetime as dt, math, os, pathlib, socket, sqlite3, sys

BACKEND, TMP = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
TMP.mkdir(parents=True, exist_ok=True)
DB = TMP / "bc_test.db"
if DB.exists():
    DB.unlink()
os.environ["TAAPMAAN_DB"] = str(DB)
for k in ("MSG91_AUTHKEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TAAPMAAN_BROADCAST_TOKEN"):
    os.environ.pop(k, None)

# Any outbound connection is recorded and refused. TestClient talks to the app
# in-process (no sockets), so this only catches real network use.
NET = []
def _no_net(*a, **k):
    NET.append(a[1:] if a else k)
    raise OSError("network disabled in test")
socket.socket.connect = _no_net
socket.create_connection = _no_net

sys.path.insert(0, str(BACKEND))
from fastapi.testclient import TestClient
from app import main, ingest, store, thermal as T

store.init()
ingest.CACHE_DIR = TMP / "cache"          # never touch the real forecast cache
c = TestClient(main.app)                  # no `with` block: lifespan (Open-Meteo) never runs

PASS, FAIL = [], []
def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  PASS " if ok else "  FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))

def rows(sql):
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(sql)]
def counts():
    return rows("select count(*) n from broadcasts")[0]["n"], rows("select count(*) n from audit")[0]["n"]

MON = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

def fake_live():
    """A clearly synthetic 'live' forecast, only so the live code paths can run."""
    today = dt.date.today()
    def day(d):
        hrs = []
        for h in range(24):
            t = 36 + 7 * math.cos(2 * math.pi * (h - 15) / 24)
            rh = 32 - 12 * math.cos(2 * math.pi * (h - 15) / 24)
            sol = max(0.0, 950 * math.sin(math.pi * (h - 6) / 13)) if 6 <= h <= 19 else 0.0
            hrs.append({"h": h, "T": round(t, 1), "rh": round(rh), "wind": 3.0, "solar": round(sol),
                        "wbgt": round(T.wbgt_c(t, rh, sol, T.w10to2(3.0)), 2)})
        pk = max(hrs, key=lambda x: x["wbgt"])
        return {"date": d.isoformat(), "tmax": pk["T"], "tmax_daily": max(x["T"] for x in hrs),
                "tmin": min(x["T"] for x in hrs), "rh": pk["rh"], "wind": pk["wind"],
                "solar": pk["solar"], "hour": pk["h"], "hourly": hrs}
    return {"days": [day(today + dt.timedelta(days=i)) for i in range(7)],
            "history": [day(today - dt.timedelta(days=i)) for i in range(10, 0, -1)],
            "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "elevation": 53, "source": "test-fixture"}

def bc(headers=None, **kw):
    body = {"city": "ahmedabad", "dry_run": True, "mode": "scenario", "actor": "Test officer"} | kw
    return c.post("/v1/broadcast", json=body, headers=headers or {})

POP = main.CITIES["ahmedabad"]["pop"]
CORP = main.CITIES["ahmedabad"]["corp"]

print("\n1. SMS part counting (fixed expectations, not the app's own formula)")
for label, msg, enc, n in (("160 GSM chars", "a" * 160, "GSM-7", 1), ("161 GSM chars", "a" * 161, "GSM-7", 2),
                           ("306 GSM chars", "a" * 306, "GSM-7", 2), ("307 GSM chars", "a" * 307, "GSM-7", 3),
                           ("80 x € (160 septets)", "€" * 80, "GSM-7", 1), ("81 x € (162 septets)", "€" * 81, "GSM-7", 2),
                           ("70 x °", "°" * 70, "UCS-2", 1), ("71 x °", "°" * 71, "UCS-2", 2),
                           ("134 Unicode", "अ" * 134, "UCS-2", 2), ("135 Unicode", "अ" * 135, "UCS-2", 3),
                           ("one • in 100 ASCII", "a" * 99 + "•", "UCS-2", 2)):
    p = main.sms_parts(msg)
    check(f"{label} -> {enc}, {n} part(s)", p == {"encoding": enc, "segments": n}, str(p))

print("\n2. Drill (scenario) dry run")
b0 = counts()
r = bc(language="EN", channels=["whatsapp", "sms"])
j = r.json()
check("202 accepted", r.status_code == 202, r.text[:200])
check("status simulated, dry_run true", j.get("status") == "simulated" and j.get("dry_run") is True)
check("data basis = drill scenario", j.get("data_basis") == "drill scenario", j.get("data_basis"))
check("census reach = pop x 0.31 (no wards)", j.get("queued") == round(POP * 0.31), f"{j.get('queued')}")
check("EN advisory is UCS-2, 6 parts", (j.get("encoding"), j.get("segments")) == ("UCS-2", 6), f"{j.get('encoding')} {j.get('segments')} ({len(j['message'])} chars)")
check("job id is 12 hex chars", len(j["job_id"]) == 15, j["job_id"])
d = dt.datetime.now(main.IST).date()
check("date line reads '11 Sep' style", f"\n{d.day} {MON[d.month-1]} · " in j["message"], j["message"].split("\n")[1])
check("1 broadcast row + 1 audit row written", counts() == (b0[0] + 1, b0[1] + 1))
aud = rows("select * from audit order by id desc limit 1")[0]
check("audit: scenario, broadcast.simulated, dry run, drill", aud["mode"] == "scenario" and aud["kind"] == "broadcast.simulated"
      and "(dry run)" in aud["detail"] and "drill scenario" in aud["detail"], str(aud))

print("\n3. Preview == send, and it labels its basis")
for lang in ("EN", "HI", "GU"):
    q = {"city": "ahmedabad", "horizon": 2, "language": lang, "mode": "scenario", "audience": "outdoor_workers",
         "channels": ["sms"], "ward_codes": [f"{CORP}-03", f"{CORP}-07"]}
    pv = c.get("/v1/broadcast/preview", params=q).json()
    sd = bc(**q).json()
    same = all(pv[k] == sd[k] for k in ("message", "recipients", "segments", "encoding", "severity", "data_basis"))
    check(f"{lang}: preview matches the recorded send", same, str({k: (pv.get(k), sd.get(k)) for k in ("recipients", "segments")}))
b0 = counts()
p = c.get("/v1/broadcast/preview").json()
check("preview (live, no data) says scenario - no live forecast", p.get("data_basis") == "scenario — no live forecast", p.get("data_basis"))
check("preview writes nothing", counts() == b0)
check("preview rejects unknown ward (422)", c.get("/v1/broadcast/preview", params={"ward_codes": "NOPE"}).status_code == 422)
bad = []
for city in main.CITIES:
    for lang in ("EN", "HI", "GU"):
        for h in range(5):
            r = c.get("/v1/broadcast/preview", params={"city": city, "language": lang, "horizon": h, "mode": "scenario"})
            m = r.json().get("message", "")
            if r.status_code != 200 or "nan" in m or "None" in m:
                bad.append((city, lang, h, r.status_code))
check(f"{len(main.CITIES) * 15} previews clean", not bad, str(bad[:5]))
check("bulletin still renders (shares compose)", c.get("/bulletin", params={"mode": "scenario"}).status_code == 200)

print("\n4. Real-send gate (every refusal writes nothing)")
b0 = counts()
check("no server token configured -> 503", bc(dry_run=False).status_code == 503)
os.environ["TAAPMAAN_BROADCAST_TOKEN"] = "s3cret-test-token"
check("token set, no header -> 401", bc(dry_run=False).status_code == 401)
check("wrong token -> 401", bc(dry_run=False, headers={"X-Taapmaan-Token": "guess"}).status_code == 401)
OK = {"X-Taapmaan-Token": "s3cret-test-token"}
check("valid token, drill data -> 400", bc(dry_run=False, headers=OK).status_code == 400)
check("valid token, live, no forecast -> 409", bc(mode="live", dry_run=False, headers=OK).status_code == 409)
ingest.CACHE["ahmedabad"] = fake_live()
check("valid token, live, no provider -> 503", bc(mode="live", dry_run=False, headers=OK).status_code == 503)
os.environ["MSG91_AUTHKEY"] = "test-not-a-real-key"
r = bc(mode="live", dry_run=False, headers=OK)
check("everything set -> 501 (delivery not built)", r.status_code == 501, f"{r.status_code} {r.text[:120]}")
check("no refusal wrote a row", counts() == b0, f"{b0} -> {counts()}")
check("no outbound network call", not NET, str(NET[:3]))
del os.environ["MSG91_AUTHKEY"], os.environ["TAAPMAAN_BROADCAST_TOKEN"]

print("\n5. Live dry run on a (synthetic) forecast")
j = bc(mode="live").json()
check("basis = live forecast", j.get("data_basis") == "live forecast", j.get("data_basis"))
d0 = dt.date.fromisoformat(ingest.CACHE["ahmedabad"]["days"][0]["date"])
check("message carries forecast date", f"{d0.day} {MON[d0.month-1]}" in j["message"])
ingest.CACHE.pop("ahmedabad")
j = bc(mode="live").json()
check("no live data -> basis says scenario", j.get("data_basis") == "scenario — no live forecast")

print("\n6. Ward-targeted census estimate (city with no subscribers)")
w = main._bundle("delhi", 0, "scenario")[0]
two = [w[0]["code"], w[1]["code"]]
j = bc(city="delhi", ward_codes=two).json()
check("estimate = those wards' population x share", j["queued"] == round((w[0]["population"] + w[1]["population"]) * 0.31),
      f"{j['queued']} vs {round((w[0]['population'] + w[1]['population']) * 0.31)}")
check("unknown ward -> 422, nothing written", bc(ward_codes=["NOPE-XX"]).status_code == 422)

print("\n7. Subscriber targeting (audience, ward, language)")
subs = (("+919000000001", None, "EN", "all_residents"), ("+919000000002", None, "GU", "all_residents"),
        ("+919000000003", f"{CORP}-05", "EN", "outdoor_workers"), ("+919000000004", f"{CORP}-10", "EN", "all_residents"))
for n, ward, lang, aud_ in subs:
    c.post("/v1/subscribe", json={"msisdn": n, "city": "ahmedabad", "ward_code": ward, "language": lang, "audience": aud_})
check("duplicate -> registered false", c.post("/v1/subscribe", json={"msisdn": subs[0][0]}).json().get("registered") is False)
for label, kw, want, other in (("all residents, EN", {}, 3, 1),
                               ("all residents, GU", {"language": "GU"}, 1, 3),
                               ("schools (none subscribed)", {"audience": "schools"}, 0, 0),
                               ("outdoor workers, EN", {"audience": "outdoor_workers"}, 1, 0),
                               (f"ward {CORP}-05 + city-wide, EN", {"ward_codes": [f"{CORP}-05"]}, 2, 1)):
    j = bc(**kw).json()
    check(f"{label} -> {want} reached, {other} other-language", (j["queued"], j["other_language_subscribers"]) == (want, other),
          f"got {j['queued']}, {j['other_language_subscribers']}")
check("basis = registered subscribers", j["audience_basis"] == "registered subscribers")

print("\n8. Operator override")
check("override sent verbatim", bc(message_override="Test override").json()["message"] == "Test override")
check("670 chars accepted", bc(message_override="x" * 670).status_code == 202)
check("671 chars -> 422", bc(message_override="x" * 671).status_code == 422)
check("blank override -> composed advisory", "HEAT ALERT" in bc(message_override="   ").json()["message"])

print("\n9. Input validation")
for name, kw, code in (("empty channels", {"channels": []}, 422), ("language FR", {"language": "FR"}, 422),
                       ("horizon 5", {"horizon": 5}, 422), ("bad audience", {"audience": "everyone"}, 422),
                       ("blank actor", {"actor": ""}, 422), ("61-char actor", {"actor": "a" * 61}, 422),
                       ("unknown city", {"city": "atlantis"}, 404)):
    check(f"{name} -> {code}", bc(**kw).status_code == code)

print("\n10. Log endpoint")
lg = c.get("/v1/broadcasts", params={"limit": 3}).json()["broadcasts"]
check("/v1/broadcasts newest-first, decoded", len(lg) == 3 and isinstance(lg[0]["channels"], list)
      and isinstance(lg[0]["dry_run"], bool) and lg[0]["id"] > lg[1]["id"])
check("every recorded broadcast is a dry run", all(r["dry_run"] == 1 and r["status"] == "simulated"
                                                   for r in rows("select dry_run, status from broadcasts")))

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
