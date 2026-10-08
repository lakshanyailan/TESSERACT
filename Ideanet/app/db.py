"""Storage for Ideanet.

- Seed projects (the existing hackathon projects we compare against) live in JSON:
  data/projects.json (made by data/seed.py, has embeddings) or data/seed_projects.json.
- Users, comments and ideas that people post live in a small SQLite file: ideanet.db
"""
import datetime
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # the Ideanet/ folder
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "ideanet.db"
TINTS = ["blue", "purple", "green", "pink", "peach", "teal"]


# ------------------------------------------------------------------ sqlite helpers
def _connect():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def q(sql, args=(), one=False):
    c = _connect()
    try:
        rows = c.execute(sql, args).fetchall()
    finally:
        c.close()
    if one:
        return rows[0] if rows else None
    return rows


def run(sql, args=()):
    c = _connect()
    try:
        cur = c.execute(sql, args)
        c.commit()
        return cur.lastrowid
    finally:
        c.close()


def init_db():
    c = _connect()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE COLLATE NOCASE,
            email TEXT UNIQUE COLLATE NOCASE,
            password_hash TEXT,
            bio TEXT DEFAULT '',
            created TEXT
        );
        CREATE TABLE IF NOT EXISTS comments(
            id INTEGER PRIMARY KEY,
            project_id TEXT, user_id INTEGER, text TEXT, created TEXT
        );
        CREATE TABLE IF NOT EXISTS ideas(
            id INTEGER PRIMARY KEY,
            user_id INTEGER, title TEXT, idea TEXT, improve TEXT,
            score REAL, vec TEXT, hash TEXT, created TEXT
        );
        """)
        c.commit()
    finally:
        c.close()


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def human_time(iso):
    try:
        t = datetime.datetime.fromisoformat(iso)
        if t.tzinfo is None:
            t = t.replace(tzinfo=datetime.timezone.utc)
        secs = (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds()
    except Exception:
        return ""
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return t.strftime("%d %b")


# ------------------------------------------------------------------ users
def create_user(username, email, password_hash):
    return run("INSERT INTO users(username, email, password_hash, bio, created) VALUES (?,?,?,?,?)",
               (username, email, password_hash, "", now_iso()))


def get_user(user_id):
    r = q("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    return dict(r) if r else None


def find_user(identifier):
    r = q("SELECT * FROM users WHERE username = ? OR email = ?", (identifier, identifier), one=True)
    return dict(r) if r else None


def username_or_email_taken(username, email):
    r = q("SELECT username, email FROM users WHERE username = ? OR email = ?", (username, email))
    return [dict(x) for x in r]


def set_bio(user_id, bio):
    run("UPDATE users SET bio = ? WHERE id = ?", (bio, user_id))


def set_password(user_id, password_hash):
    run("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))


# ------------------------------------------------------------------ seed projects (JSON)
_SEED = None


def load_seed():
    global _SEED
    if _SEED is None:
        path = DATA_DIR / "projects.json"
        if not path.exists():
            path = DATA_DIR / "seed_projects.json"
        projects = json.loads(path.read_text(encoding="utf-8"))
        for p in projects:
            p["id"] = str(p["id"])
        _SEED = projects
    return _SEED


def ensure_embeddings():
    """Embed any seed project that has no vector yet (needs Ollama). Saves projects.json."""
    from .ai import embed
    projects = load_seed()
    changed = False
    for p in projects:
        if not p.get("vec"):
            p["vec"] = embed(f"{p['title']}. {p['idea']}")
            changed = True
    if changed:
        (DATA_DIR / "projects.json").write_text(json.dumps(projects, indent=2), encoding="utf-8")


# ------------------------------------------------------------------ ideas people post
def add_idea(user_id, title, idea, improve, score, vec, fingerprint):
    return run("INSERT INTO ideas(user_id, title, idea, improve, score, vec, hash, created) VALUES (?,?,?,?,?,?,?,?)",
               (user_id, title, idea, improve, score, json.dumps(vec), fingerprint, now_iso()))


def _idea_row_to_project(r, with_vec=False):
    p = {
        "id": f"u{r['id']}",
        "title": r["title"],
        "idea": r["idea"],
        "built": "",
        "improve": r["improve"] or "",
        "hackathon": f"Originality {r['score']:.1f}/10",
        "by": "@" + (r["username"] or "user"),
        "date": human_time(r["created"]),
        "date_label": human_time(r["created"]),
        "created": r["created"],
        "likes": 0,
        "tech": [],
        "tint": TINTS[r["id"] % len(TINTS)],
        "user_id": r["user_id"],
    }
    if with_vec:
        p["vec"] = json.loads(r["vec"])
    return p


_IDEA_SQL = ("SELECT i.*, u.username FROM ideas i LEFT JOIN users u ON u.id = i.user_id")


def list_ideas():
    return [_idea_row_to_project(r) for r in q(_IDEA_SQL + " ORDER BY i.id DESC")]


def ideas_by_user(user_id):
    return [_idea_row_to_project(r) for r in q(_IDEA_SQL + " WHERE i.user_id = ? ORDER BY i.id DESC", (user_id,))]


def get_corpus():
    """Everything a new idea is compared against: seed projects + ideas people posted."""
    items = [p for p in load_seed() if p.get("vec")]
    items += [_idea_row_to_project(r, with_vec=True) for r in q(_IDEA_SQL)]
    return items


def get_project(pid):
    """Find a project by id: 'o1' = seed project, 'u3' = posted idea."""
    pid = str(pid)
    if pid.startswith("u") and pid[1:].isdigit():
        r = q(_IDEA_SQL + " WHERE i.id = ?", (int(pid[1:]),), one=True)
        return _idea_row_to_project(r) if r else None
    for p in load_seed():
        if p["id"] == pid:
            return {k: v for k, v in p.items() if k != "vec"}
    return None


# ------------------------------------------------------------------ comments
def add_comment(project_id, user_id, text):
    run("INSERT INTO comments(project_id, user_id, text, created) VALUES (?,?,?,?)",
        (str(project_id), user_id, text, now_iso()))


def delete_comment(comment_id, user_id):
    run("DELETE FROM comments WHERE id = ? AND user_id = ?", (comment_id, user_id))


def comments_for(project_id=None, me_id=None):
    """Return {project_id: [comment dicts]} (or one project's list when project_id is given)."""
    sql = ("SELECT c.id, c.project_id, c.user_id, c.text, c.created, u.username "
           "FROM comments c LEFT JOIN users u ON u.id = c.user_id")
    rows = q(sql + (" WHERE c.project_id = ?" if project_id else "") + " ORDER BY c.id",
             (str(project_id),) if project_id else ())
    grouped = {}
    for r in rows:
        grouped.setdefault(r["project_id"], []).append({
            "id": r["id"],
            "name": r["username"] or "someone",
            "handle": "@" + (r["username"] or "someone"),
            "text": r["text"],
            "at": human_time(r["created"]),
            "likes": 0,
            "mine": me_id is not None and r["user_id"] == me_id,
        })
    if project_id:
        return grouped.get(str(project_id), [])
    return grouped
