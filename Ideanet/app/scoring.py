from .ai import embed, cosine, ask_gemma


def find_similar(vec: list[float], corpus: list[dict], k: int = 5) -> list[tuple[float, dict]]:
    """Return the k corpus items closest in meaning to `vec`, best first."""
    scored = [(cosine(vec, item["vec"]), item) for item in corpus]
    scored.sort(key=lambda pair: pair[0], reverse=True)   # highest similarity first
    return scored[:k]


def embedding_score(max_sim: float) -> float:
    """Turn 'how close is the nearest project' into a 1-10 originality score.
    TUNE THESE TWO NUMBERS after testing."""
    HIGH_SIM = 0.85   # at or above this similarity -> score 1 (basically a copy)
    LOW_SIM = 0.45    # at or below this similarity -> score 10 (nothing like it)
    score = 1 + (HIGH_SIM - max_sim) / (HIGH_SIM - LOW_SIM) * 9
    return max(1.0, min(10.0, score))      # clamp into 1..10


def judge(title: str, description: str, corpus: list[dict]) -> dict:
    # 1. Embed the new idea
    vec = embed(f"{title}. {description}")

    # 2. Find the 5 most similar existing projects
    top = find_similar(vec, corpus, k=5)
    similar = [
        {
            "title": item["title"],
            "description": item["description"],
            "url": item.get("url", ""),
            "similarity": round(sim, 2),
        }
        for sim, item in top
    ]
    max_sim = top[0][0] if top else 0.0

    # 3. Formula-based score
    e_score = embedding_score(max_sim)

    # 4. Ask Gemma to judge with the evidence in front of it
    listing = "\n".join(
        f"- {s['title']} (similarity {s['similarity']}): {s['description']}" for s in similar
    )
    prompt = f"""You are a strict hackathon judge. You score ORIGINALITY only.

NEW IDEA
Title: {title}
Description: {description}

MOST SIMILAR EXISTING PROJECTS
{listing}

Rules:
- 1 means almost a copy of an existing project. 10 means genuinely novel.
- Most ideas are 3 to 6. Reserve 8+ for ideas with a truly new angle.
- Compare directly against the projects listed. Name them in your reasoning.

Reply ONLY as JSON with exactly these keys:
{{"score": <number 1-10>, "reasoning": "<2-3 sentences>", "differentiators": "<what is new about it, or what it lacks>"}}"""

    out = ask_gemma(prompt)

    # 5. Clean the output safely (Gemma might return a string like "7" or miss a key)
    try:
        llm_score = float(out.get("score", 5))
    except (TypeError, ValueError):
        llm_score = 5.0
    llm_score = max(1.0, min(10.0, llm_score))

    # 6. Blend the two scores
    final = round(0.6 * llm_score + 0.4 * e_score, 1)

    return {
        "score": final,
        "llm_score": llm_score,
        "embed_score": round(e_score, 1),
        "reasoning": out.get("reasoning", ""),
        "differentiators": out.get("differentiators", ""),
        "similar": similar,
        "vector": vec,       # Person A stores this when an idea is published
    }