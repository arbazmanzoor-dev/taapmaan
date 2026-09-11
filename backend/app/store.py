"""SQLite persistence: alert log, broadcast log, subscribers, HAP trigger state.

SQLite because a hackathon does not need Postgres to be credible. The schema
ports to Postgres unchanged apart from the AUTOINCREMENT keyword.
"""
from __future__ import annotations
import datetime as dt, hashlib, json, os, pathlib, sqlite3, threading

DB_PATH = pathlib.Path(os.environ.get("TAAPMAAN_DB", pathlib.Path(__file__).resolve().parent.parent / "data" / "taapmaan.db"))
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, city TEXT NOT NULL, severity TEXT NOT NULL,
  title TEXT NOT NULL, body TEXT NOT NULL, meta TEXT);
CREATE TABLE IF NOT EXISTS broadcasts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT UNIQUE NOT NULL, ts TEXT NOT NULL, city TEXT NOT NULL,
  severity TEXT, audience TEXT, channels TEXT, language TEXT,
  ward_codes TEXT, recipients INTEGER, delivered INTEGER,
  status TEXT NOT NULL, dry_run INTEGER NOT NULL, message TEXT);
CREATE TABLE IF NOT EXISTS subscribers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, phone_hash TEXT UNIQUE NOT NULL, city TEXT NOT NULL,
  ward_code TEXT, language TEXT NOT NULL, audience TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS trigger_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, city TEXT NOT NULL, trigger_id TEXT NOT NULL,
  ward_code TEXT, htsi REAL, threshold REAL, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  city TEXT NOT NULL, mode TEXT NOT NULL, action_id TEXT NOT NULL,
  status TEXT NOT NULL, activated_at TEXT NOT NULL, due_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, updated_by TEXT, note TEXT,
  UNIQUE(city, mode, action_id));
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, city TEXT NOT NULL, mode TEXT NOT NULL,
  actor TEXT, kind TEXT NOT NULL, ref TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS users (
  username TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, department TEXT,
  pw_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY, username TEXT NOT NULL,
  created_at TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_audit_city ON audit(city, mode, id);
CREATE INDEX IF NOT EXISTS ix_alerts_city ON alerts(city, ts);
CREATE INDEX IF NOT EXISTS ix_trig_city ON trigger_events(city, ts);
"""

def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init() -> None:
    with _lock, _conn() as c:
        c.executescript(SCHEMA)

def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

def hash_phone(msisdn: str) -> str:
    """Store a salted hash, never the number itself."""
    salt = os.environ.get("TAAPMAAN_SALT", "taapmaan-dev-salt")
    return hashlib.sha256((salt + msisdn.strip()).encode()).hexdigest()

def log_broadcast(rec: dict) -> None:
    with _lock, _conn() as c:
        c.execute(
            """INSERT INTO broadcasts
               (job_id, ts, city, severity, audience, channels, language,
                ward_codes, recipients, delivered, status, dry_run, message)
               VALUES (:job_id,:ts,:city,:severity,:audience,:channels,:language,
                       :ward_codes,:recipients,:delivered,:status,:dry_run,:message)""",
            {**rec, "channels": json.dumps(rec["channels"]),
             "ward_codes": json.dumps(rec["ward_codes"])})

def list_broadcasts(limit: int = 25) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute("SELECT * FROM broadcasts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["channels"] = json.loads(d["channels"] or "[]")
        d["ward_codes"] = json.loads(d["ward_codes"] or "[]")
        d["dry_run"] = bool(d["dry_run"])
        out.append(d)
    return out

def add_subscriber(msisdn: str, city: str, ward: str | None, lang: str, audience: str) -> bool:
    """Returns False if already registered. The raw number is never stored."""
    try:
        with _lock, _conn() as c:
            c.execute("""INSERT INTO subscribers (ts, phone_hash, city, ward_code, language, audience)
                         VALUES (?,?,?,?,?,?)""",
                      (now(), hash_phone(msisdn), city, ward, lang, audience))
        return True
    except sqlite3.IntegrityError:
        return False

def count_subscribers(city: str | None = None) -> int:
    with _lock, _conn() as c:
        if city:
            return c.execute("SELECT COUNT(*) FROM subscribers WHERE city=?", (city,)).fetchone()[0]
        return c.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]

def count_targeted(city: str, audience: str, wards: list[str], language: str) -> dict:
    """Who a broadcast reaches. 'all_residents' means every audience; ward codes
    narrow it to those wards plus city-wide subscribers (no ward on file). One
    message has one language, so other-language subscribers are counted, not reached."""
    q, args = "SELECT language, COUNT(*) n FROM subscribers WHERE city=?", [city]
    if audience != "all_residents":
        q += " AND audience=?"; args.append(audience)
    if wards:
        q += f" AND (ward_code IS NULL OR ward_code IN ({','.join('?' * len(wards))}))"; args += wards
    with _lock, _conn() as c:
        by_lang = {r["language"]: r["n"] for r in c.execute(q + " GROUP BY language", args)}
    matched = by_lang.get(language, 0)
    return {"matched": matched, "other_language": sum(by_lang.values()) - matched}

def log_trigger(city: str, trigger_id: str, ward: str | None,
                htsi: float, threshold: float, state: str) -> None:
    with _lock, _conn() as c:
        c.execute("""INSERT INTO trigger_events (ts, city, trigger_id, ward_code, htsi, threshold, state)
                     VALUES (?,?,?,?,?,?,?)""",
                  (now(), city, trigger_id, ward, htsi, threshold, state))

def recent_triggers(city: str, limit: int = 40) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute("""SELECT * FROM trigger_events WHERE city=?
                            ORDER BY id DESC LIMIT ?""", (city, limit)).fetchall()
    return [dict(r) for r in rows]


# ---- Heat Action Plan action state ------------------------------------------
# `mode` separates live operations from drills. A drill run on the May-peak
# scenario must never be mixed into the live record, or the post-season review
# and any RTI response would count rehearsals as real interventions.

def get_actions(city: str, mode: str) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute("SELECT * FROM actions WHERE city=? AND mode=?", (city, mode)).fetchall()
    return [dict(r) for r in rows]

def activate_action(city: str, mode: str, action_id: str, deadline_hours: float) -> tuple[dict, bool]:
    """Returns (row, created). `created` is True only for the call that inserted."""
    t = dt.datetime.now(dt.timezone.utc)
    rec = {"city": city, "mode": mode, "action_id": action_id, "status": "pending",
           "activated_at": t.isoformat(timespec="seconds"),
           "due_at": (t + dt.timedelta(hours=deadline_hours)).isoformat(timespec="seconds"),
           "updated_at": t.isoformat(timespec="seconds"), "updated_by": "system", "note": None}
    with _lock, _conn() as c:
        cur = c.execute("""INSERT OR IGNORE INTO actions
                     (city, mode, action_id, status, activated_at, due_at, updated_at, updated_by, note)
                     VALUES (:city,:mode,:action_id,:status,:activated_at,:due_at,:updated_at,:updated_by,:note)""", rec)
        created = cur.rowcount == 1
        row = c.execute("SELECT * FROM actions WHERE city=? AND mode=? AND action_id=?",
                        (city, mode, action_id)).fetchone()
    return dict(row), created

def set_action_status(city: str, mode: str, action_id: str, status: str,
                      actor: str, note: str | None) -> dict | None:
    with _lock, _conn() as c:
        cur = c.execute("""UPDATE actions SET status=?, updated_at=?, updated_by=?, note=COALESCE(?, note)
                           WHERE city=? AND mode=? AND action_id=?""",
                        (status, now(), actor, note, city, mode, action_id))
        if cur.rowcount == 0:
            return None
        row = c.execute("SELECT * FROM actions WHERE city=? AND mode=? AND action_id=?",
                        (city, mode, action_id)).fetchone()
    return dict(row)

def reset_actions(city: str, mode: str) -> int:
    with _lock, _conn() as c:
        return c.execute("DELETE FROM actions WHERE city=? AND mode=?", (city, mode)).rowcount

def audit(city: str, mode: str, actor: str, kind: str, ref: str | None, detail: str) -> None:
    with _lock, _conn() as c:
        c.execute("INSERT INTO audit (ts, city, mode, actor, kind, ref, detail) VALUES (?,?,?,?,?,?,?)",
                  (now(), city, mode, actor, kind, ref, detail))

def list_audit(city: str, mode: str, limit: int = 50) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute("""SELECT ts, city, mode, actor, kind, ref, detail FROM audit
                            WHERE city=? AND mode=? ORDER BY id DESC LIMIT ?""",
                         (city, mode, limit)).fetchall()
    return [dict(r) for r in rows]


# ---- official accounts and sessions -------------------------------------------

def create_user(username: str, name: str, role: str, department: str | None,
                pw_hash: str, only_if_missing: bool = False) -> bool:
    """With only_if_missing an existing username returns False; otherwise it raises."""
    with _lock, _conn() as c:
        cur = c.execute(f"INSERT {'OR IGNORE ' if only_if_missing else ''}INTO users "
                        "(username, name, role, department, pw_hash, active, created_at) VALUES (?,?,?,?,?,1,?)",
                        (username, name, role, department, pw_hash, now()))
    return cur.rowcount == 1

def get_user(username: str) -> dict | None:
    with _lock, _conn() as c:
        r = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    return dict(r) if r else None

def list_users() -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute("""SELECT * FROM users ORDER BY CASE role WHEN 'admin' THEN 0
                            WHEN 'operator' THEN 1 WHEN 'department' THEN 2 ELSE 3 END, username""").fetchall()
    return [dict(r) for r in rows]

def update_user(username: str, **fields) -> None:
    sets = [(k, v) for k, v in fields.items() if k in {"name", "role", "department", "pw_hash", "active"}]
    if sets:
        with _lock, _conn() as c:
            c.execute(f"UPDATE users SET {', '.join(k + '=?' for k, _ in sets)} WHERE username=?",
                      [v for _, v in sets] + [username])

def create_session(token_hash: str, username: str, hours: float) -> None:
    exp = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=hours)).isoformat(timespec="seconds")
    with _lock, _conn() as c:
        c.execute("DELETE FROM sessions WHERE expires_at < ?", (now(),))
        c.execute("INSERT INTO sessions (token_hash, username, created_at, expires_at) VALUES (?,?,?,?)",
                  (token_hash, username, now(), exp))

def session_user(token_hash: str) -> dict | None:
    with _lock, _conn() as c:
        r = c.execute("""SELECT u.* FROM sessions s JOIN users u ON u.username = s.username
                         WHERE s.token_hash=? AND s.expires_at > ?""", (token_hash, now())).fetchone()
    return dict(r) if r else None

def delete_session(token_hash: str) -> None:
    with _lock, _conn() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))

def delete_user_sessions(username: str) -> None:
    with _lock, _conn() as c:
        c.execute("DELETE FROM sessions WHERE username=?", (username,))
