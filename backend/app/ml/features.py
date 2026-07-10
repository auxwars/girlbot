"""Text -> vectors, written from scratch.

Two things live here:
  1. A tokenizer that is deliberately tuned for *texting nuance* — it emits
     special signal tokens for the stuff that carries tone: a trailing period,
     an ellipsis, ALL CAPS, terse one-word replies, loaded short replies
     ('k', 'fine', 'whatever'), emojis, and word bigrams.
  2. A TF-IDF vectorizer (fit / counts / tfidf) implemented by hand on top of
     numpy. No scikit-learn.
"""
import math
import re

import numpy as np

# Rough emoji ranges — enough to catch the common ones.
_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF❤✅]"
)
_LOADED_SHORT = {
    "k", "kk", "fine", "ok", "okay", "sure", "whatever", "nvm", "np",
    "cool", "fs", "kys", "lol", "lmao", "wow", "great", "nice", "yep", "yup", "mk",
}


def tokenize(text: str) -> list[str]:
    """Turn a message into feature tokens, keeping texting-tone signals."""
    if not text:
        return []
    raw = text.strip()
    lower = raw.lower()
    toks: list[str] = []

    # --- tone / punctuation signals ---------------------------------------
    if re.search(r"[a-z0-9]\.\s*$", lower) and len(raw) < 80:
        toks.append("__trailing_period__")
    if "..." in raw or "…" in raw:
        toks.append("__ellipsis__")
    if re.search(r"!{2,}", raw):
        toks.append("__multi_exclaim__")
    if re.search(r"\?{2,}", raw):
        toks.append("__multi_question__")
    if len(raw) > 2 and raw.isupper() and any(c.isalpha() for c in raw):
        toks.append("__all_caps__")
    if not re.search(r"[.?!]", raw) and len(raw) > 0:
        toks.append("__no_end_punct__")

    words = re.findall(r"[a-z']+", lower)

    if len(words) <= 1 and len(lower) <= 8:
        toks.append("__terse_reply__")
    if lower.strip(". !") in _LOADED_SHORT:
        toks.append("__loaded_short_reply__")

    # --- emojis -----------------------------------------------------------
    for e in _EMOJI.findall(raw):
        toks.append("emoji_" + e)

    # --- words + bigrams --------------------------------------------------
    toks.extend(words)
    for i in range(len(words) - 1):
        toks.append(words[i] + "_" + words[i + 1])

    return toks


class TextVectorizer:
    """Bag-of-tokens TF-IDF. Fit once on the corpus, then transform messages."""

    def __init__(self, min_df: int = 1):
        self.min_df = min_df
        self.vocab: dict[str, int] = {}
        self.idf: np.ndarray | None = None

    def fit(self, docs: list[str]) -> "TextVectorizer":
        doc_freq: dict[str, int] = {}
        for d in docs:
            for t in set(tokenize(d)):
                doc_freq[t] = doc_freq.get(t, 0) + 1

        terms = sorted(t for t, c in doc_freq.items() if c >= self.min_df)
        self.vocab = {t: i for i, t in enumerate(terms)}

        n = max(1, len(docs))
        idf = np.zeros(len(self.vocab), dtype=np.float64)
        for t, i in self.vocab.items():
            # smoothed idf, always positive
            idf[i] = math.log((1 + n) / (1 + doc_freq[t])) + 1.0
        self.idf = idf
        return self

    @property
    def n_features(self) -> int:
        return len(self.vocab)

    def counts(self, doc: str) -> np.ndarray:
        vec = np.zeros(self.n_features, dtype=np.float64)
        for t in tokenize(doc):
            j = self.vocab.get(t)
            if j is not None:
                vec[j] += 1.0
        return vec

    def counts_matrix(self, docs: list[str]) -> np.ndarray:
        if not docs:
            return np.zeros((0, self.n_features), dtype=np.float64)
        return np.vstack([self.counts(d) for d in docs])

    def tfidf(self, doc: str) -> np.ndarray:
        v = self.counts(doc) * self.idf
        norm = np.linalg.norm(v)
        return v / norm if norm > 0 else v

    def tfidf_matrix(self, docs: list[str]) -> np.ndarray:
        if not docs:
            return np.zeros((0, self.n_features), dtype=np.float64)
        return np.vstack([self.tfidf(d) for d in docs])
