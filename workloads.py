"""Reproducible request and key workload generation."""
from __future__ import annotations
import numpy as np

def generate_keys(key_count: int) -> list[str]:
    if key_count < 1:
        raise ValueError("key_count must be >= 1")
    return [f"key-{i:08d}" for i in range(key_count)]

def generate_requests(keys: list[str], request_count: int, workload: str, seed: int,
                      zipf_alpha: float = 1.0) -> list[str]:
    """Generate requests from a uniform or Zipf-like popularity distribution."""
    if request_count < 1:
        raise ValueError("request_count must be >= 1")
    if not keys:
        raise ValueError("keys cannot be empty")
    rng = np.random.default_rng(seed)
    mode = workload.lower()
    if mode == "uniform":
        indices = rng.integers(0, len(keys), size=request_count)
    elif mode == "zipf":
        if zipf_alpha < 0:
            raise ValueError("zipf_alpha must be >= 0")
        # numpy's Zipf requires alpha > 1. Use a rank-based power law to support
        # the paper's alpha values 0.5, 1.0, and 1.5.
        ranks = np.arange(1, len(keys) + 1, dtype=float)
        probs = ranks ** (-zipf_alpha)
        probs /= probs.sum()
        indices = rng.choice(len(keys), size=request_count, p=probs)
    else:
        raise ValueError("workload must be 'uniform' or 'zipf'")
    return [keys[int(i)] for i in indices]
