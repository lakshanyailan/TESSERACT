"""Accounts: signup, login, logout, profile. Passwords are hashed; the session is a signed cookie."""
import re
from functools import wraps

from flask import (Blueprint, flash, g, redirect, render_template, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from . import db

bp = Blueprint("auth", __name__)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def init_app(app):
    app.register_blueprint(bp)


def safe_next(target, default="/"):
    """Only allow redirects to pages on this site."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return default


@bp.before_app_request
def load_user():
    uid = session.get("user_id")
    g.user = db.get_user(uid) if uid else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in first.", "error")
            back = request.full_path.rstrip("?") if request.method == "GET" else "/"
            return redirect(url_for("auth.login", next=back))
        return view(*args, **kwargs)
    return wrapped


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        error = None
        if not USERNAME_RE.match(username):
            error = "Username must be 3 to 20 characters: letters, numbers, underscore."
        elif not EMAIL_RE.match(email):
            error = "Enter a valid email address."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            for row in db.username_or_email_taken(username, email):
                if row["username"].lower() == username.lower():
                    error = "That username is taken."
                elif row["email"].lower() == email:
                    error = "That email already has an account."
        if error:
            flash(error, "error")
            return render_template("signup.html")

        uid = db.create_user(username, email, generate_password_hash(password))
        session.clear()
        session["user_id"] = uid
        flash(f"Welcome to Ideanet, {username}!", "success")
        return redirect(url_for("index"))
    return render_template("signup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        user = db.find_user(identifier) if identifier else None
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(safe_next(request.args.get("next")))
        flash("Incorrect username or password.", "error")      # same message for both on purpose
        return render_template("login.html")
    return render_template("login.html")


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_profile":
            db.set_bio(g.user["id"], request.form.get("bio", "").strip()[:300])
            flash("Bio saved.", "success")
        elif action == "change_password":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if not check_password_hash(g.user["password_hash"], current):
                flash("Your current password is not correct.", "error")
            elif len(new) < 8:
                flash("New password must be at least 8 characters.", "error")
            elif new != confirm:
                flash("New passwords do not match.", "error")
            else:
                db.set_password(g.user["id"], generate_password_hash(new))
                flash("Password updated.", "success")
        return redirect(url_for("auth.profile"))

    projects = db.ideas_by_user(g.user["id"])
    days = {}
    for p in projects:
        day = (p.get("created") or "")[:10]
        if day:
            days[day] = days.get(day, 0) + 1
    return render_template("profile.html", user=g.user, projects=projects, project_days=days)
