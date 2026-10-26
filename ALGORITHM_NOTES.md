# Algorithm and paper-alignment notes

## Mapping from paper to source files

- Section 5.1 Consistent Hashing: `hashing.py` → `ConsistentHashRing`
- Section 5.2 Rendezvous Hashing: `hashing.py` → `rendezvous_primary`
- Section 5.3.1 Load-aware routing: `simulator.py` → `_route_requests`
- Section 7 workload generation: `workloads.py`
- Section 8 load/movement/performance metrics: `metrics.py` and `simulator.py`
- Section 14 experiment CLI/reproducibility: `main.py`
- Figures: `plot_results.py`

## Exact CH-LA decision sequence implemented

1. Determine the CH primary owner for the request key.
2. Compute the mean of current request counts across active nodes.
3. If primary load is no greater than alpha times mean load, route to primary.
4. Otherwise discover up to C distinct alternative physical nodes clockwise from the key's ring position, excluding the primary.
5. Route to the first candidate in ring order whose load is no greater than the threshold.
6. If none qualifies, route to the least-loaded examined candidate; ties use smallest node ID.
7. Increment the selected destination's request counter.
8. Count a reassignment if selected destination differs from primary.

## Important distinction

This implementation simulates request routing. It does not move persistent key/value data or implement replication, network RPCs, queueing delays, or cluster coordination. Therefore, request reassignment is not persistent key remapping.

## Known modeling choice to disclose

The paper describes the threshold as alpha times the mean load. Here, the mean is recalculated from the current online request counters before every request. Since the sum of the counters equals the number of requests already processed, this is a dynamic mean; at the start it is zero. If the intended paper design is to compare against a fixed expected mean (`request_count / active_nodes`) or a moving time window, change the threshold definition and rerun all experiments before reporting results. Do not mix results from different threshold definitions.
