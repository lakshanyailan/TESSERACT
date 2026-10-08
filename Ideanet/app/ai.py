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


def ask_gemma(prompt: str, model: str = CHAT_MODEL) -> dict:
    """Send a prompt to Gemma and get back a Python dict (parsed from JSON)."""
    r = httpx.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,      # wait for the full answer instead of word-by-word chunks
            "format": "json",     # force Gemma to output valid JSON
        },
        timeout=300,              # local models can be slow; don't give up after 5 seconds
    )
    r.raise_for_status()
    text = r.json()["message"]["content"]
    return json.loads(text)       # turn the JSON string into a Python dict