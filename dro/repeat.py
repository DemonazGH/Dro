"""Does the same pair of options give the same winner again and again?

Runs one pair over many seeds and counts the winners. Two uses:

* Repeatability: two different options. The roadmap asks for the same
  winner in at least 16 of 20 runs.
* Control: the same option on both sides (give it as ``--a`` and ``--b``).
  The two "options" should then win about equally often.

Usage::

    python -m dro.repeat --a yes --b no
    python -m dro.repeat --a yes --b yes

This is a measuring tool. It must never be used to pick a seed for a real
decision: the daily run takes its seed from the date and the question.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .decide import decide
from .graph import Graph, load

# The two trials of a decision use seed + 1 and seed + 2, so seeds are
# spaced out to keep the runs independent of each other.
SEED_STEP = 10


def run(graph: Graph, option_a: str, option_b: str, runs: int, base_dir: Path = Path(".")) -> list[dict]:
    """One short record per run."""
    rows = []
    for number in range(1, runs + 1):
        record, _ = decide(graph, "repeat", option_a, option_b, number * SEED_STEP, base_dir=base_dir)
        rows.append(
            {
                "seed": number * SEED_STEP,
                "choice": record["choice"],
                "toward_a": record["steering_spikes_toward"]["a"],
                "toward_b": record["steering_spikes_toward"]["b"],
            }
        )
    return rows


def summary(rows: list[dict]) -> dict:
    """Winner counts and the share of runs won by the most frequent winner."""
    counts = Counter(row["choice"] for row in rows)
    wins = max(counts.get("a", 0), counts.get("b", 0))
    return {
        "a": counts.get("a", 0),
        "b": counts.get("b", 0),
        "undecided": counts.get("undecided", 0),
        "same_winner_share": wins / len(rows) if rows else 0.0,
        "mean_toward_a": sum(row["toward_a"] for row in rows) / max(len(rows), 1),
        "mean_toward_b": sum(row["toward_b"] for row in rows) / max(len(rows), 1),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repeat one pair of options over many seeds.")
    parser.add_argument("--a", required=True)
    parser.add_argument("--b", required=True)
    parser.add_argument("--graph", type=Path, default=Path("data/compiled"))
    parser.add_argument("--runs", type=int, default=20)
    args = parser.parse_args(argv)

    rows = run(load(args.graph), args.a, args.b, args.runs)
    for row in rows:
        print(f"seed {row['seed']:>4}: {row['choice']:<9}  a {row['toward_a']:>4}  b {row['toward_b']:>4}")
    result = summary(rows)
    print(
        f"a won {result['a']}, b won {result['b']}, undecided {result['undecided']} "
        f"of {len(rows)}; mean steering spikes a {result['mean_toward_a']:.1f}, "
        f"b {result['mean_toward_b']:.1f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
