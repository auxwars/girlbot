"""Multinomial Naive Bayes, from scratch on numpy.

Learns P(intent | message) from the labeled examples. Small-data friendly,
transparent, and gives a real probability distribution (a confidence) instead
of a black-box guess.
"""
import numpy as np


class MultinomialNB:
    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.classes: list[str] = []
        self.log_prior: np.ndarray | None = None
        self.log_likelihood: np.ndarray | None = None  # (n_classes, n_features)

    def fit(self, x_counts: np.ndarray, y: list[str]) -> "MultinomialNB":
        y_arr = np.array(y)
        self.classes = sorted(set(y))
        n_docs = len(y)
        n_features = x_counts.shape[1]

        self.log_prior = np.zeros(len(self.classes))
        self.log_likelihood = np.zeros((len(self.classes), n_features))

        for ci, c in enumerate(self.classes):
            rows = x_counts[y_arr == c]
            self.log_prior[ci] = np.log(rows.shape[0] / n_docs)
            counts = rows.sum(axis=0) + self.alpha          # Laplace smoothing
            total = counts.sum()
            self.log_likelihood[ci] = np.log(counts / total)
        return self

    def predict_proba(self, x_count: np.ndarray) -> dict[str, float]:
        """Return {class: probability} for a single count vector."""
        if not self.classes:
            return {}
        scores = self.log_prior + self.log_likelihood @ x_count
        scores -= scores.max()                              # numerical stability
        probs = np.exp(scores)
        probs /= probs.sum()
        return {c: float(p) for c, p in zip(self.classes, probs)}
