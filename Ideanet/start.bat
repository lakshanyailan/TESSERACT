@echo off
cd /d "%~dp0"

if not exist venv (
    echo First-time setup: creating venv and installing packages...
    python -m venv venv
    venv\Scripts\python -m pip install -r requirements.txt
)

if not exist ideas.db (
    echo Seeding database...
    venv\Scripts\python seed.py
)

echo Starting server at http://localhost:8000
venv\Scripts\python -m uvicorn app.main:app
pause