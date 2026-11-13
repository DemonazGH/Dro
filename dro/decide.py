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
    pictures: dict | None = None,
) -> tuple[dict, list]:
    """Run both trials. Returns the log record and the raw trial results.

    ``pictures`` may supply ready-made pictures for "a" and "b"; otherwise
    the options are drawn as text or loaded as image files.
    """
    pictures = pictures or {"a": render(option_a, base_dir), "b": render(option_b, base_dir)}
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


# Bands of the activity picture, bottom to top, and the cells in each.
PICTURE_BANDS = (
    ("shown the picture", lambda kind, group: kind == INPUT_TYPE),
    ("other visual cells", lambda kind, group: np.isin(group, ("ol_intrinsic", "visual_projection", "visual_centrifugal"))),
    ("central brain", lambda kind, group: np.char.startswith(group, "cb_")),
    ("to and from the body", lambda kind, group: np.ones(kind.shape, dtype=bool)),
)
AMBER, ACCENT, PAPER, INK = "#ffb000", "#ffffff", "#0b0b0d", "#c9c9c9"


def activity_rows(graph: Graph, cells: np.ndarray) -> tuple[np.ndarray, list, list, int]:
    """Give each of the given neurons a row in a picture, in bands by role.

    Returns the row of every neuron (-1 if it has none), a label for each
    band as (name, number of cells, middle row), the rows where bands meet,
    and the number of rows.
    """
    meta = graph.meta
    kind = meta["type"].fillna("").to_numpy(dtype=str)
    group = meta["superclass"].fillna("").to_numpy(dtype=str)
    side = meta["somaSide"].fillna("").to_numpy(dtype=str)
    row_of = np.full(graph.n, -1, dtype=np.int64)
    unplaced = cells.copy()
    labels, edges, rows = [], [0], 0
    for name, belongs in PICTURE_BANDS:
        members = np.flatnonzero(unplaced & belongs(kind, group))
        unplaced[members] = False
        members = members[np.argsort(side[members], kind="stable")]  # left side below right
        row_of[members] = rows + np.arange(members.size)
        rows += members.size
        labels.append((name, members.size, (edges[-1] + rows) / 2))
        edges.append(rows)
    return row_of, labels, edges, rows


def save_raster(graph: Graph, results: list, record: dict, path: Path) -> None:
    """Draw which neurons fired when, in both trials.

    Only neurons that fired are drawn: a few hundred of the whole graph. The
    two steering neurons get a band of their own at the top, because the
    difference between them is what is read as the choice.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    meta = graph.meta
    kind = meta["type"].fillna("").to_numpy(dtype=str)
    side = meta["somaSide"].fillna("").to_numpy(dtype=str)
    fired = np.zeros(graph.n, dtype=bool)
    for result in results:
        fired[result.spike_neurons] = True
    steering = np.isin(kind, STEERING_TYPES)

    row_of, labels, edges, rows = activity_rows(graph, fired & ~steering)
    rows = max(rows, 1)
    band = max(rows * 0.09, 1.0)  # height of one steering band
    steering_base = {"L": rows + band * 0.5, "R": rows + band * 1.75}
    top = rows + band * 3.0

    options = record["options"]
    toward = record["steering_spikes_toward"]
    figure, axes = plt.subplots(1, 2, figsize=(10, 6.2), dpi=120, sharey=True)
    figure.patch.set_facecolor(PAPER)
    for axis, result, trial in zip(axes, results, record["trials"]):
        axis.set_facecolor(PAPER)
        placed = row_of[result.spike_neurons]
        shown = placed >= 0
        axis.scatter(
            result.spike_times_ms[shown], placed[shown] + 0.5, s=2.2, c=AMBER, linewidths=0, alpha=0.85
        )
        for edge in edges[1:-1]:
            axis.axhline(edge, color="#2a2a2e", linewidth=0.6)
        for which, base in steering_base.items():
            cells_here = np.flatnonzero(steering & (side == which))
            times = result.spike_times_ms[np.isin(result.spike_neurons, cells_here)]
            axis.axhspan(base, base + band, color="#17171b", linewidth=0)
            axis.vlines(times, base, base + band, color=ACCENT, linewidth=0.9)
            axis.text(
                result.duration_ms * 0.985, base + band / 2, f"{times.size} spikes",
                color=ACCENT, fontsize=8, ha="right", va="center",
            )
        axis.set_xlim(0, result.duration_ms)
        axis.set_ylim(0, top)
        axis.set_xlabel("time, ms", color=INK, fontsize=9)
        axis.set_title(
            f'left eye: "{options[trial["left_eye"]]}"   right eye: "{options[trial["right_eye"]]}"',
            color=INK, fontsize=9,
        )
        axis.tick_params(colors="#8a8a8a", labelsize=8, length=0)
        for spine in axis.spines.values():
            spine.set_color("#333333")

    ticks = [(middle, f"{name}\n{count} cells") for name, count, middle in labels if count]
    ticks += [(steering_base["L"] + band / 2, "steering neuron\nleft"),
              (steering_base["R"] + band / 2, "steering neuron\nright")]
    axes[0].set_yticks([position for position, _ in ticks])
    axes[0].set_yticklabels([text for _, text in ticks], color=INK, fontsize=8)

    if record["choice"] == "undecided":
        verdict = f"undecided: {toward['a']} steering spikes each way"
    else:
        other = "b" if record["choice"] == "a" else "a"
        verdict = (
            f'turned towards "{record["choice_label"]}": '
            f"{toward[record['choice']]} steering spikes against {toward[other]}"
        )
    figure.suptitle(
        f"Dro, {record['date']}: {record['question']}", color="#f2f2f2", fontsize=13, x=0.02, ha="left", y=0.975
    )
    figure.text(0.02, 0.915, verdict, color=AMBER, fontsize=10.5, ha="left")
    figure.text(
        0.98, 0.012,
        f"every neuron that fired, of {graph.n:,} simulated; a simulation of a fly's wiring diagram, not a fly",
        color="#8a8a8a", fontsize=7, ha="right",
    )
    figure.subplots_adjust(left=0.135, right=0.985, top=0.845, bottom=0.115, wspace=0.07)
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
        save_raster(graph, results, record, raster)
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
