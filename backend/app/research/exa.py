"""Exa search client — the 'what are people saying online' half.

Exa does neural web search and can pull result text. We bias it toward the
places where people actually decode this stuff out loud: Reddit, forums, etc.
The API key is passed in (per-account, set in Settings). Falls back to an empty
list — never crashes — if there's no key or the call fails.
"""
import httpx

_EXA_URL = "https://api.exa.ai/search"

# Communities where people literally explain "when we say X we mean Y".
_SOCIAL_DOMAINS = [
    "reddit.com",
    "twitter.com",
    "x.com",
    "quora.com",
    "girlsaskguys.com",
]


async def search(query: str, api_key: str, num_results: int = 4,
                 social_only: bool = True) -> list[dict]:
    if not api_key:
        return []

    payload: dict = {
        "query": query,
        "numResults": num_results,
        "type": "auto",
        "contents": {"text": {"maxCharacters": 800}, "highlights": True},
    }
    if social_only:
        payload["includeDomains"] = _SOCIAL_DOMAINS

    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(_EXA_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001 - research is best-effort
        return [{"error": f"Exa request failed: {exc}"}]

    out = []
    for r in data.get("results", []):
        text = r.get("text") or ""
        highlights = r.get("highlights") or []
        snippet = " … ".join(highlights) if highlights else text[:400]
        out.append({
            "source": "social",
            "title": r.get("title") or "(untitled)",
            "url": r.get("url", ""),
            "snippet": snippet.strip(),
        })
    return out
