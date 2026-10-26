"""Generate publication-ready comparison plots from simulator CSV output."""
from __future__ import annotations
import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt

def save_plot(df, x, y, title, ylabel, path, filters=None):
    data = df.copy()
    if filters:
        for col, value in filters.items():
            data = data[data[col] == value]
    if data.empty or x not in data or y not in data:
        return
    grouped = data.groupby([x, "algorithm"], as_index=False)[y].mean()
    fig, ax = plt.subplots(figsize=(8, 5))
    for algorithm, group in grouped.groupby("algorithm"):
        group = group.sort_values(x)
        ax.plot(group[x], group[y], marker="o", label=algorithm)
    ax.set_title(title)
    ax.set_xlabel(x.replace("_", " ").title())
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv_file", nargs="?", default="results.csv")
    p.add_argument("--output-dir", default="plots")
    args = p.parse_args()
    df = pd.read_csv(args.csv_file)
    os.makedirs(args.output_dir, exist_ok=True)
    plot_specs = [
        ("nodes", "jain_fairness", "Jain Fairness by Node Count", "Jain's fairness index"),
        ("nodes", "max_load", "Maximum Node Load", "Requests on busiest node"),
        ("nodes", "std_load", "Load Standard Deviation", "Standard deviation of request load"),
        ("nodes", "peak_to_average", "Peak-to-Average Load Ratio", "Maximum / mean load"),
        ("nodes", "p95_load", "P95 Node Load", "P95 node request load"),
        ("nodes", "p99_load", "P99 Node Load", "P99 node request load"),
        ("nodes", "routing_time_seconds", "Routing Time", "Seconds"),
        ("nodes", "routing_ops_per_second", "Routing Operations per Second", "Operations / second"),
        ("nodes", "membership_remapping_rate_pct", "Membership-Induced Key Remapping", "Remapped keys (%)"),
        ("nodes", "load_reassignment_rate_pct", "Load-Induced Request Reassignment", "Reassigned requests (%)"),
        ("nodes", "build_time_seconds", "Build Time", "Seconds"),
        ("nodes", "peak_memory_bytes", "Peak Python Allocation", "Bytes"),
    ]
    filters = {}
    if "workload" in df.columns:
        filters["workload"] = "zipf" if (df["workload"] == "zipf").any() else df["workload"].iloc[0]
    if "requests" in df.columns:
        filters["requests"] = int(df["requests"].min())
    for x, y, title, ylabel in plot_specs:
        save_plot(df, x, y, title, ylabel, os.path.join(args.output_dir, y + ".png"), filters)
    # Sensitivity figures when the relevant columns are present.
    for x, y, title, ylabel in [
        ("load_threshold", "jain_fairness", "Threshold Sensitivity: Fairness", "Jain's fairness index"),
        ("candidate_count", "jain_fairness", "Candidate Sensitivity: Fairness", "Jain's fairness index"),
        ("zipf_alpha", "jain_fairness", "Zipf Skew Sensitivity: Fairness", "Jain's fairness index"),
    ]:
        save_plot(df, x, y, title, ylabel, os.path.join(args.output_dir, y + "_by_" + x + ".png"), filters)
    print(f"Plots saved to: {args.output_dir}")

if __name__ == "__main__":
    main()
