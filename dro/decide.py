"""Let the fly choose between two options and write the run log.

Usage::

    python -m dro.decide --graph data/compiled                 # next question in questions.json
    python -m dro.decide --question my.json --graph data/compiled  # one particular question

How a decision is made:

1. Each option is drawn as a small picture. The rig turns the picture into
   firing of the object-detecting LC10a cells of one side: each cell fires
   in proportion to the contrast of the picture where that cell looks (see
   ``stimulus.py``).
2. Trial 1 shows option A to the left eye and option B to the right eye.
   Trial 2 swaps them, so a built-in preference for one side cancels out.
3. In each trial the spikes of the steering neuron DNa02, which descends
   from the brain to the body, are counted on the left and on the right.
   More spikes on one side is read as a turn towards that side, i.e.
   towards the option shown there.
4. The option the fly turned towards more, summed over both trials, wins.
   If the two sums are equal the fly is "undecided", and that is logged
   as it is.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

from . import __version__
from .graph import Graph, load
from .sim import Params, simulate
from .stimulus import INPUT_TYPE, RULE, input_rates, render, views

# A descending neuron known to steer walking: activity on one side turns the
# fly towards that side. DNa01 is not read: it has almost no excitatory
# visual input in this dataset (docs/CALIBRATION_NOTES.md, experiment 12).
STEERING_TYPES = ("DNa02",)
# Dopamine neurons of the mushroom body: PAM signals reward, PPL1 punishment.
REWARD_PREFIX = "PAM"
PUNISH_PREFIX = "PPL1"

ATTRIBUTION = (
    "Connectome: MaleCNS v1.0, FlyEM Project Team at HHMI Janelia, Cambridge "
    "Connectomics Group and Google Research, CC BY 4.0 (Berg et al., Cell 2026). "
    "Neuron model: Shiu et al., Nature 2024."
)


def _side_indices(graph: Graph, types: tuple[str, ...], side: str) -> np.ndarray:
    meta = graph.meta
    mask = meta["type"].isin(types) & (meta["somaSide"] == side)
    return np.flatnonzero(mask.to_numpy(dtype=bool, na_value=False))


def _prefix_indices(graph: Graph, prefix: str) -> np.ndarray:
    return np.flatnonzero(graph.meta["type"].fillna("").str.startswith(prefix).to_numpy())


def input_by_option(trials: list[dict]) -> tuple[dict, str]:
    """Mean input rate the rig produced for each option, and which is higher.

    This is the choice the rig's contrast rule would make on its own, before
    the brain runs: "a", "b" or "tie".
    """
    shown = {"a": [], "b": []}
    for trial in trials:
        shown[trial["left_eye"]].append(trial["input_rate_hz_left"])
        shown[trial["right_eye"]].append(trial["input_rate_hz_right"])
    rate = {option: round(float(np.mean(values)), 1) for option, values in shown.items()}
    if rate["a"] == rate["b"]:
        return rate, "tie"
    return rate, "a" if rate["a"] > rate["b"] else "b"


def log_order(path: Path) -> tuple:
    """Sort key for run logs: date, then the run number within that date."""
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:-(\d+))?", path.stem)
    return (match.group(1), int(match.group(2) or 1)) if match else ("", 0)


def next_question(queue: list[dict], runs: Path) -> dict:
    """The question to ask next.

    The first entry of the queue whose pair of options has no run log yet.
    Once every entry has been asked, the one asked longest ago. The choice
    depends only on the queue and the logs, never on a result.
    """
    last_asked = {}
    logs = sorted((path for path in runs.glob("*.json") if log_order(path)[0]), key=log_order)
    for position, path in enumerate(logs):
        options = json.loads(path.read_text(encoding="utf-8")).get("options", {})
        last_asked[frozenset(options.values())] = position
    return min(queue, key=lambda entry: last_asked.get(frozenset((entry["a"], entry["b"])), -1))


def make_seed(date: str, question: str, option_a: str, option_b: str) -> int:
    """A seed fixed by the day and the question, so a run cannot be cherry-picked."""
    text = "\n".join([date, question, option_a, option_b]).encode()
    return int.from_bytes(hashlib.sha256(text).digest()[:4], "big")


def decide(
    graph: Graph,
    question: str,
    option_a: str,
    option_b: str,
    seed: int,
    duration_ms: float = 1000.0,
    max_rate_hz: float = 150.0,
    params: Params = Params(),
    base_dir: Path = Path("."),
) -> tuple[dict, list]:
    """Run both trials. Returns the log record and the raw trial results."""
    pictures = {"a": render(option_a, base_dir), "b": render(option_b, base_dir)}
    steer = {side: _side_indices(graph, STEERING_TYPES, side) for side in ("L", "R")}
    reward, punish = _prefix_indices(graph, REWARD_PREFIX), _prefix_indices(graph, PUNISH_PREFIX)
    seconds = duration_ms / 1000.0
    eye = views(graph)

    trials, results = [], []
    toward = {"a": 0, "b": 0}
    reward_spikes = punish_spikes = total_spikes = 0
    for number, (left, right) in enumerate((("a", "b"), ("b", "a")), start=1):
        rates = input_rates(graph, pictures[left], pictures[right], max_rate_hz, eye)
        result = simulate(graph.weights, rates, duration_ms, seed + number, params)
        counts = result.spike_counts
        steer_left, steer_right = int(counts[steer["L"]].sum()), int(counts[steer["R"]].sum())
        toward[left] += steer_left
        toward[right] += steer_right
        reward_spikes += int(counts[reward].sum())
        punish_spikes += int(counts[punish].sum())
        total_spikes += int(counts.sum())
        trials.append(
            {
                "trial": number,
                "left_eye": left,
                "right_eye": right,
                # Set by the rig before the brain runs: mean input rate of the
                # cells that were shown each picture.
                "input_rate_hz_left": round(float(rates[eye["L"].cells].mean()), 1),
                "input_rate_hz_right": round(float(rates[eye["R"].cells].mean()), 1),
                "steering_spikes_left": steer_left,
                "steering_spikes_right": steer_right,
                "neurons_active": int((counts > 0).sum()),
                "spikes": int(counts.sum()),
            }
        )
        results.append(result)

    if toward["a"] > toward["b"]:
        choice = "a"
    elif toward["b"] > toward["a"]:
        choice = "b"
    else:
        choice = "undecided"
    labels = {"a": option_a, "b": option_b, "undecided": None}
    input_rate, by_input = input_by_option(trials)

    record = {
        "question": question,
        "options": {"a": option_a, "b": option_b},
        "choice": choice,
        "choice_label": labels[choice],
        "steering_spikes_toward": toward,
        # What the rig's contrast rule alone would have chosen. When this
        # equals "choice", the brain passed the rig's difference on.
        "input_rate_hz": input_rate,
        "choice_by_input_alone": by_input,
        "mood": {
            "reward_rate_hz": round(reward_spikes / max(reward.size, 1) / (2 * seconds), 2),
            "punish_rate_hz": round(punish_spikes / max(punish.size, 1) / (2 * seconds), 2),
        },
        "trials": trials,
        "total_spikes": total_spikes,
        "seed": seed,
        "duration_ms_per_trial": duration_ms,
        "max_input_rate_hz": max_rate_hz,
        "steering_types": list(STEERING_TYPES),
        "input": {
            "cell_type": INPUT_TYPE,
            "cells_left": int(eye["L"].cells.size),
            "cells_right": int(eye["R"].cells.size),
            "rule": RULE,
        },
        "model": params.as_dict(),
        "graph": graph.info,
        "who_did_what": {
            "fly": "where each input cell looks, how its firing spreads and "
            "competes between the two sides, which side the steering neuron "
            "fired on, and so the choice",
            "rig": "the question, the options, drawing them as pictures, "
            "the early vision (turning picture contrast into firing of the "
            "input cells), the rule that reads a turn as a choice",
        },
        "attribution": ATTRIBUTION,
        "dro_version": __version__,
    }
    return record, results


def save_raster(graph: Graph, result, path: Path, title: str, sample: int = 6000) -> None:
    """Draw which neurons fired when, for a random sample of neurons."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(0)
    order = graph.meta["superclass"].fillna("zz_unknown").to_numpy()
    picked = np.sort(rng.choice(graph.n, size=min(sample, graph.n), replace=False))
    picked = picked[np.argsort(order[picked], kind="stable")]
    row_of = np.full(graph.n, -1, dtype=np.int32)
    row_of[picked] = np.arange(picked.size)
    rows = row_of[result.spike_neurons]
    shown = rows >= 0

    figure, axis = plt.subplots(figsize=(10, 5.6), dpi=120)
    figure.patch.set_facecolor("#0b0b0d")
    axis.set_facecolor("#0b0b0d")
    axis.scatter(
        result.spike_times_ms[shown], rows[shown], s=0.6, c="#ffb000", linewidths=0, alpha=0.8
    )
    axis.set_xlim(0, result.duration_ms)
    axis.set_ylim(0, picked.size)
    axis.set_xlabel("time, ms", color="#c9c9c9")
    axis.set_ylabel(f"{picked.size:,} sampled neurons, grouped by class", color="#c9c9c9")
    axis.set_title(title, color="#f2f2f2", loc="left", fontsize=11)
    axis.tick_params(colors="#8a8a8a")
    for spine in axis.spines.values():
        spine.set_color("#333333")
    figure.tight_layout()
    figure.savefig(path, facecolor=figure.get_facecolor())
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Let the fly choose between two options.")
    parser.add_argument("--question", type=Path, help="a file with one question; overrides --queue")
    parser.add_argument("--queue", type=Path, default=Path("questions.json"), help="the question queue")
    parser.add_argument("--graph", type=Path, default=Path("data/compiled"))
    parser.add_argument("--runs", type=Path, default=Path("runs"))
    parser.add_argument("--date", help="run date, YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--seed", type=int, help="override the seed derived from date and question")
    parser.add_argument("--duration-ms", type=float, default=1000.0)
    parser.add_argument("--no-raster", action="store_true")
    args = parser.parse_args(argv)

    if args.question:
        source = args.question
        spec = json.loads(source.read_text(encoding="utf-8"))
    else:
        source = args.queue
        spec = next_question(json.loads(source.read_text(encoding="utf-8")), args.runs)
    question, option_a, option_b = spec["question"], spec["a"], spec["b"]
    date = args.date or dt.datetime.now(dt.timezone.utc).date().isoformat()
    seed = args.seed if args.seed is not None else make_seed(date, question, option_a, option_b)

    graph = load(args.graph)
    started = time.time()
    record, results = decide(
        graph,
        question,
        option_a,
        option_b,
        seed,
        duration_ms=args.duration_ms,
        base_dir=source.parent,
    )
    record = {"date": date, **record, "runtime_s": round(time.time() - started, 1)}
    # What is already known about how often this pair gives the same winner.
    # Written by a human into the question file and passed on unchanged.
    if "repeatability" in spec:
        record["repeatability"] = spec["repeatability"]

    args.runs.mkdir(parents=True, exist_ok=True)
    stem = date
    suffix = 1
    while (args.runs / f"{stem}.json").exists():
        suffix += 1
        stem = f"{date}-{suffix}"
    if not args.no_raster:
        raster = args.runs / f"{stem}.png"
        save_raster(graph, results[0], raster, f"Dro, {date}: {question}")
        record["raster"] = raster.name
    (args.runs / f"{stem}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    verdict = record["choice_label"] or "undecided"
    print(f"{question} -> {verdict}  (toward a: {record['steering_spikes_toward']['a']}, "
          f"toward b: {record['steering_spikes_toward']['b']})")
    print(f"log: {args.runs / (stem + '.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
