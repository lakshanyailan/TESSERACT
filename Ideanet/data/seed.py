import json
import sqlite3
from pathlib import Path

DATA_FILE = Path(__file__).with_name("seed_projects.json")
DATABASE_FILE = Path(__file__).with_name("projects.db")


def seed_projects() -> None:
    with DATA_FILE.open(encoding="utf-8") as file:
        projects = json.load(file)

    if not isinstance(projects, list):
        raise ValueError("seed_projects.json must contain a JSON list.")

    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)

        for project in projects:
            connection.execute(
                """
                INSERT INTO projects (id, name, description, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    status = excluded.status
                """,
                (
                    project["id"],
                    project["name"],
                    project.get("description", ""),
                    project.get("status", "planned"),
                ),
            )

    print(f"Seeded {len(projects)} projects into {DATABASE_FILE.name}.")


if __name__ == "__main__":
    seed_projects()
