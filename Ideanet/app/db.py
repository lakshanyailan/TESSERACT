import json
import sqlite3
from pathlib import Path

# Always the project root, no matter which folder you run from
DB_PATH = Path(__file__).resolve().parent.parent / "ideas.db"


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row      # lets us read columns by name
    return c


def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS seed_projects(
            id INTEGER PRIMARY KEY,
            title TEXT, description TEXT, url TEXT, vector TEXT
        );
        CREATE TABLE IF NOT EXISTS ideas(
            id INTEGER PRIMARY KEY,
            title TEXT, description TEXT,
            author_name TEXT, author_email TEXT,
            score REAL, reasoning TEXT,
            similar_json TEXT, vector TEXT,
            hash TEXT, created_at TEXT
        );
        """)


def get_all_vectors():
    """Everything an idea can be compared against: seed projects + published ideas."""
    items = []
    with conn() as c:
        for r in c.execute("SELECT title, description, url, vector FROM seed_projects"):
            items.append({"title": r["title"], "description": r["description"],
                          "url": r["url"] or "", "vec": json.loads(r["vector"])})
        for r in c.execute("SELECT title, description, vector FROM ideas"):
            items.append({"title": r["title"], "description": r["description"],
                          "url": "", "vec": json.loads(r["vector"])})
    return items


def seed_count():
    with conn() as c:
        return c.execute("SELECT COUNT(*) FROM seed_projects").fetchone()[0]


def add_idea(title, description, name, email, result, fingerprint, created):
    with conn() as c:
        cur = c.execute(
            """INSERT INTO ideas(title, description, author_name, author_email, score,
                                 reasoning, similar_json, vector, hash, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (title, description, name, email, result["score"], result["reasoning"],
             json.dumps(result["similar"]), json.dumps(result["vector"]),
             fingerprint, created),
        )
        return cur.lastrowid


def list_ideas():
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT id, title, description, author_name, score, created_at "
            "FROM ideas ORDER BY id DESC")]


def get_idea(idea_id):
    with conn() as c:
        row = c.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone()
        return dict(row) if row else None