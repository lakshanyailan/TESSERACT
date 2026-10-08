#!/bin/bash
cd "$(dirname "$0")"
[ -d venv ] || { python3 -m venv venv && venv/bin/python -m pip install -r requirements.txt; }
[ -f ideas.db ] || venv/bin/python seed.py
venv/bin/python -m uvicorn app.main:app