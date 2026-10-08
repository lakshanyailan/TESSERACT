import json
import httpx
import numpy as np

OLLAMA = "http://localhost:11434"
CHAT_MODEL = "gemma4:latest"          # change to match `ollama list`
EMBED_MODEL = "nomic-embed-text"   # change if your name has a tag, e.g. nomic-embed-text:latest


def embed(text: str) -> list[float]:
    """Turn text into a list of numbers that represents its meaning."""
    r = httpx.post(
        f"{OLLAMA}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=60,
    )
    r.raise_for_status()                 # crash loudly on HTTP errors instead of hiding them
    return r.json()["embeddings"][0]     # "embeddings" is a list of vectors; we sent 1 text, so take [0]


def cosine(a, b) -> float:
    """How similar two vectors are. 1.0 = same meaning."""
    a, b = np.array(a), np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def ask_gemma(prompt: str, model: str = CHAT_MODEL, retries: int = 2) -> dict:
    last_error = None
    for _ in range(retries):
        try:
            r = httpx.post(
                f"{OLLAMA}/api/chat",
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "stream": False, "format": "json"},
                timeout=300,
            )
            r.raise_for_status()
            return json.loads(r.json()["message"]["content"])
        except (json.JSONDecodeError, KeyError) as e:
            last_error = e                    # try again
    return {"score": 5, "reasoning": "The AI judge could not produce a valid answer.",
            "differentiators": ""}            # safe fallback so the website doesn't crash