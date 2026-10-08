from app.ai import embed
from app.scoring import judge

# A tiny fake corpus so you don't need the database yet
raw = [
    ("CalorieCam", "Mobile app that estimates calories from photos of your meals."),
    ("StudyBuddy", "AI tutor that quizzes students and tracks weak topics."),
    ("EcoTrack", "Dashboard that estimates your carbon footprint from purchases."),
    ("SpaceDodger", "Browser game where you dodge asteroids in a spaceship."),
    ("MedRemind", "App that reminds elderly patients to take medication."),
    ("LingoChat", "Language learning through chatting with an AI partner."),
]
corpus = [{"title": t, "description": d, "url": "", "vec": embed(f"{t}. {d}")} for t, d in raw]

tests = {
    "COPY": ("FoodSnap", "App that counts calories by taking a photo of your food."),
    "MEDIUM": ("Gym Planner", "App that builds weekly workout plans based on your goals."),
    "WEIRD": ("Dream Weaver", "Uses a wearable that detects REM sleep and plays tailored sounds "
                              "to steer dream themes, then logs them in a shared dream map."),
}

for label, (title, desc) in tests.items():
    r = judge(title, desc, corpus)
    print(f"\n=== {label}: {title} ===")
    print("final:", r["score"], "| llm:", r["llm_score"], "| embed:", r["embed_score"])
    print("closest:", r["similar"][0]["title"], r["similar"][0]["similarity"])
    print("reasoning:", r["reasoning"])