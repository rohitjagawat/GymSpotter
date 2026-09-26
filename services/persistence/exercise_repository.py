"""Connection-per-operation SQLite storage; no credentials in session history."""
from contextlib import contextmanager
from pathlib import Path
import os, sqlite3, json
from services.config.workout_config import ROOT

def db_path():
    return Path(os.environ.get("GYMSPOTTER_DB", str(ROOT / "data.db")))

@contextmanager
def connection():
    conn = sqlite3.connect(str(db_path()), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    db_path().parent.mkdir(parents=True, exist_ok=True)
    with connection() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript("""
        CREATE TABLE IF NOT EXISTS accounts(
          id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
          display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS login_limits(
          username TEXT PRIMARY KEY, failures INTEGER NOT NULL, blocked_until REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS workouts(
          id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES accounts(id),
          exercise TEXT NOT NULL, kind TEXT NOT NULL, target_sets INTEGER NOT NULL,
          target_amount INTEGER NOT NULL, reps INTEGER NOT NULL DEFAULT 0,
          sets INTEGER NOT NULL DEFAULT 0, hold_seconds REAL NOT NULL DEFAULT 0,
          active_seconds REAL NOT NULL DEFAULT 0, score REAL,
          status TEXT NOT NULL, details TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS workout_owner ON workouts(user_id, created_at);
        """)

def save_workout(user_id, workout_id, exercise, plan, snapshot, status="active"):
    # Upsert absolute counters so repeated refreshes cannot double count.
    details = json.dumps({"records": snapshot.get("records", []),
                          "issues": snapshot.get("issue_counts", {})})
    with connection() as c:
        c.execute("""INSERT INTO workouts
        (id,user_id,exercise,kind,target_sets,target_amount,reps,sets,hold_seconds,
         active_seconds,score,status,details) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
          reps=excluded.reps, sets=excluded.sets, hold_seconds=excluded.hold_seconds,
          active_seconds=excluded.active_seconds, score=excluded.score,
          status=excluded.status, details=excluded.details, updated_at=CURRENT_TIMESTAMP
        WHERE workouts.user_id=excluded.user_id""",
        (workout_id,user_id,exercise,plan['kind'],plan['sets'],plan['amount'],
         snapshot.get('reps',0),snapshot.get('sets',0),snapshot.get('hold_seconds',0),
         snapshot.get('active_seconds',0),snapshot.get('score'),status,details))

def history(user_id):
    with connection() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM workouts WHERE user_id=? ORDER BY created_at DESC", (user_id,))]
