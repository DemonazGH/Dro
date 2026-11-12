"""Sanity check: sugar-sensing neurons should drive the proboscis motor neuron.

This repeats, on MaleCNS, the first result of Shiu et al. (Nature 2024):
activating the sugar-sensing gustatory receptor neurons of one side makes the
proboscis motor neuron MN9 fire, more strongly at higher input rates, while
activity stays inside a small circuit (a few hundred neurons).

Usage::

    python -m dro.sanity --graph data/compiled

The check passes when, at every input rate and seed,

* the number of active neurons stays below ``--max-active``, and
* the MN9 rate does not fall as the input rate rises, and is above zero at
  the highest input rate.

Sugar-sensing neurons are taken to be the labellar bristle types LB3a to
LB3d. MaleCNS does not label taste quality; these are the types that connect
to the second-order sugar neurons named in the release (see
``docs/CALIBRATION_NOTES.md``, experiment 6).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

from .graph import Graph, load
from .sim import Params, simulate

SUGAR_TYPES = ("LB3a", "LB3b", "LB3c", "LB3d")
MOTOR_TYPE = "MN9"


def sugar_neurons(graph: Graph, side: str) -> np.ndarray:
    """Sugar-sensing neurons whose nerve enters on the given side (L or R)."""
    meta = graph.meta
    mask = meta["type"].isin(SUGAR_TYPES) & meta["instance"].fillna("").str.endswith(f"_{side}")
    return np.flatnonzero(mask.to_numpy(dtype=bool, na_value=False))


def run(
    graph: Graph,
    rates_hz: list[float],
    seeds: list[int],
    side: str = "R",
    duration_ms: float = 1000.0,
    params: Params = Params(),
) -> list[dict]:
    """One row per input rate and seed."""
    inputs = sugar_neurons(graph, side)
    motor = np.flatnonzero((graph.meta["type"] == MOTOR_TYPE).to_numpy(dtype=bool, na_value=False))
    seconds = duration_ms / 1000.0
    rows = []
    for rate in rates_hz:
        drive = np.zeros(graph.n)
        drive[inputs] = rate
        for seed in seeds:
            counts = simulate(graph.weights, drive, duration_ms, seed, params).spike_counts
            rows.append(
                {
                    "rate_hz": rate,
                    "seed": seed,
                    # There is one MN9 per side; report the more active one.
                    "mn9_hz": float(counts[motor].max()) / seconds if motor.size else 0.0,
                    "active": int((counts > 0).sum()),
                    "spikes": int(counts.sum()),
                }
            )
    return rows


def verdict(rows: list[dict], max_active: int) -> tuple[bool, list[str]]:
    """Whether the rows pass, and why not if they do not."""
    problems = []
    for row in rows:
        if row["active"] >= max_active:
            problems.append(
                f"{row['active']:,} neurons active at {row['rate_hz']:g} Hz, seed {row['seed']}"
            )
    rates = sorted({row["rate_hz"] for row in rows})
    mean = [np.mean([row["mn9_hz"] for row in rows if row["rate_hz"] == rate]) for rate in rates]
    if any(later < earlier for earlier, later in zip(mean, mean[1:])):
        problems.append("the MN9 rate falls as the input rate rises")
    if mean and mean[-1] <= 0:
        problems.append("MN9 is silent at the highest input rate")
    return not problems, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sugar neurons to MN9 sanity check.")
    parser.add_argument("--graph", type=Path, default=Path("data/compiled"))
    parser.add_argument("--rates", default="10,50,100,150,200", help="input rates in Hz")
    parser.add_argument("--seeds", default="1,2,3")
    parser.add_argument("--side", choices=("L", "R"), default="R")
    parser.add_argument("--duration-ms", type=float, default=1000.0)
    parser.add_argument("--w-synapse-mv", type=float, help="override the synapse strength")
    parser.add_argument("--max-active", type=int, default=1000)
    args = parser.parse_args(argv)

    params = Params()
    if args.w_synapse_mv is not None:
        params = replace(params, w_synapse_mv=args.w_synapse_mv)
    graph = load(args.graph)
    rates = [float(rate) for rate in args.rates.split(",")]
    seeds = [int(seed) for seed in args.seeds.split(",")]
    print(
        f"{sugar_neurons(graph, args.side).size} sugar neurons on side {args.side}, "
        f"{params.w_synapse_mv} mV per synapse, {args.duration_ms:g} ms per run"
    )
    rows = run(graph, rates, seeds, args.side, args.duration_ms, params)

    print(f"{'input Hz':>8}  {'MN9 Hz by seed':<24}  {'active neurons':<24}  spikes")
    for rate in rates:
        group = [row for row in rows if row["rate_hz"] == rate]
        mn9 = ", ".join(format(row["mn9_hz"], "g") for row in group)
        active = ", ".join(str(row["active"]) for row in group)
        spikes = ", ".join(str(row["spikes"]) for row in group)
        print(f"{rate:>8g}  {mn9:<24}  {active:<24}  {spikes}")
    passed, problems = verdict(rows, args.max_active)
    print("PASS" if passed else "FAIL: " + "; ".join(problems))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
