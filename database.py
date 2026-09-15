import os
import sqlite3
from datetime import datetime, timezone


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "websentinel.db",
)


def get_connection():
    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS scans (
            id TEXT PRIMARY KEY,
            target TEXT NOT NULL,
            status TEXT NOT NULL,
            stage TEXT,
            progress INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            json_report TEXT,
            html_report TEXT,
            error TEXT
        )
        """
    )

    connection.commit()

    connection.close()


# =========================================================
# USERS
# =========================================================

def create_user(
    name,
    email,
    password_hash,
):
    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            INSERT INTO users (
                name,
                email,
                password_hash,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                email,
                password_hash,
                datetime.now(
                    timezone.utc
                ).isoformat(),
            ),
        )

        connection.commit()

        return cursor.lastrowid

    except sqlite3.IntegrityError:
        return None

    finally:
        connection.close()


def get_user_by_email(email):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)


# =========================================================
# SCANS
# =========================================================

def create_scan_record(
    scan_id,
    target,
    status="QUEUED",
    stage="Waiting to start",
    progress=0,
):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO scans (
            id,
            target,
            status,
            stage,
            progress,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            scan_id,
            target,
            status,
            stage,
            progress,
            datetime.now(
                timezone.utc
            ).isoformat(),
        ),
    )

    connection.commit()
    connection.close()


def update_scan_record(
    scan_id,
    **values,
):
    if not values:
        return

    allowed_columns = {
        "status",
        "stage",
        "progress",
        "started_at",
        "finished_at",
        "json_report",
        "html_report",
        "error",
    }

    updates = []
    parameters = []

    for key, value in values.items():

        if key not in allowed_columns:
            continue

        updates.append(
            f"{key} = ?"
        )

        parameters.append(value)

    if not updates:
        return

    parameters.append(scan_id)

    connection = get_connection()

    connection.execute(
        f"""
        UPDATE scans
        SET {", ".join(updates)}
        WHERE id = ?
        """,
        parameters,
    )

    connection.commit()
    connection.close()


def get_scan_record(scan_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT *
        FROM scans
        WHERE id = ?
        """,
        (scan_id,),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)


def get_scan_history(limit=20):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT *
        FROM scans
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]