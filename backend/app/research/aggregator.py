"""Runs the social + academic searches together and merges the results."""
import asyncio

from . import exa, openalex


async def gather(query: str, exa_key: str, openalex_mailto: str,
                 n_social: int, n_research: int) -> list[dict]:
    tasks = []
    if n_social > 0:
        tasks.append(exa.search(query, exa_key, num_results=n_social, social_only=True))
    if n_research > 0:
        tasks.append(openalex.search(query, openalex_mailto, num_results=n_research))

    if not tasks:
        return []

    results = await asyncio.gather(*tasks, return_exceptions=True)
    merged: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            continue
        for item in r:
            if "error" not in item:
                merged.append(item)
    return merged
