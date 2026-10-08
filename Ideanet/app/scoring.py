import re

from .ai import embed, cosine, ask_gemma

STOP = {"that", "this", "with", "from", "your", "have", "will", "they", "their", "about", "into",
        "using", "based", "which", "when", "what", "them", "than", "then", "each", "other",
        "app", "apps", "idea", "build", "make", "makes", "help", "helps", "users", "user"}


def find_similar(vec, corpus, k=5):
    """Return the k corpus items closest in meaning to `vec`, best first."""
    scored = [(cosine(vec, item["vec"]), item) for item in corpus if item.get("vec")]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[:k]


def embedding_score(max_sim: float) -> float:
    """Nearest-project similarity -> 1-10 originality. TUNE HIGH_SIM / LOW_SIM after testing."""
    HIGH_SIM = 0.85   # at or above -> 1 (basically a copy)
    LOW_SIM = 0.45    # at or below -> 10 (nothing like it)
    score = 1 + (HIGH_SIM - max_sim) / (HIGH_SIM - LOW_SIM) * 9
    return max(1.0, min(10.0, score))


def closeness_label(sim: float) -> str:
    if sim >= 0.75:
        return "Very close"
    if sim >= 0.60:
        return "Close"
    return "Related"


def _words(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower()) if w not in STOP}


def shared_words(idea_text: str, item: dict) -> list:
    mine = _words(idea_text)
    theirs = {k.lower() for k in item.get("keywords", [])} | _words(item.get("title", "")) | _words(item.get("idea", ""))
    common = [w for w in item.get("keywords", []) if w.lower() in mine]
    for w in sorted(mine & theirs):
        if w not in common:
            common.append(w)
    return common[:3]


def judge(title: str, description: str, corpus: list) -> dict:
    """title may be '' (the Explore page only has one box)."""
    text = f"{title}. {description}" if title else description
    vec = embed(text)

    top = find_similar(vec, corpus, k=5)
    similar = []
    for sim, item in top:
        d = {k: v for k, v in item.items() if k != "vec"}
        d["description"] = d.get("idea", "")
        d["similarity"] = round(sim, 2)
        d["closeness"] = closeness_label(sim)
        d["shared"] = shared_words(description, item)
        similar.append(d)
    max_sim = top[0][0] if top else 0.0
    e_score = embedding_score(max_sim)

    listing = "\n".join(
        f"- {s['title']} (similarity {s['similarity']}): {s.get('idea', '')}" for s in similar
    ) or "(no existing projects found)"
    prompt = f"""You are a strict hackathon judge. You score ORIGINALITY only.

NEW IDEA
{text}

MOST SIMILAR EXISTING PROJECTS
{listing}

Rules:
- 1 means almost a copy of an existing project. 10 means genuinely novel.
- Most ideas are 3 to 6. Reserve 8+ for ideas with a truly new angle.
- Compare directly against the projects listed. Name them in your reasoning.
- Say "similar to". Never say plagiarism or patented.

Reply ONLY as JSON with exactly these keys:
{{"score": <number 1-10>, "reasoning": "<2-3 sentences>", "differentiators": "<what is new about it, or what it lacks>"}}"""

    out = ask_gemma(prompt)
    try:
        llm_score = float(out.get("score", 5))
    except (TypeError, ValueError):
        llm_score = 5.0
    llm_score = max(1.0, min(10.0, llm_score))

    final = round(0.6 * llm_score + 0.4 * e_score, 1)
    final = max(1.0, min(9.9, final))

    return {
        "score": final,
        "llm_score": llm_score,
        "embed_score": round(e_score, 1),
        "reasoning": str(out.get("reasoning", "")),
        "differentiators": str(out.get("differentiators", "")),
        "similar": similar,
        "vector": vec,
    }
