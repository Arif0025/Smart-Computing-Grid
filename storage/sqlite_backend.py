import sqlite3
from contextlib import contextmanager
from typing import List
from main import GridState, OptimizationEvent

class SQLiteStorage:
    def __init__(self, db_path: str = "./grid_history.db"):
        self.db_path = db_path
        self._init_schema()
    
    def _init_schema(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS grid_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grid_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    total_power REAL,
                    avg_load REAL,
                    avg_temperature REAL,
                    unoptimized_power REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS node_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grid_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    load REAL, temperature REAL, power_watts REAL,
                    fan_speed REAL, status TEXT, source TEXT, reading_quality TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS optimizer_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grid_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    action TEXT, source_id TEXT, target_id TEXT,
                    amount REAL, reason TEXT, priority TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_time ON grid_snapshots(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_node ON node_readings(node_id, timestamp)")
    
    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def save_snapshot(self, grid_id: str, state: GridState):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO grid_snapshots (grid_id, timestamp, total_power, avg_load, avg_temperature, unoptimized_power) VALUES (?,?,?,?,?,?)",
                (grid_id, state.timestamp, state.total_power, state.avg_load, state.avg_temperature, state.unoptimized_power)
            )
    
    def save_optimizer_event(self, grid_id: str, event: OptimizationEvent):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO optimizer_events (grid_id, timestamp, action, source_id, target_id, amount, reason, priority) VALUES (?,?,?,?,?,?,?,?)",
                (grid_id, event.timestamp, event.action, event.source_id, event.target_id, event.amount, event.reason, event.priority)
            )
    
    def get_history(self, grid_id: str, limit: int = 100) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM grid_snapshots WHERE grid_id=? ORDER BY timestamp DESC LIMIT ?",
                (grid_id, limit)
            ).fetchall()
        return [dict(r) for r in rows]
