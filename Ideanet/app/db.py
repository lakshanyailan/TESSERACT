import json
import os
import threading
import uuid
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")

_lock = threading.Lock()


def _read():
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _write(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    tmp = USERS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
    os.replace(tmp, USERS_FILE)  # atomic write, avoids corrupted file


def get_user_by_id(user_id):
    return next((u for u in _read() if u["id"] == user_id), None)


def get_user_by_email(email):
    email = email.strip().lower()
    return next((u for u in _read() if u["email"] == email), None)


def get_user_by_username(username):
    username = username.strip().lower()
    return next((u for u in _read() if u["username"].lower() == username), None)


def create_user(username, email, password_hash):
    """Create and return a new user. Raises ValueError on duplicates."""
    with _lock:
        users = _read()
        if any(u["email"] == email.strip().lower() for u in users):
            raise ValueError("An account with that email already exists.")
        if any(u["username"].lower() == username.strip().lower() for u in users):
            raise ValueError("That username is already taken.")

        user = {
            "id": uuid.uuid4().hex,
            "username": username.strip(),
            "email": email.strip().lower(),
            "password_hash": password_hash,
            "bio": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        users.append(user)
        _write(users)
        return user


def update_user(user_id, **fields):
    """Update allowed fields on a user and return the updated record."""
    allowed = {"username", "email", "password_hash", "bio"}
    with _lock:
        users = _read()
        for u in users:
            if u["id"] == user_id:
                for key, value in fields.items():
                    if key in allowed:
                        u[key] = value
                _write(users)
                return u
    return None
