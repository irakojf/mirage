"""
Database operations for Mirage Slack bot.

Uses Turso (libSQL) for cloud SQLite access.
Shared database between Slack bot and local Claude Code.
"""

import os
import uuid
from datetime import datetime
from typing import Optional
import libsql_experimental as libsql


def get_connection():
    """Get a connection to the Turso database."""
    url = os.environ.get("TURSO_DATABASE_URL")
    auth_token = os.environ.get("TURSO_AUTH_TOKEN")

    if not url:
        raise ValueError("TURSO_DATABASE_URL environment variable not set")

    if auth_token:
        return libsql.connect(url, auth_token=auth_token)
    else:
        # Local SQLite fallback for development
        return libsql.connect(url)


def create_task(
    content: str,
    bucket: str,
    estimated_minutes: Optional[int] = None,
    notes: Optional[str] = None
) -> dict:
    """
    Create a new task in the database.

    Returns the created task dict.
    """
    conn = get_connection()
    task_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    conn.execute(
        """
        INSERT INTO tasks (id, content, bucket, status, estimated_minutes, times_added, first_added_at, last_added_at, notes)
        VALUES (?, ?, ?, 'open', ?, 1, ?, ?, ?)
        """,
        (task_id, content, bucket, estimated_minutes, now, now, notes)
    )
    conn.commit()
    conn.close()

    return {
        "id": task_id,
        "content": content,
        "bucket": bucket,
        "estimated_minutes": estimated_minutes,
        "times_added": 1,
        "notes": notes
    }


def find_similar_task(content: str) -> Optional[dict]:
    """
    Find an existing open task that matches the content.

    This does exact matching - semantic matching is handled by Claude
    before calling this function.

    Returns the task if found, None otherwise.
    """
    conn = get_connection()
    cursor = conn.execute(
        """
        SELECT id, content, bucket, times_added, status
        FROM tasks
        WHERE status = 'open' AND LOWER(content) = LOWER(?)
        """,
        (content,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "content": row[1],
            "bucket": row[2],
            "times_added": row[3],
            "status": row[4]
        }
    return None


def increment_task_mentions(task_id: str) -> Optional[dict]:
    """
    Increment the times_added counter for an existing task.

    Returns the updated task dict, or None if task doesn't exist.
    """
    conn = get_connection()
    now = datetime.now().isoformat()

    conn.execute(
        """
        UPDATE tasks
        SET times_added = times_added + 1, last_added_at = ?
        WHERE id = ?
        """,
        (now, task_id)
    )
    conn.commit()

    cursor = conn.execute(
        """
        SELECT id, content, bucket, times_added, status
        FROM tasks
        WHERE id = ?
        """,
        (task_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "content": row[1],
        "bucket": row[2],
        "times_added": row[3],
        "status": row[4]
    }


def get_open_tasks() -> list[dict]:
    """
    Get all open tasks for semantic matching.

    Returns list of task dicts with id and content.
    """
    conn = get_connection()
    cursor = conn.execute(
        """
        SELECT id, content, bucket, times_added
        FROM tasks
        WHERE status = 'open'
        ORDER BY last_added_at DESC
        """
    )
    tasks = []
    for row in cursor.fetchall():
        tasks.append({
            "id": row[0],
            "content": row[1],
            "bucket": row[2],
            "times_added": row[3]
        })
    conn.close()
    return tasks


def create_dump_session(raw_input: str) -> str:
    """
    Create a dump session record for Slack messages.

    Returns the session ID.
    """
    conn = get_connection()
    session_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    conn.execute(
        """
        INSERT INTO dump_sessions (id, started_at, ended_at, raw_input)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, now, now, raw_input)
    )
    conn.commit()
    conn.close()

    return session_id


def link_task_to_session(task_id: str, session_id: str):
    """Link a task to a dump session."""
    conn = get_connection()
    now = datetime.now().isoformat()

    conn.execute(
        """
        INSERT INTO task_mentions (task_id, session_id, mentioned_at)
        VALUES (?, ?, ?)
        """,
        (task_id, session_id, now)
    )
    conn.commit()
    conn.close()


def get_identity_statements() -> dict[str, str]:
    """
    Get all identity statements for context in task processing.

    Returns dict mapping category to statement.
    """
    conn = get_connection()
    cursor = conn.execute(
        """
        SELECT category, statement
        FROM identity
        """
    )
    statements = {}
    for row in cursor.fetchall():
        statements[row[0]] = row[1]
    conn.close()
    return statements
