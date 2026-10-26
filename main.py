"""Command-line entry point for reproducible distributed hashing experiments."""
from __future__ import annotations
import argparse
import csv
import itertools
import os
from simulator import run_single, ALGORITHMS

def parse_args():
    p = argparse.ArgumentParser(description="Compare CH, RH, and load-aware CH routing.")
    p.add_argument("--mode", choices=["main", "sensitivity"], default="main")
    p.add_argument("--sensitivity-type", choices=["alpha", "candidate", "workload"], default="alpha")
    p.add_argument("--nodes", nargs="+", type=int, default=[5, 10, 20, 50, 100])
    p.add_argument("--requests", nargs="+", type=int, default=[10000, 100000])
    p.add_argument("--keys", type=int, default=10000)
    p.add_argument("--virtual-nodes", type=int, default=100)
    p.add_argument("--alpha", type=float, default=1.25)
    p.add_argument("--candidates", type=int, default=4)
    p.add_argument("--seeds", nargs="+", type=int, default=list(range(42, 52)))
    p.add_argument("--workloads", nargs="+", choices=["uniform", "zipf"], default=["uniform", "zipf"])
    p.add_argument("--zipf-alpha", type=float, default=1.0)
    p.add_argument("--alpha-values", nargs="+", type=float, default=[1.0, 1.1, 1.25, 1.5])
    p.add_argument("--candidate-values", nargs="+", type=int, default=[2, 4, 8])
    p.add_argument("--zipf-params", nargs="+", type=float, default=[0.5, 1.0, 1.5])
    p.add_argument("--membership-events", nargs="+", choices=["none", "add", "remove"], default=["none"])
    p.add_argument("--output", default="results.csv")
    return p.parse_args()

def write_csv(rows, path):
    if not rows:
        raise RuntimeError("No experiment rows generated.")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fieldnames = list(dict.fromkeys(k for row in rows for k in row.keys()))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {path}")

def main():
    args = parse_args()
    configs = []
    if args.mode == "main":
        for nodes, requests, workload, seed, event in itertools.product(
            args.nodes, args.requests, args.workloads, args.seeds, args.membership_events
        ):
            za = args.zipf_alpha
            for alg in ALGORITHMS:
                configs.append((nodes, requests, workload, seed, event, alg, args.alpha, args.candidates, za))
    else:
        if args.sensitivity_type == "alpha":
            for nodes, requests, seed, alpha in itertools.product(args.nodes, args.requests, args.seeds, args.alpha_values):
                for alg in ALGORITHMS:
                    configs.append((nodes, requests, "zipf", seed, "none", alg, alpha, args.candidates, args.zipf_alpha))
        elif args.sensitivity_type == "candidate":
            for nodes, requests, seed, c in itertools.product(args.nodes, args.requests, args.seeds, args.candidate_values):
                for alg in ALGORITHMS:
                    configs.append((nodes, requests, "zipf", seed, "none", alg, args.alpha, c, args.zipf_alpha))
        else:
            for nodes, requests, seed, za in itertools.product(args.nodes, args.requests, args.seeds, args.zipf_params):
                for alg in ALGORITHMS:
                    configs.append((nodes, requests, "zipf", seed, "none", alg, args.alpha, args.candidates, za))
    rows = []
    for i, (nodes, requests, workload, seed, event, alg, alpha, c, za) in enumerate(configs, 1):
        print(f"[{i}/{len(configs)}] {alg}, nodes={nodes}, requests={requests}, workload={workload}, seed={seed}")
        rows.append(run_single(nodes, requests, workload, seed, args.keys, args.virtual_nodes,
                               alpha, c, za, event, alg))
    write_csv(rows, args.output)

if __name__ == "__main__":
    main()
