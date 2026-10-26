"""Core experiment runner for CH, RH, and bounded load-aware CH routing."""
from __future__ import annotations
import time
from collections import Counter
from hashing import ConsistentHashRing, rendezvous_primary
from workloads import generate_keys, generate_requests
from metrics import load_metrics, measure_memory_bytes

ALGORITHMS = ("CH", "RH", "CH-LA")

def _make_nodes(count: int) -> list[str]:
    if count < 1:
        raise ValueError("node count must be >= 1")
    return [f"node-{i:03d}" for i in range(count)]

def _owner_map(algorithm: str, keys: list[str], nodes: list[str], virtual_nodes: int):
    if algorithm == "CH" or algorithm == "CH-LA":
        ring = ConsistentHashRing(nodes, virtual_nodes)
        return {key: ring.primary(key) for key in keys}, ring
    if algorithm == "RH":
        return {key: rendezvous_primary(key, nodes) for key in keys}, None
    raise ValueError(f"Unknown algorithm: {algorithm}")

def _route_requests(algorithm: str, requests: list[str], primary_map: dict[str, str],
                    nodes: list[str], ring: ConsistentHashRing | None,
                    alpha: float, candidates: int, variant: str = "full"):
    """Route requests sequentially; load counters are updated after every request."""
    loads = {node: 0 for node in nodes}
    reassigned = 0
    started = time.perf_counter()
    for key in requests:
        primary = primary_map[key]
        destination = primary
        if algorithm == "CH-LA" and variant != "ordinary":
            mean_load = sum(loads.values()) / len(nodes)
            threshold = alpha * mean_load
            if loads[primary] > threshold:
                if variant in ("threshold_candidates", "full"):
                    options = ring.next_distinct_nodes(key, candidates, exclude=primary) if ring else []
                    eligible = [node for node in options if loads[node] <= threshold]
                    if eligible:
                        destination = eligible[0]  # clockwise candidate order
                    elif options and variant == "full":
                        destination = min(options, key=lambda node: (loads[node], node))
                    elif options and variant == "threshold_candidates":
                        destination = primary
                elif variant == "threshold_only":
                    destination = primary
        loads[destination] += 1
        if destination != primary:
            reassigned += 1
    elapsed = time.perf_counter() - started
    return loads, reassigned, elapsed

def run_single(nodes_count: int, request_count: int, workload: str, seed: int,
               key_count: int = 10000, virtual_nodes: int = 100, alpha: float = 1.25,
               candidates: int = 4, zipf_alpha: float = 1.0, membership_event: str = "none",
               algorithm: str = "CH", variant: str = "full") -> dict:
    """Run one algorithm/configuration. Returns one flat CSV-ready record."""
    if nodes_count < 1:
        raise ValueError("nodes_count must be >= 1")
    nodes_before = _make_nodes(nodes_count)
    keys = generate_keys(key_count)
    requests = generate_requests(keys, request_count, workload, seed, zipf_alpha)

    build_started = time.perf_counter()
    primary_before, ring_before = _owner_map(algorithm, keys, nodes_before, virtual_nodes)
    build_seconds = time.perf_counter() - build_started
    before_memory = measure_memory_bytes(lambda: _owner_map(algorithm, keys, nodes_before, virtual_nodes))

    nodes_after = list(nodes_before)
    if membership_event == "add":
        new_id = f"node-{nodes_count:03d}"
        nodes_after.append(new_id)
    elif membership_event == "remove":
        if len(nodes_after) <= 1:
            membership_event = "none"  # cannot remove the only node
        else:
            nodes_after.remove(nodes_after[-1])
    elif membership_event != "none":
        raise ValueError("membership_event must be none/add/remove")

    if membership_event != "none":
        membership_started = time.perf_counter()
        primary_after, ring_after = _owner_map(algorithm, keys, nodes_after, virtual_nodes)
        membership_seconds = time.perf_counter() - membership_started
        remapped_keys = sum(primary_before[k] != primary_after[k] for k in keys)
        remapping_rate = remapped_keys / len(keys) * 100
        # Route against the post-event membership to make membership and request routing comparable.
        primary_map, ring = primary_after, ring_after
    else:
        membership_seconds = 0.0
        remapped_keys = 0
        remapping_rate = 0.0
        primary_map, ring = primary_before, ring_before

    if algorithm == "CH-LA":
        loads, reassigned, routing_seconds = _route_requests(
            algorithm, requests, primary_map, nodes_after, ring, alpha, candidates, variant
        )
    else:
        loads, reassigned, routing_seconds = _route_requests(
            algorithm, requests, primary_map, nodes_after, ring, alpha, candidates, "ordinary"
        )
    metrics = load_metrics(loads)
    row = {
        "algorithm": algorithm, "nodes": nodes_count, "active_nodes_after": len(nodes_after),
        "keys": key_count, "requests": request_count, "workload": workload.lower(),
        "zipf_alpha": zipf_alpha if workload.lower() == "zipf" else 0.0,
        "load_threshold": alpha, "candidate_count": candidates, "seed": seed,
        "membership_event": membership_event, "variant": variant,
        **metrics,
        "remapped_keys": remapped_keys, "membership_remapping_rate_pct": remapping_rate,
        "reassigned_requests": reassigned,
        "load_reassignment_rate_pct": reassigned / request_count * 100,
        "build_time_seconds": build_seconds, "membership_rebuild_seconds": membership_seconds,
        "routing_time_seconds": routing_seconds,
        "routing_ops_per_second": request_count / routing_seconds if routing_seconds else 0,
        "peak_memory_bytes": before_memory,
    }
    return row
