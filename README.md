# Distributed Hashing Experiment Simulator

This project implements the experimental framework described in the uploaded paper,
**“Load Balance, Key Remapping, and Lookup Overhead in Distributed Hashing Under Dynamic Workloads.”**

It compares:
- **CH** — Consistent Hashing with 100 virtual nodes per physical node by default.
- **RH** — Rendezvous / Highest Random Weight hashing.
- **CH-LA** — bounded-candidate load-aware request routing over the CH primary owner.

## Important interpretation note

This is a **single-process simulation**, not a deployed distributed cluster. Routing timing is algorithmic simulation time, not network latency or production throughput. The program generates new measurements; do not describe generated results as previously observed paper findings until you run and validate them.

The paper's Results section is unfinished. Run the experiments and use the generated CSV and plots to complete that section with actual measured values.

## Requirements

- Python 3.10 or newer recommended
- Install packages:

```bash
python -m pip install -r requirements.txt
```

## Quick test

A smaller run is recommended before the full experiment:

```bash
python main.py --nodes 5 10 --requests 1000 --keys 1000 --seeds 42 --workloads uniform zipf --output smoke_test.csv
python plot_results.py smoke_test.csv --output-dir smoke_plots
```

## Main experiment

The paper's configuration uses 10,000 keys; 10,000 and 100,000 requests; node counts 5, 10, 20, 50, 100; uniform and Zipf(1.0) workloads; 100 virtual nodes; alpha=1.25; C=4; and seeds 42–51.

```bash
python main.py --nodes 5 10 20 50 100 --requests 10000 100000 --keys 10000 --virtual-nodes 100 --alpha 1.25 --candidates 4 --seeds 42 43 44 45 46 47 48 49 50 51 --workloads uniform zipf --output results.csv
python plot_results.py results.csv --output-dir plots
```

This main command can take a while because it executes all configurations and all three algorithms. Start with the quick test first.

## Dynamic membership experiment

Add one node or remove one node, recompute primary ownership, and record the fraction of keys whose primary owner changed:

```bash
python main.py --nodes 5 10 20 --requests 10000 --keys 10000 --seeds 42 43 44 --membership-events add remove --output membership.csv
```

The `membership_remapping_rate_pct` metric is based on primary-owner changes. It is deliberately distinct from `load_reassignment_rate_pct`, which counts individual requests sent away from the CH primary owner by CH-LA.

## Sensitivity experiments

### Threshold alpha

```bash
python main.py --mode sensitivity --sensitivity-type alpha --nodes 5 10 --requests 10000 --keys 10000 --alpha-values 1.0 1.1 1.25 1.5 --seeds 42 43 44 --output sensitivity_alpha.csv
```

### Candidate count C

```bash
python main.py --mode sensitivity --sensitivity-type candidate --nodes 5 10 --requests 10000 --keys 10000 --candidate-values 2 4 8 --seeds 42 43 44 --output sensitivity_candidates.csv
```

### Zipf skew

```bash
python main.py --mode sensitivity --sensitivity-type workload --nodes 5 10 --requests 10000 --keys 10000 --zipf-params 0.5 1.0 1.5 --seeds 42 43 44 --output sensitivity_workload.csv
```

## Output fields

| Field | Meaning |
|---|---|
| `algorithm` | CH, RH, or CH-LA |
| `nodes`, `active_nodes_after` | Initial and post-membership node counts |
| `keys`, `requests`, `workload`, `zipf_alpha`, `seed` | Workload configuration |
| `load_threshold`, `candidate_count` | CH-LA parameters |
| `mean_load`, `max_load`, `std_load`, `peak_to_average` | Request-load distribution |
| `jain_fairness` | Jain's fairness index (1.0 is perfectly even) |
| `p95_load`, `p99_load` | Nearest-rank percentiles across physical-node loads |
| `membership_remapping_rate_pct` | Percentage of keys whose primary owner changed due to membership event |
| `load_reassignment_rate_pct` | Percentage of requests routed away from their CH primary owner |
| `routing_time_seconds`, `routing_ops_per_second` | Simulation routing time and operations/second |
| `build_time_seconds`, `membership_rebuild_seconds` | Initialization and post-membership mapping time |
| `peak_memory_bytes` | Python allocation peak measured during one mapping/build call |

## Algorithm details and assumptions

1. **Stable hashing:** BLAKE2b 64-bit digests are used instead of Python's built-in `hash()` so runs are reproducible across processes.
2. **CH ring:** Each physical node has `virtual_nodes` ring positions. Lookup is binary search over sorted ring positions.
3. **RH:** Each key is scored against every active node; the node with the maximum score is primary owner.
4. **CH-LA:** First computes the CH primary owner. If that owner's current request count is above `alpha × current mean load`, the router examines up to C distinct alternative physical nodes in clockwise ring order. It chooses the first candidate at or below threshold. If none qualifies, the full policy selects the least-loaded examined candidate; ties are broken by lexicographically smallest node ID. If there are no alternatives (single-node cluster), it stays at the primary.
5. **Online load:** Request load is updated after each routed request. Because the load threshold uses the current mean across active nodes, early requests can behave differently from a policy that uses a fixed expected average. Document this implementation choice in the paper.
6. **Membership:** Add/remove experiments compare primary-owner maps before and after membership. Load-aware request redirection is not counted as key remapping.
7. **Memory:** `tracemalloc` records Python allocation peak for a mapping/build call. It is not total resident set size (RSS).

## Reproducibility checklist

- Keep the command line used for each CSV.
- Record the Git commit hash and Python/package versions.
- Preserve CSV files and plot images.
- Use the same seeds and request sequences for paired algorithm comparisons.
- Validate the implementation and report measured findings only after running the experiments.
