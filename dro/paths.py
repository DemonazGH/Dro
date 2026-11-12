"""Find and test routes through the graph to a set of target neurons.

Two tools, both used to look for a visual route to the steering neurons:

``rank``
    Graph search, no simulation. For every cell type it adds up the strength
    of all excitatory paths of one, two and three steps to the target.

``drive``
    Simulation. Fires every cell of the given types on one side at a fixed
    rate and counts the spikes of the steering neurons on both sides.

Usage::

    python -m dro.paths rank DNa02 --side R
    python -m dro.paths drive LC10a --side R --rates 50,100,200

Path strength: a connection counts as its share of the receiving neuron's
input synapses (excitatory and inhibitory together). The strength of a path
is the product of these shares along it. Only excitatory connections are
followed, because every neuron in this model is silent at rest, so removing
inhibition cannot start activity.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

from .graph import Graph, load
from .sim import Params, simulate

STEERING_TYPES = ("DNa01", "DNa02")


def cells(graph: Graph, types: tuple[str, ...] | list[str], side: str) -> np.ndarray:
    """Neurons of the given types with their cell body on the given side."""
    meta = graph.meta
    mask = meta["type"].isin(types) & (meta["somaSide"] == side)
    return np.flatnonzero(mask.to_numpy(dtype=bool, na_value=False))


def excitatory_shares(graph: Graph) -> sparse.csr_matrix:
    """Excitatory connections as shares of the receiving neuron's input."""
    weights = graph.weights.tocsr()
    total_input = np.asarray(abs(weights).sum(axis=0)).ravel()
    total_input[total_input == 0] = 1.0
    return (weights.maximum(0) @ sparse.diags(1.0 / total_input)).tocsr()


def path_strength(graph: Graph, targets: np.ndarray, steps: int = 3) -> list[np.ndarray]:
    """For each step count 1..steps: every neuron's path strength to the targets."""
    shares = excitatory_shares(graph)
    reach = np.zeros(graph.n)
    reach[targets] = 1.0 / max(targets.size, 1)
    out = []
    for _ in range(steps):
        reach = shares @ reach
        out.append(reach.copy())
    return out


def rank(graph: Graph, target_type: str, side: str, superclass: str | None, steps: int = 3) -> pd.DataFrame:
    """Cell types ordered by summed path strength to the target, by step count."""
    strengths = path_strength(graph, cells(graph, [target_type], side), steps)
    meta = graph.meta
    table = pd.DataFrame(
        {
            "type": meta["type"].fillna("untyped"),
            "side": meta["somaSide"].fillna("?"),
            "superclass": meta["superclass"].fillna("unknown"),
        }
    )
    names = [f"steps_{number}" for number in range(1, steps + 1)]
    for name, strength in zip(names, strengths):
        table[name] = strength
    if superclass:
        table = table[table["superclass"] == superclass]
    grouped = table.groupby(["type", "side"]).agg(cells=("type", "size"), **{n: (n, "sum") for n in names})
    grouped["total"] = grouped[names].sum(axis=1)
    return grouped.sort_values("total", ascending=False).reset_index()


def drive(
    graph: Graph,
    types: list[str],
    side: str,
    rate_hz: float,
    seed: int = 1,
    duration_ms: float = 1000.0,
    params: Params = Params(),
) -> dict:
    """Fire the given cell types on one side and read the steering neurons."""
    sources = cells(graph, types, side)
    rates = np.zeros(graph.n)
    rates[sources] = rate_hz
    counts = simulate(graph.weights, rates, duration_ms, seed, params).spike_counts
    row = {"cells_driven": int(sources.size), "rate_hz": rate_hz, "seed": seed}
    for steering in STEERING_TYPES:
        for readout_side in ("L", "R"):
            row[f"{steering}_{readout_side}"] = int(counts[cells(graph, [steering], readout_side)].sum())
    row["active"] = int((counts > 0).sum())
    row["spikes"] = int(counts.sum())
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find and test routes to target neurons.")
    parser.add_argument("--graph", type=Path, default=Path("data/compiled"))
    commands = parser.add_subparsers(dest="command", required=True)

    rank_parser = commands.add_parser("rank", help="rank cell types by path strength to a target")
    rank_parser.add_argument("target", help="target cell type, for example DNa02")
    rank_parser.add_argument("--side", choices=("L", "R"), default="R")
    rank_parser.add_argument("--superclass", default="visual_projection", help="'' for all")
    rank_parser.add_argument("--top", type=int, default=15)

    drive_parser = commands.add_parser("drive", help="fire cell types and read the steering neurons")
    drive_parser.add_argument("types", help="comma-separated cell types, for example LC10a")
    drive_parser.add_argument("--side", choices=("L", "R"), default="R")
    drive_parser.add_argument("--rates", default="50,100,200")
    drive_parser.add_argument("--seed", type=int, default=1)

    args = parser.parse_args(argv)
    graph = load(args.graph)
    pd.set_option("display.width", 200)
    if args.command == "rank":
        table = rank(graph, args.target, args.side, args.superclass or None)
        print(f"path strength to {args.target} on side {args.side}")
        print(table.head(args.top).round(4).to_string(index=False))
    else:
        rows = [
            drive(graph, args.types.split(","), args.side, float(rate), args.seed)
            for rate in args.rates.split(",")
        ]
        print(f"driving {args.types} on side {args.side}, spikes in 1 s")
        print(pd.DataFrame(rows).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
