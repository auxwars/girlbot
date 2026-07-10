"""OpenAlex client — the 'what does the actual research say' half.

Free, no API key. Pulls relationship-psychology papers (communication, conflict,
attachment, how people process and respond to emotional cues) so the bot can
ground advice in more than vibes. Polite pool: pass a mailto if one is set.
"""
import httpx

_OPENALEX_URL = "https://api.openalex.org/works"


async def search(query: str, mailto: str = "", num_results: int = 3) -> list[dict]:
    params = {
        "search": query,
        "per_page": num_results,
        "filter": "has_abstract:true",
        "sort": "relevance_score:desc",
    }
    if mailto:
        params["mailto"] = mailto

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(_OPENALEX_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001 - research is best-effort
        return [{"error": f"OpenAlex request failed: {exc}"}]

    out = []
    for w in data.get("results", []):
        out.append({
            "source": "research",
            "title": w.get("title") or "(untitled)",
            "url": (w.get("primary_location") or {}).get("landing_page_url") or w.get("id", ""),
            "snippet": _abstract(w),
        })
    return out


def _abstract(work: dict) -> str:
    """OpenAlex stores abstracts as an inverted index; rebuild it to text."""
    inv = work.get("abstract_inverted_index")
    if not inv:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)[:500]
