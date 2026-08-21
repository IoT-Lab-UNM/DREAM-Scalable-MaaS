import json
import os
import sqlite3
import uuid

from core import iso_now


class JobStore:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._initialize()

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _initialize(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    device_id TEXT NOT NULL,
                    device_kind TEXT NOT NULL,
                    action TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    command_id TEXT NOT NULL UNIQUE,
                    envelope_b64 TEXT,
                    state TEXT NOT NULL,
                    policy_decision TEXT NOT NULL DEFAULT 'NOT_EVALUATED',
                    sla_class TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    dispatched_at TEXT,
                    completed_at TEXT,
                    last_error TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    event_time TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state);
                CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id, id);
                """
            )

    @staticmethod
    def _job(row):
        if row is None:
            return None
        item = dict(row)
        item["parameters"] = json.loads(item.pop("parameters_json"))
        return item

    def create(self, device_id, device_kind, action, parameters, idempotency_key, sla_class):
        job_id = str(uuid.uuid4())
        command_id = f"job-{job_id}"
        now = iso_now()
        try:
            with self.connect() as conn:
                conn.execute(
                    """INSERT INTO jobs
                    (id,idempotency_key,device_id,device_kind,action,parameters_json,
                     command_id,state,sla_class,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        job_id,
                        idempotency_key,
                        device_id,
                        device_kind,
                        action,
                        json.dumps(parameters, separators=(",", ":")),
                        command_id,
                        "QUEUED",
                        sla_class,
                        now,
                        now,
                    ),
                )
                self._event(conn, job_id, "JOB_QUEUED", {"action": action})
        except sqlite3.IntegrityError:
            if idempotency_key:
                with self.connect() as conn:
                    return self._job(
                        conn.execute(
                            "SELECT * FROM jobs WHERE idempotency_key=?", (idempotency_key,)
                        ).fetchone()
                    ), False
            raise
        return self.get(job_id), True

    def _event(self, conn, job_id, event_type, details):
        conn.execute(
            "INSERT INTO events(job_id,event_time,event_type,details_json) VALUES(?,?,?,?)",
            (job_id, iso_now(), event_type, json.dumps(details, separators=(",", ":"))),
        )

    def add_event(self, job_id, event_type, details):
        with self.connect() as conn:
            self._event(conn, job_id, event_type, details)

    def get(self, job_id):
        with self.connect() as conn:
            return self._job(conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    def list(self, limit=100):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._job(row) for row in rows]

    def events(self, job_id):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE job_id=? ORDER BY id", (job_id,)
            ).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["details"] = json.loads(item.pop("details_json"))
                result.append(item)
            return result

    def update_state(self, job_id, state, event_type, details=None, **fields):
        fields = dict(fields)
        fields["state"] = state
        fields["updated_at"] = iso_now()
        allowed = {
            "state", "updated_at", "dispatched_at", "completed_at", "last_error",
            "envelope_b64", "policy_decision"
        }
        if not set(fields).issubset(allowed):
            raise ValueError("unsupported job field")
        assignments = ",".join(f"{name}=?" for name in fields)
        values = list(fields.values()) + [job_id]
        with self.connect() as conn:
            conn.execute(f"UPDATE jobs SET {assignments} WHERE id=?", values)
            self._event(conn, job_id, event_type, details or {})
        return self.get(job_id)

    def active(self):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE state IN ('DISPATCHED','ACKNOWLEDGED')"
            ).fetchall()
            return [self._job(row) for row in rows]
