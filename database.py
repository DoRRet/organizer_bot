import sqlite3
from datetime import datetime
from config import DB_PATH

def now():
    return datetime.now().isoformat(timespec="seconds")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            registered_at TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            archived_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            media_type TEXT DEFAULT 'none',
            media_file_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        conn.commit()

def register_user(user_id, username):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users(user_id, username, registered_at) VALUES (?, ?, ?)",
                (user_id, username or "", now())
            )
            conn.commit()

def add_project(user_id, title, description=""):
    with connect() as conn:
        cur = conn.cursor()
        t = now()
        cur.execute("""
            INSERT INTO projects(user_id, title, description, status, archived_at, created_at, updated_at)
            VALUES (?, ?, ?, 'active', NULL, ?, ?)
        """, (user_id, title, description, t, t))
        conn.commit()
        return cur.lastrowid

def get_projects(user_id, include_archived=False):
    with connect() as conn:
        cur = conn.cursor()
        if include_archived:
            cur.execute("SELECT * FROM projects WHERE user_id=? ORDER BY updated_at DESC", (user_id,))
        else:
            cur.execute("SELECT * FROM projects WHERE user_id=? AND status!='archived' ORDER BY updated_at DESC", (user_id,))
        return cur.fetchall()

def get_project(user_id, project_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM projects WHERE id=? AND user_id=?", (project_id, user_id))
        return cur.fetchone()

def set_project_status(user_id, project_id, status):
    archived_at = now() if status == "archived" else None
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE projects SET status=?, archived_at=?, updated_at=? WHERE id=? AND user_id=?",
            (status, archived_at, now(), project_id, user_id)
        )
        conn.commit()

def delete_project(user_id, project_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM entries WHERE project_id=? AND user_id=?", (project_id, user_id))
        cur.execute("DELETE FROM projects WHERE id=? AND user_id=?", (project_id, user_id))
        conn.commit()

def add_entry(user_id, project_id, content, media_type="none", media_file_id=None):
    with connect() as conn:
        cur = conn.cursor()
        t = now()
        cur.execute("""
            INSERT INTO entries(project_id, user_id, content, media_type, media_file_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, user_id, content, media_type, media_file_id, t, t))
        conn.commit()
        return cur.lastrowid

def update_entry(user_id, entry_id, content=None, media_type=None, media_file_id=None):
    with connect() as conn:
        cur = conn.cursor()
        fields, values = [], []
        if content is not None:
            fields.append("content=?"); values.append(content)
        if media_type is not None:
            fields.append("media_type=?"); values.append(media_type)
        if media_file_id is not None:
            fields.append("media_file_id=?"); values.append(media_file_id)
        if not fields:
            return
        fields.append("updated_at=?"); values.append(now())
        values.extend([entry_id, user_id])
        cur.execute(f"UPDATE entries SET {', '.join(fields)} WHERE id=? AND user_id=?", values)
        conn.commit()

def get_entries(user_id, project_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM entries
            WHERE project_id=? AND user_id=?
            ORDER BY created_at DESC
        """, (project_id, user_id))
        return cur.fetchall()

def get_entry(user_id, entry_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM entries WHERE id=? AND user_id=?", (entry_id, user_id))
        return cur.fetchone()

def delete_entry(user_id, entry_id):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM entries WHERE id=? AND user_id=?", (entry_id, user_id))
        conn.commit()