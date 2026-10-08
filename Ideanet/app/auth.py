import re
from functools import wraps
from urllib.parse import urlparse

from flask import (
    Blueprint, flash, g, redirect, render_template,
    request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from . import db

auth_bp = Blueprint("auth", __name__)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 8


# ---------- helpers ----------
def init_app(app):
    """Call once from main.py: auth.init_app(app)"""
    app.register_blueprint(auth_bp)


@auth_bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = db.get_user_by_id(user_id) if user_id else None


def login_required(view):
    """Decorator: redirect to login if not signed in."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def _is_safe_url(target):
    """Only allow redirects to relative paths on this site."""
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.netloc and not parsed.scheme and target.startswith("/")


def _validate_password(password):
    if len(password) < MIN_PASSWORD_LEN:
        return f"Password must be at least {MIN_PASSWORD_LEN} characters."
    return None


# ---------- routes ----------
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if g.user:
        return redirect("/")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        error = None
        if not USERNAME_RE.match(username):
            error = "Username must be 3-20 characters: letters, numbers, underscore."
        elif not EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif _validate_password(password):
            error = _validate_password(password)
        elif password != confirm:
            error = "Passwords do not match."

        if error is None:
            try:
                user = db.create_user(
                    username, email, generate_password_hash(password)
                )
            except ValueError as e:
                error = str(e)
            else:
                session.clear()
                session["user_id"] = user["id"]
                flash(f"Welcome, {user['username']}!", "success")
                return redirect("/")

        flash(error, "error")

    return render_template("auth.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect("/")

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        user = db.get_user_by_email(identifier) or db.get_user_by_username(identifier)

        # Same message for both failures so attackers can't probe for accounts
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username/email or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            nxt = request.args.get("next")
            return redirect(nxt if _is_safe_url(nxt) else "/")

    return render_template("auth.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You've been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_profile":
            bio = request.form.get("bio", "").strip()[:300]
            db.update_user(g.user["id"], bio=bio)
            flash("Profile updated.", "success")

        elif action == "change_password":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")

            if not check_password_hash(g.user["password_hash"], current):
                flash("Current password is incorrect.", "error")
            elif _validate_password(new):
                flash(_validate_password(new), "error")
            elif new != confirm:
                flash("New passwords do not match.", "error")
            else:
                db.update_user(
                    g.user["id"], password_hash=generate_password_hash(new)
                )
                flash("Password changed.", "success")

        return redirect(url_for("auth.profile"))

    return render_template("profile.html", user=g.user)
