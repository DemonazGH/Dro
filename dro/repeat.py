"""Does the same pair of options give the same winner again and again?

Runs one pair over many seeds and counts the winners. Two uses:

* Repeatability: two different options. The roadmap asks for the same
  winner in at least 16 of 20 runs.
* Control: the same option on both sides (give it as ``--a`` and ``--b``).
  The two "options" should then win about equally often.

Usage::

    python -m dro.repeat --a yes --b no
    python -m dro.repeat --a yes --b yes
    python -m dro.repeat --a tabs --b spaces --question "Tabs or spaces?" --add-to questions.json

With ``--add-to`` the pair is appended to the question queue, together with
a sentence on what was measured, but only if it repeats.

This is a measuring tool. It must never be used to pick a seed for a real
decision: the daily run takes its seed from the date and the question.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

from .decide import decide
from .graph import Graph, load

# The two trials of a decision use seed + 1 and seed + 2, so seeds are
# spaced out to keep the runs independent of each other.
SEED_STEP = 10
# A pair "repeats" when one option wins at least this share of the runs.
REPEAT_SHARE = 0.8


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
                "input_a": record["input_rate_hz"]["a"],
                "input_b": record["input_rate_hz"]["b"],
                "by_input": record["choice_by_input_alone"],
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


def repeats(result: dict) -> bool:
    """Whether one option won often enough to call the pair repeatable."""
    return result["same_winner_share"] >= REPEAT_SHARE


def note(option_a: str, option_b: str, rows: list[dict], date: str) -> str:
    """One sentence on what was measured, for the question queue and the logs."""
    result = summary(rows)
    winner, wins = (option_a, result["a"]) if result["a"] >= result["b"] else (option_b, result["b"])
    loser = option_b if winner == option_a else option_a
    won = result["mean_toward_a"] if winner == option_a else result["mean_toward_b"]
    lost = result["mean_toward_b"] if winner == option_a else result["mean_toward_a"]
    text = (
        f"Measured on {date} with python -m dro.repeat: {winner} won {wins} of {len(rows)} runs, "
        f"{won:.1f} steering spikes against {lost:.1f} on average."
    )
    by_input = rows[0]["by_input"]
    rate = {option_a: rows[0]["input_a"], option_b: rows[0]["input_b"]}
    if by_input == "tie":
        text += f" The two pictures have the same contrast ({rate[winner]} Hz of input each)."
    elif (by_input == "a") == (winner == option_a):
        text += f" {winner} is also the picture with more contrast ({rate[winner]} Hz of input against {rate[loser]} Hz)."
    else:
        text += f" {loser} is the picture with more contrast ({rate[loser]} Hz of input against {rate[winner]} Hz)."
    return text


def add_to_queue(queue: Path, question: str, option_a: str, option_b: str, measured: str) -> bool:
    """Append a question to the queue file. Returns False if the pair is already there."""
    entries = json.loads(queue.read_text(encoding="utf-8")) if queue.exists() else []
    if any({entry["a"], entry["b"]} == {option_a, option_b} for entry in entries):
        return False
    entries.append({"question": question, "a": option_a, "b": option_b, "repeatability": measured})
    queue.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repeat one pair of options over many seeds.")
    parser.add_argument("--a", required=True)
    parser.add_argument("--b", required=True)
    parser.add_argument("--graph", type=Path, default=Path("data/compiled"))
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--question", help="the question to store with --add-to")
    parser.add_argument("--add-to", type=Path, help="question queue to append the pair to if it repeats")
    args = parser.parse_args(argv)
    if args.add_to and not args.question:
        parser.error("--add-to needs --question")

    rows = run(load(args.graph), args.a, args.b, args.runs)
    for row in rows:
        print(f"seed {row['seed']:>4}: {row['choice']:<9}  a {row['toward_a']:>4}  b {row['toward_b']:>4}")
    result = summary(rows)
    print(
        f"a won {result['a']}, b won {result['b']}, undecided {result['undecided']} "
        f"of {len(rows)}; mean steering spikes a {result['mean_toward_a']:.1f}, "
        f"b {result['mean_toward_b']:.1f}"
    )
    measured = note(args.a, args.b, rows, dt.datetime.now(dt.timezone.utc).date().isoformat())
    print(measured)
    if args.add_to:
        if not repeats(result):
            print(f"not added: no option won {REPEAT_SHARE:.0%} of the runs, so this pair may be a coin toss")
        elif add_to_queue(args.add_to, args.question, args.a, args.b, measured):
            print(f"added to {args.add_to}")
        else:
            print(f"not added: {args.add_to} already holds this pair")
    return 0


if __name__ == "__main__":
    sys.exit(main())
