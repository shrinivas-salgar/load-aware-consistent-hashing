"""Metrics for load balance, movement, timing, and memory."""
from __future__ import annotations
import math
import tracemalloc
import time

def jains_fairness(loads: list[int | float]) -> float:
    if not loads or sum(x*x for x in loads) == 0:
        return 1.0
    total = sum(loads)
    return (total * total) / (len(loads) * sum(x*x for x in loads))

def load_metrics(loads: dict[str, int]) -> dict:
    values = [float(v) for v in loads.values()]
    if not values:
        return {"mean_load": 0, "max_load": 0, "std_load": 0, "peak_to_average": 0,
                "jain_fairness": 1, "p95_load": 0, "p99_load": 0}
    mean = sum(values) / len(values)
    sorted_values = sorted(values)
    def percentile(p):
        # Nearest-rank percentile, consistent and dependency-free.
        return sorted_values[max(0, math.ceil(p * len(sorted_values)) - 1)]
    return {
        "mean_load": mean,
        "max_load": max(values),
        "std_load": (sum((x-mean)**2 for x in values) / len(values)) ** 0.5,
        "peak_to_average": (max(values) / mean) if mean else 0,
        "jain_fairness": jains_fairness(values),
        "p95_load": percentile(.95),
        "p99_load": percentile(.99),
    }

def measure_memory_bytes(callable_obj):
    tracemalloc.start()
    try:
        callable_obj()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return int(peak)

def elapsed_seconds(callable_obj):
    start = time.perf_counter()
    result = callable_obj()
    return result, time.perf_counter() - start
