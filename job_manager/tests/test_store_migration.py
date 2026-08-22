import os
import sqlite3
import tempfile
import unittest

from store import JobStore


class StoreMigrationTests(unittest.TestCase):
    def test_adds_sla_decision_to_existing_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "jobs.db")
            with sqlite3.connect(path) as conn:
                conn.execute(
                    """CREATE TABLE jobs (
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
                    )"""
                )
            store = JobStore(path)
            with store.connect() as conn:
                columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
            self.assertIn("sla_decision", columns)


if __name__ == "__main__":
    unittest.main()
