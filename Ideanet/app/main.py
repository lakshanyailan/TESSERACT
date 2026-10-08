"""Ideanet: the Flask app. Run from the Ideanet/ folder with:
    python -m flask --app app.main run
"""
import hashlib
import os
import uuid
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, flash, g, redirect, render_template, request, url_for

from . import auth, db, scoring

MIN_SHOWN_SIMILARITY = 0.50     # below this a project is not "similar", so the carousel hides it
DRAFTS = {}                     # judged-but-not-posted ideas, kept in memory (cleared on restart)


def create_app():
    app = Flask(__name__)
    secret = os.getenv("SECRET_KEY") or os.getenv("SESSION_SECRET")
    if not secret:
        print("[warning] SECRET_KEY is not set in .env, using an unsafe development key")
        secret = "dev-only-change-me"
    app.config["SECRET_KEY"] = secret

    db.init_db()
    auth.init_app(app)

    def back_to(default):
        """Go back to the page the form was on, if it is on this site."""
        ref = request.referrer
        if ref and urlparse(ref).netloc == request.host:
            return redirect(ref)
        return redirect(default)

    # ------------------------------------------------------------ Explore
    @app.route("/")
    def index():
        return render_template("index.html", idea=request.args.get("idea", ""))

    @app.route("/result", methods=["GET", "POST"])
    def result():
        if request.method == "GET":
            return redirect(url_for("index"))
        idea = request.form.get("idea", "").strip()
        if len(idea) < 3:
            flash("Type your idea first (at least 3 characters).", "error")
            return redirect(url_for("index"))
        try:
            db.ensure_embeddings()                                  # first run only
            res = scoring.judge("", idea, db.get_corpus())
        except Exception as e:
            print("[judge error]", repr(e))
            flash("The AI judge could not run. Is Ollama running and are the model names right? "
                  f"({type(e).__name__}: {e})", "error")
            return render_template("index.html", idea=idea)

        similar = [s for s in res["similar"] if s["similarity"] >= MIN_SHOWN_SIMILARITY]
        draft_id = uuid.uuid4().hex
        DRAFTS[draft_id] = {"idea": idea, "res": res}
        while len(DRAFTS) > 50:
            DRAFTS.pop(next(iter(DRAFTS)))
        return render_template("result.html", idea=idea, score=res["score"], similar=similar,
                               draft_id=draft_id, reasoning=res["reasoning"])

    @app.route("/publish", methods=["POST"])
    @auth.login_required
    def publish():
        draft = DRAFTS.get(request.form.get("draft_id", ""))
        if not draft:
            flash("That result expired. Check your idea again, then post it.", "error")
            return redirect(url_for("index"))
        idea, res = draft["idea"], draft["res"]
        words = idea.split()
        title = " ".join(words[:7]) + ("..." if len(words) > 7 else "")
        stamp = db.now_iso()
        fingerprint = hashlib.sha256(f"{idea}|{g.user['id']}|{stamp}".encode()).hexdigest()
        improve = " ".join(x for x in (res["differentiators"], res["reasoning"]) if x)
        new_id = db.add_idea(g.user["id"], title, idea, improve, res["score"], res["vector"], fingerprint)
        DRAFTS.pop(request.form.get("draft_id", ""), None)
        flash("Posted to For you.", "success")
        return redirect(url_for("project", pid=f"u{new_id}"))

    # ------------------------------------------------------------ feed + project pages
    @app.route("/forum")
    def forum():
        me = g.user["id"] if g.user else None
        by_project = db.comments_for(me_id=me)
        seed = sorted(({k: v for k, v in p.items() if k != "vec"} for p in db.load_seed()),
                      key=lambda p: p.get("date", ""), reverse=True)
        posts = db.list_ideas() + seed
        for p in posts:
            p["date_label"] = p.get("date_label") or p.get("date", "")
            p["comments"] = by_project.get(p["id"], [])
            p["comment_count"] = len(p["comments"])
        seen, stories = set(), []
        for p in seed:
            name = p.get("hackathon")
            if name and name not in seen:
                seen.add(name)
                stories.append({"name": name, "tint": p.get("tint"), "id": len(stories), "url": "/forum"})
        return render_template("forum.html", posts=posts, stories=stories)

    @app.route("/idea/<pid>")
    def project(pid):
        p = db.get_project(pid)
        if not p:
            return render_template("forum.html", posts=[], stories=[]), 404
        me = g.user["id"] if g.user else None
        p["mine"] = bool(me) and p.get("user_id") == me
        return render_template("idea.html", p=p, comments=db.comments_for(pid, me_id=me))

    @app.route("/idea/<pid>/comment", methods=["POST"])
    @auth.login_required
    def add_comment(pid):
        text = request.form.get("text", "").strip()[:280]
        if not db.get_project(pid):
            flash("That project does not exist.", "error")
            return redirect(url_for("forum"))
        if text:
            db.add_comment(pid, g.user["id"], text)
        return back_to(url_for("project", pid=pid))

    @app.route("/idea/<pid>/comment/<int:cid>/delete", methods=["POST"])
    @auth.login_required
    def delete_comment(pid, cid):
        db.delete_comment(cid, g.user["id"])                       # only deletes your own
        return back_to(url_for("project", pid=pid))

    # ------------------------------------------------------------ other pages
    @app.route("/upcoming")
    def upcoming():
        return render_template("upcoming.html")

    @app.route("/chats")
    def chats():
        return render_template("chats.html")

    @app.route("/health")
    def health():
        """Open http://127.0.0.1:5000/health to check Ollama and the data are OK."""
        import httpx
        from . import ai
        info = {"seed_projects": len(db.load_seed()),
                "with_embeddings": sum(1 for p in db.load_seed() if p.get("vec")),
                "chat_model": ai.CHAT_MODEL, "embed_model": ai.EMBED_MODEL}
        try:
            tags = httpx.get(f"{ai.OLLAMA}/api/tags", timeout=3).json()["models"]
            info["ollama_models"] = [m["name"] for m in tags]
        except Exception as e:
            info["ollama_error"] = f"{type(e).__name__}: {e}"
        return info

    return app


app = create_app()
