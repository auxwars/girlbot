"""Nearest-neighbour retrieval over TF-IDF vectors, from scratch.

Used to pull up the most similar past messages you've already decoded, so the
bot can say "last time she said something like this, it meant X." Because the
TF-IDF vectors are L2-normalized, cosine similarity is just a dot product.
"""
import numpy as np


class NearestNeighbors:
    def __init__(self, matrix: np.ndarray):
        # matrix: (n_examples, n_features), each row L2-normalized
        self.matrix = matrix

    def query(self, vec: np.ndarray, k: int = 3) -> list[tuple[int, float]]:
        """Return [(row_index, similarity), ...] sorted best-first."""
        if self.matrix.shape[0] == 0:
            return []
        sims = self.matrix @ vec                      # cosine sim per row
        k = min(k, len(sims))
        # argsort descending, take top-k
        top = np.argsort(-sims)[:k]
        return [(int(i), float(sims[i])) for i in top]
