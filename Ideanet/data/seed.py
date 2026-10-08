import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent
ROOT = DATA.parent                       # the Ideanet/ folder
sys.path.insert(0, str(ROOT))

SEED_FILE = DATA / "seed_projects.json"
OUT_FILE = DATA / "projects.json"


def load_seed():
    with SEED_FILE.open(encoding="utf-8") as f:
        projects = json.load(f)
    if not isinstance(projects, list) or not projects:
        raise SystemExit("seed_projects.json must be a non-empty JSON list.")
    for p in projects:
        for key in ("id", "title", "idea"):
            if key not in p:
                raise SystemExit(f"Project is missing '{key}': {p}")
        p["id"] = str(p["id"])
    return projects


def add_embeddings(projects):
    try:
        from app.ai import embed
    except Exception as e:
        print(f"Skipping embeddings (could not import app.ai: {e})")
        return 0
    done = 0
    for p in projects:
        try:
            p["vec"] = embed(f"{p['title']}. {p['idea']}")
            done += 1
        except Exception as e:
            print(f"Ollama not available ({e}). Saving without embeddings.")
            for q in projects:
                q.pop("vec", None)
            return 0
    return done


def main():
    projects = load_seed()
    n = add_embeddings(projects)
    OUT_FILE.write_text(json.dumps(projects, indent=2), encoding="utf-8")
    print(f"Saved {len(projects)} projects to {OUT_FILE.name} ({n} with embeddings).")


if __name__ == "__main__":
    main()
