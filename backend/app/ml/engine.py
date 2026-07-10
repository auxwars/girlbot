"""The 'her-specific' model: learns from your labeled examples and reads a new
message the way you've taught it to.

Because your dataset is small and grows every time you label something, we just
refit on every analyze() call — for a few hundred examples that's milliseconds,
and it means the model is always up to date with your latest data. If your data
ever gets big, this is the one place to add caching.
"""
from dataclasses import dataclass, field

from .. import db
from .features import TextVectorizer
from .knn import NearestNeighbors
from .naive_bayes import MultinomialNB
from .taxonomy import INTENTS


@dataclass
class SimilarCase:
    her_message: str
    context: str
    true_meaning: str
    intent: str
    similarity: float


@dataclass
class Analysis:
    trained: bool
    n_examples: int
    top_intent: str | None = None
    top_intent_desc: str | None = None
    confidence: float = 0.0
    distribution: dict[str, float] = field(default_factory=dict)
    similar_cases: list[SimilarCase] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "trained": self.trained,
            "n_examples": self.n_examples,
            "top_intent": self.top_intent,
            "top_intent_desc": self.top_intent_desc,
            "confidence": round(self.confidence, 3),
            "distribution": {k: round(v, 3) for k, v in self.distribution.items()},
            "similar_cases": [
                {
                    "her_message": c.her_message,
                    "context": c.context,
                    "true_meaning": c.true_meaning,
                    "intent": c.intent,
                    "similarity": round(c.similarity, 3),
                }
                for c in self.similar_cases
            ],
            "note": self.note,
        }


class MeaningEngine:
    """Fit-on-demand wrapper around the from-scratch ML pieces."""

    def _build(self):
        examples = db.list_examples()
        if not examples:
            return None
        docs = [self._doc(e) for e in examples]
        labels = [e["intent"] for e in examples]

        vec = TextVectorizer().fit(docs)
        nb = MultinomialNB().fit(vec.counts_matrix(docs), labels)
        nn = NearestNeighbors(vec.tfidf_matrix(docs))
        return vec, nb, nn, examples

    @staticmethod
    def _doc(example: dict) -> str:
        # Feed the message plus any situational context into the features.
        ctx = example.get("context") or ""
        return f"{example['her_message']} {ctx}".strip()

    def analyze(self, message: str, context: str = "", k: int = 3) -> Analysis:
        built = self._build()
        n = db.count_examples()
        if built is None:
            return Analysis(
                trained=False, n_examples=0,
                note="No training data yet. Go label some of her messages on the "
                     "Training page and I'll start learning her patterns.",
            )

        vec, nb, nn, examples = built
        query = f"{message} {context}".strip()

        distribution = nb.predict_proba(vec.counts(query))
        top_intent = max(distribution, key=distribution.get) if distribution else None
        confidence = distribution.get(top_intent, 0.0) if top_intent else 0.0

        neighbours = nn.query(vec.tfidf(query), k=k)
        similar = [
            SimilarCase(
                her_message=examples[i]["her_message"],
                context=examples[i].get("context", ""),
                true_meaning=examples[i]["true_meaning"],
                intent=examples[i]["intent"],
                similarity=sim,
            )
            for i, sim in neighbours
            if sim > 0.0
        ]

        note = ""
        if n < 8:
            note = (f"Heads up: only {n} example(s) so far, so this read is shaky. "
                    "The more of her messages you label, the sharper I get.")

        return Analysis(
            trained=True,
            n_examples=n,
            top_intent=top_intent,
            top_intent_desc=INTENTS.get(top_intent, "") if top_intent else "",
            confidence=confidence,
            distribution=distribution,
            similar_cases=similar,
            note=note,
        )


engine = MeaningEngine()
