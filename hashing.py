"""Deterministic hashing algorithms used by the distributed hashing simulator."""
from __future__ import annotations
import bisect
import hashlib
from typing import Iterable

def stable_hash(value: str) -> int:
    """Return a stable 64-bit hash (unlike Python's process-randomized hash())."""
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=False)

class ConsistentHashRing:
    """Consistent-hashing ring with a fixed number of virtual nodes per physical node."""
    def __init__(self, nodes: Iterable[str], virtual_nodes: int = 100):
        if virtual_nodes < 1:
            raise ValueError("virtual_nodes must be >= 1")
        self.virtual_nodes = virtual_nodes
        self.nodes = sorted(set(nodes))
        self._positions = []
        self._owners = []
        for node in self.nodes:
            for replica in range(virtual_nodes):
                pos = stable_hash(f"vnode:{node}:{replica}")
                self._positions.append(pos)
                self._owners.append(node)
        ordered = sorted(zip(self._positions, self._owners), key=lambda item: (item[0], item[1]))
        self._positions = [x[0] for x in ordered]
        self._owners = [x[1] for x in ordered]

    def primary(self, key: str) -> str:
        if not self.nodes:
            raise ValueError("Cannot route with an empty node set")
        if not self._positions:
            raise ValueError("Ring has no positions")
        point = stable_hash(f"key:{key}")
        idx = bisect.bisect_left(self._positions, point)
        if idx == len(self._positions):
            idx = 0
        return self._owners[idx]

    def next_distinct_nodes(self, key: str, count: int, exclude: str | None = None) -> list[str]:
        """Return up to count distinct physical nodes clockwise from the key position.

        The primary owner is excluded by default, matching the paper's definition.
        """
        if count <= 0 or len(self.nodes) <= 1:
            return []
        point = stable_hash(f"key:{key}")
        idx = bisect.bisect_left(self._positions, point)
        if idx == len(self._positions):
            idx = 0
        result, seen = [], set()
        # At most one full ring traversal; every physical node can appear many times.
        for offset in range(len(self._positions)):
            owner = self._owners[(idx + offset) % len(self._owners)]
            if owner == exclude or owner in seen:
                continue
            seen.add(owner)
            result.append(owner)
            if len(result) >= min(count, len(self.nodes) - (1 if exclude in self.nodes else 0)):
                break
        return result

def rendezvous_primary(key: str, nodes: Iterable[str]) -> str:
    """Highest-random-weight / rendezvous hashing, deterministic tie-breaking."""
    node_list = sorted(set(nodes))
    if not node_list:
        raise ValueError("Cannot route with an empty node set")
    # Maximize the deterministic score; node name resolves the extremely unlikely tie.
    return max(node_list, key=lambda node: (stable_hash(f"rh:{key}:{node}"), node))
