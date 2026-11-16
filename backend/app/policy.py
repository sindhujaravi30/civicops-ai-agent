from pathlib import Path
import re

POLICY_DIR = Path(__file__).resolve().parent.parent / "data" / "policies"

def _tokens(text: str) -> set[str]:
    """Normalize text into a set of lowercase tokens suitable for matching."""
    return set(re.findall(r"[a-zA-Z0-9-]+", text.lower()))

def retrieve_policy(query: str, limit: int = 3) -> list[dict[str, str]]:
    """Return the most relevant policy excerpts for a query using lexical matching."""
    terms = _tokens(query)
    ranked = []
    for path in POLICY_DIR.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        chunks = [part.strip() for part in content.split("\n## ") if part.strip()]
        for chunk in chunks:
            title = chunk.splitlines()[0].lstrip("# ").strip()
            score = len(terms & _tokens(chunk))
            if score:
                ranked.append((score, {"source": path.name, "title": title, "content": chunk[:1400]}))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:limit]]
