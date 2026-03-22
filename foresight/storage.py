import sqlite3
from pathlib import Path


DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "foresight.db"

VALID_METRICS = {
    "cpu_percent",
    "ram_percent",
    "ram_used_mb",
    "disk_percent",
    "disk_used_gb",
}


def init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT    NOT NULL,
            cpu_percent   REAL    NOT NULL,
            ram_percent   REAL    NOT NULL,
            ram_used_mb   REAL    NOT NULL,
            ram_total_mb  REAL    NOT NULL,
            disk_percent  REAL    NOT NULL,
            disk_used_gb  REAL    NOT NULL,
            disk_total_gb REAL    NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_snapshot(snapshot: dict) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO snapshots (
            timestamp,
            cpu_percent,
            ram_percent,
            ram_used_mb,
            ram_total_mb,
            disk_percent,
            disk_used_gb,
            disk_total_gb
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        snapshot["timestamp"],
        snapshot["cpu_percent"],
        snapshot["ram_percent"],
        snapshot["ram_used_mb"],
        snapshot["ram_total_mb"],
        snapshot["disk_percent"],
        snapshot["disk_used_gb"],
        snapshot["disk_total_gb"],
    ))

    conn.commit()
    conn.close()


def get_snapshots(limit: int = 100) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM snapshots
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_metric_series(metric: str, limit: int = 50) -> tuple[list, list]:
    if metric not in VALID_METRICS:
        raise ValueError(
            f"Invalid metric '{metric}'. "
            f"Choose from: {VALID_METRICS}"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT timestamp, {metric}
        FROM snapshots
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    rows = list(reversed(rows))
    timestamps = [row["timestamp"] for row in rows]
    values = [row[metric] for row in rows]

    return timestamps, values


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DB_PATH}")

    dummy = {
        "timestamp": "2026-03-22T10:00:00",
        "cpu_percent": 45.2,
        "ram_percent": 61.0,
        "ram_used_mb": 9800.0,
        "ram_total_mb": 16384.0,
        "disk_percent": 43.0,
        "disk_used_gb": 430.0,
        "disk_total_gb": 953.0,
    }

    save_snapshot(dummy)
    print("Saved one dummy snapshot.")

    results = get_snapshots(limit=5)
    print(f"\nLast {len(results)} snapshots:")
    for row in results:
        print(row)