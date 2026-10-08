import os
import json
import uuid
import hashlib
import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()      # must run BEFORE importing auth, which reads .env

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import db, scoring

BASE = Path(__file__).resolve().parent

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "dev-secret"))
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

db.init_db()
print(f"[startup] seed projects in database: {db.seed_count()}")

# Judged-but-not-yet-published ideas. Lives in memory; cleared when the server restarts.
DRAFTS = {}


# ---------------------------------------------------------------- login
# If Google keys are in .env, use Person D's Google login.
# Otherwise fall back to a simple "type your name" login so the demo still works.
if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
    from . import auth
    app.include_router(auth.router)
    print("[startup] login mode: Google")
else:
    print("[startup] login mode: simple name login (no Google keys found)")

    @app.get("/login", response_class=HTMLResponse)
    def login_page():
        return """
        <link rel="stylesheet" href="/static/style.css">
        <h2>Log in</h2>
        <form method="post" action="/login">
          <input name="name" placeholder="Your name" required>
          <button>Log in</button>
        </form>"""

    @app.post("/login")
    def login_submit(request: Request, name: str = Form(...)):
        name = name.strip() or "Guest"
        request.session["user"] = {"name": name, "email": f"{name.lower().replace(' ', '.')}@local"}
        return RedirectResponse("/", status_code=303)

    @app.get("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/", status_code=303)


def current_user(request: Request):
    return request.session.get("user")


def error_page(message: str):
    return HTMLResponse(
        f'<link rel="stylesheet" href="/static/style.css">'
        f'<h2>Something went wrong</h2><p>{message}</p><a href="/">Back</a>',
        status_code=500,
    )


# ---------------------------------------------------------------- pages
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"user": current_user(request)})


@app.post("/judge")
def judge_idea(request: Request, title: str = Form(...), description: str = Form(...)):
    title, description = title.strip(), description.strip()
    if not title or not description:
        return RedirectResponse("/", status_code=303)
    try:
        result = scoring.judge(title, description, db.get_all_vectors())   # Person B's function
    except Exception as e:
        return error_page(f"The AI judge failed. Is Ollama running? ({e})")

    draft_id = uuid.uuid4().hex
    DRAFTS[draft_id] = {"title": title, "description": description, "result": result}
    return templates.TemplateResponse(request, "result.html", {
        "user": current_user(request), "r": result, "title": title,
        "description": description, "draft_id": draft_id,
    })


@app.post("/publish")
def publish(request: Request, draft_id: str = Form(...)):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    draft = DRAFTS.get(draft_id)
    if not draft:
        return RedirectResponse("/", status_code=303)     # server restarted; submit again

    created = datetime.datetime.now(datetime.timezone.utc).isoformat()
    fingerprint = hashlib.sha256(
        f"{draft['title']}|{draft['description']}|{user['email']}|{created}".encode()
    ).hexdigest()

    idea_id = db.add_idea(draft["title"], draft["description"], user.get("name", ""),
                          user["email"], draft["result"], fingerprint, created)
    DRAFTS.pop(draft_id, None)
    return RedirectResponse(f"/idea/{idea_id}", status_code=303)


@app.get("/forum")
def forum(request: Request):
    return templates.TemplateResponse(request, "forum.html", {
        "user": current_user(request), "ideas": db.list_ideas()})


@app.get("/idea/{idea_id}")
def idea_page(request: Request, idea_id: int):
    idea = db.get_idea(idea_id)
    if not idea:
        return RedirectResponse("/forum", status_code=303)
    return templates.TemplateResponse(request, "idea.html", {
        "user": current_user(request), "idea": idea,
        "similar": json.loads(idea["similar_json"])})