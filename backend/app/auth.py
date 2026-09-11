"""Official accounts: per-person sign-in with roles, so the live audit trail names
the officer who acted instead of a self-declared label.

Roles
  admin       Municipal Commissioner / HAP Nodal Officer: everything, and manages accounts
  operator    Control room: every live action, live-mode broadcasts, bulletins, re-ingest
  department  One department's officer: that department's live actions only
  viewer      District Collector / state observer: sees everything, changes nothing

Sign-in is on when TAAPMAAN_DEMO_PASSWORD or TAAPMAAN_OPERATOR_TOKEN is set, as on
a public deployment. Unset, as on a laptop, the console stays open with no accounts.
The public dashboard and May-peak drills never need an account.

Passwords: scrypt with a per-user salt. Sessions: a random token in an HttpOnly,
SameSite=Strict cookie; only its SHA-256 is stored, so a copied database holds no
usable session.
"""
from __future__ import annotations
import base64, hashlib, hmac, os, secrets, threading, time

from . import sop, store

ROLES = {"admin": "Administrator", "operator": "Control-room operator",
         "department": "Department officer", "viewer": "Viewer"}
SESSION_COOKIE = "taapmaan_session"
SESSION_HOURS = 12
DEPT_NAME = {d["id"]: d["name"] for d in sop.DEPARTMENTS}

# Recreated at start-up with the server's demo password (never overwritten). On a
# host whose disk resets -- Render's free tier -- that is how accounts survive a restart.
DEMO = [
    ("commissioner",   "Municipal Commissioner",     "admin",      None),
    ("control.room",   "Control Room Operator",      "operator",   None),
    ("health.officer", "Chief Medical Officer",      "department", "health"),
    ("water.officer",  "Executive Engineer (Water)", "department", "water"),
    ("collector",      "District Collector",         "viewer",     None),
]

def demo_password() -> str | None:
    return os.environ.get("TAAPMAAN_DEMO_PASSWORD") or os.environ.get("TAAPMAAN_OPERATOR_TOKEN") or None

def enabled() -> bool:
    return demo_password() is not None

# ---- passwords ----------------------------------------------------------------

def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${base64.b64encode(salt).decode()}${base64.b64encode(h).decode()}"

def check_password(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(got, base64.b64decode(h))
    except (ValueError, TypeError):
        return False

# checked against when the username does not exist, so both cases take equally long
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))

# ---- sign-in throttle: 5 failures on an account within 15 min locks it for 15 min ----

WINDOW_S, MAX_FAILS = 15 * 60, 5
_fails: dict[str, list[float]] = {}
_fail_lock = threading.Lock()

def locked(username: str) -> bool:
    with _fail_lock:
        t = time.time()
        recent = [x for x in _fails.get(username, []) if t - x < WINDOW_S]
        _fails[username] = recent
        return len(recent) >= MAX_FAILS

def note_failure(username: str) -> None:
    with _fail_lock:
        _fails.setdefault(username, []).append(time.time())

def clear_failures(username: str) -> None:
    with _fail_lock:
        _fails.pop(username, None)

# ---- sessions -----------------------------------------------------------------

def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def start_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    store.create_session(_digest(token), username, SESSION_HOURS)
    return token

def user_for(token: str | None) -> dict | None:
    if not token:
        return None
    u = store.session_user(_digest(token))
    return public(u) if u and u["active"] else None

def end_session(token: str | None) -> None:
    if token:
        store.delete_session(_digest(token))

# ---- who may do what ----------------------------------------------------------

def public(u: dict) -> dict:
    return {"username": u["username"], "name": u["name"], "role": u["role"], "role_label": ROLES[u["role"]],
            "department": u["department"], "department_name": DEPT_NAME.get(u["department"]),
            "active": bool(u["active"])}

def actor_label(u: dict) -> str:
    return f"{u['name']} ({u['department_name'] if u['role'] == 'department' else u['role_label']})"

def can_act_live(u: dict | None, department: str) -> bool:
    return u is not None and (u["role"] in ("admin", "operator")
                              or (u["role"] == "department" and u["department"] == department))

def can_operate(u: dict | None) -> bool:
    """Live-mode broadcasts, bulletins on the record, a forced re-ingest."""
    return u is not None and u["role"] in ("admin", "operator")

def seed_demo_accounts() -> int:
    pw = demo_password()
    if not pw:
        return 0
    return sum(store.create_user(name, full, role, dept, hash_password(pw), only_if_missing=True)
               for name, full, role, dept in DEMO)
