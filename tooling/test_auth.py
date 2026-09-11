"""Official sign-in and roles. Throwaway DB, no network.

usage: backend/.venv/bin/python tooling/test_auth.py backend <tmp_dir>
"""
import datetime as dt, math, os, pathlib, socket, sqlite3, sys

BACKEND, TMP = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
TMP.mkdir(parents=True, exist_ok=True)
DB = TMP / "auth_test.db"
DB.unlink(missing_ok=True)
PW = "correct-horse-battery-staple"
os.environ["TAAPMAAN_DB"] = str(DB)
os.environ["TAAPMAAN_OPERATOR_TOKEN"] = PW
os.environ.pop("TAAPMAAN_DEMO_PASSWORD", None)

def _no_net(*a, **k):
    raise OSError("network disabled in test")
socket.socket.connect = _no_net
socket.create_connection = _no_net

sys.path.insert(0, str(BACKEND))
from fastapi.testclient import TestClient
from app import auth, main, ingest, store, thermal as T

store.init()
ingest.CACHE_DIR = TMP / "cache"
PASS, FAIL = [], []
def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  PASS " if ok else "  FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))

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

ingest.CACHE["ahmedabad"] = fake_live()
check("5 demo accounts seeded", auth.seed_demo_accounts() == 5)
check("seeding again changes nothing", auth.seed_demo_accounts() == 0)
main.activate_live_actions()

def client(username=None, password=PW):
    c = TestClient(main.app)
    if username:
        r = c.post("/v1/auth/login", json={"username": username, "password": password})
        assert r.status_code == 200, (username, r.status_code, r.text)
    return c
def action(dept, mode="live"):
    acts = TestClient(main.app).get(f"/v1/command?city=ahmedabad&mode={mode}").json()["actions"]
    return next(a for a in acts if a["active"] and a["department"] == dept)
def move(c, a, status, mode="live"):
    return c.post("/v1/command/action", json={"city": "ahmedabad", "mode": mode, "action_id": a["id"],
                                                "status": status, "actor": "Typed Name"})
last_actor = lambda: store.list_audit("ahmedabad", "live", 1)[0]["actor"]

print("\n1. Public visitor")
v = client()
me = v.get("/v1/auth/me").json()
check("me: sign-in on, nobody signed in", me["enabled"] is True and me["user"] is None)
check("me: demo usernames listed, no passwords", len(me["demo"]) == 5 and PW not in str(me))
check("live action -> 401", move(v, action("health"), "acknowledged").status_code == 401)
check("drill action allowed", move(v, action("health", "scenario"), "acknowledged", "scenario").status_code == 200)
check("live broadcast -> 401", v.post("/v1/broadcast", json={"mode": "live"}).status_code == 401)
check("drill broadcast allowed", v.post("/v1/broadcast", json={"mode": "scenario"}).status_code == 202)
check("user list -> 401", v.get("/v1/users").status_code == 401)

print("\n2. Signing in")
r = TestClient(main.app).post("/v1/auth/login", json={"username": "health.officer", "password": "nope"})
check("wrong password -> 401", r.status_code == 401)
check("unknown user -> same 401", TestClient(main.app).post("/v1/auth/login", json={"username": "ghost", "password": "x"}).status_code == 401)
for _ in range(5):
    TestClient(main.app).post("/v1/auth/login", json={"username": "water.officer", "password": "nope"})
r = TestClient(main.app).post("/v1/auth/login", json={"username": "water.officer", "password": PW})
check("5 failures lock the account (even the right password -> 429)", r.status_code == 429, r.status_code)
auth.clear_failures("water.officer")
r = TestClient(main.app).post("/v1/auth/login", json={"username": "Health.Officer ", "password": PW})
sc = r.headers.get("set-cookie", "").lower()
check("right password -> session cookie", r.status_code == 200 and "taapmaan_session=" in sc)
check("cookie HttpOnly + SameSite=Strict", "httponly" in sc and "samesite=strict" in sc)
token = r.cookies.get("taapmaan_session")
with sqlite3.connect(DB) as con:
    stored = [x[0] for x in con.execute("SELECT token_hash FROM sessions")]
    hashes = [x[0] for x in con.execute("SELECT pw_hash FROM users")]
check("raw session token not stored", token not in stored and len(stored) >= 1)
check("passwords stored as scrypt hashes", all(h.startswith("scrypt$") and PW not in h for h in hashes))

print("\n3. Department officer (Health)")
ho = client("health.officer")
check("me: role department, Health", ho.get("/v1/auth/me").json()["user"]["department"] == "health")
check("own department's live action saved", move(ho, action("health"), "acknowledged").status_code == 200)
check("audit names the officer, not the typed name", last_actor() == "Chief Medical Officer (Health)", last_actor())
check("another department's live action -> 403", move(ho, action("water"), "acknowledged").status_code == 403)
check("live broadcast -> 403", ho.post("/v1/broadcast", json={"mode": "live"}).status_code == 403)
check("user list -> 403", ho.get("/v1/users").status_code == 403)

print("\n4. Viewer (District Collector)")
vw = client("collector")
check("live action -> 403", move(vw, action("health"), "in_progress").status_code == 403)
check("can read the command board", vw.get("/v1/command?city=ahmedabad&mode=live").status_code == 200)

print("\n5. Control-room operator")
op = client("control.room")
check("any department's live action", move(op, action("water"), "acknowledged").status_code == 200)
check("live broadcast dry run", op.post("/v1/broadcast", json={"mode": "live"}).status_code == 202)
n0 = len(store.list_audit("ahmedabad", "live", 100000))
op.get("/bulletin?city=ahmedabad&mode=live")
check("live bulletin logged under the operator", len(store.list_audit("ahmedabad", "live", 100000)) == n0 + 1
      and last_actor() == "Control Room Operator (Control-room operator)", last_actor())
check("user list -> 403", op.get("/v1/users").status_code == 403)

print("\n6. Administrator")
ad = client("commissioner")
check("user list", ad.get("/v1/users").status_code == 200 and len(ad.get("/v1/users").json()["users"]) == 5)
r = ad.post("/v1/users", json={"username": "police.dcp", "name": "DCP Traffic", "role": "department",
                                "department": "police", "password": "temporary-pass-1"})
check("add a department officer", r.status_code == 201 and r.json()["department_name"] == "Police & traffic", r.text[:120])
check("duplicate username -> 409", ad.post("/v1/users", json={"username": "police.dcp", "name": "X Y", "role": "viewer",
                                                              "password": "temporary-pass-1"}).status_code == 409)
check("department officer without a department -> 422", ad.post("/v1/users", json={"username": "no.dept", "name": "No Dept",
      "role": "department", "password": "temporary-pass-1"}).status_code == 422)
check("short password -> 422", ad.post("/v1/users", json={"username": "short.pw", "name": "Short Pw", "role": "viewer",
                                                          "password": "short"}).status_code == 422)
pd = client("police.dcp", "temporary-pass-1")
check("new officer can sign in", pd.get("/v1/auth/me").json()["user"]["username"] == "police.dcp")
check("switch off an account", ad.patch("/v1/users/police.dcp", json={"active": False}).json()["active"] is False)
check("its open session ends at once", pd.get("/v1/auth/me").json()["user"] is None)
check("and it can no longer sign in", TestClient(main.app).post("/v1/auth/login",
      json={"username": "police.dcp", "password": "temporary-pass-1"}).status_code == 401)
check("cannot switch off yourself", ad.patch("/v1/users/commissioner", json={"active": False}).status_code == 400)

print("\n7. Signing out, API clients, change password")
op.post("/v1/auth/logout")
check("after sign-out the old cookie is useless", op.get("/v1/auth/me").json()["user"] is None)
r = TestClient(main.app).post("/v1/command/action", json={"city": "ahmedabad", "mode": "live",
      "action_id": action("water")["id"], "status": "in_progress"}, headers={"X-Taapmaan-Operator": PW})
check("operator token header works for API clients", r.status_code == 200, r.text[:100])
check("change own password", ho.post("/v1/auth/password", json={"current": PW, "new": "a-brand-new-pass"}).status_code == 200)
check("new password signs in", TestClient(main.app).post("/v1/auth/login",
      json={"username": "health.officer", "password": "a-brand-new-pass"}).status_code == 200)

print("\n8. Sign-in off (laptop: no password configured)")
del os.environ["TAAPMAAN_OPERATOR_TOKEN"]
check("me: sign-in off", TestClient(main.app).get("/v1/auth/me").json() | {"roles": 0, "departments": 0}
      == {"enabled": False, "user": None, "roles": 0, "departments": 0, "demo": []})
check("live action open again", move(TestClient(main.app), action("water"), "done").status_code == 200)

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
