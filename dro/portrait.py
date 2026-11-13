"""Portrait through a fly's eyes: a poster of how the brain reacted to a photo.

Usage::

    python -m dro.portrait photo.jpg --out portrait.png --name "Grace"

The photo is cropped to a square and shown to both eyes of the simulated
brain for one second. The poster shows, from top to bottom:

1. What reached the eyes: the photo as 32 x 32 points of light.
2. What the object-detecting cells (LC10a) reported, one dot per cell at
   the spot where that cell looks, drawn over a faint copy of the photo and
   larger where the picture has more contrast. This step is the rig's
   stand-in for the optic lobe.
3. Every neuron that fired during the second, and the two steering neurons.

The fly sees no face. It gets light and dark, and the poster says so.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from .decide import ACCENT, AMBER, ATTRIBUTION, INK, PAPER, STEERING_TYPES, activity_rows
from .graph import Graph, load
from .sim import simulate
from .stimulus import CANVAS, PATCH, View, local_contrast, views

MAX_RATE_HZ = 150.0
DURATION_MS = 1000.0


def load_square(path: Path) -> np.ndarray:
    """A photo as a square grayscale picture in [0, 1], cropped around its middle."""
    image = Image.open(path).convert("L")
    side = min(image.size)
    left, top = (image.width - side) // 2, (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize((CANVAS, CANVAS), Image.BOX)
    return np.asarray(image, dtype=np.float32) / 255.0


def view_centres(view: View) -> tuple[np.ndarray, np.ndarray]:
    """Where each input cell looks: the middle of its view, as picture row and column."""
    return view.weights.T @ view.rows, view.weights.T @ view.cols


def look(graph: Graph, picture: np.ndarray, seed: int) -> dict:
    """Show one picture to both eyes for a second and collect what the poster needs."""
    eye = views(graph)
    rates = np.zeros(graph.n, dtype=np.float64)
    contrast = {}
    for side in ("L", "R"):
        contrast[side] = local_contrast(picture, eye[side])
        rates[eye[side].cells] = contrast[side] * MAX_RATE_HZ
    result = simulate(graph.weights, rates, DURATION_MS, seed)

    meta = graph.meta
    steering = meta["type"].isin(STEERING_TYPES).to_numpy(dtype=bool, na_value=False)
    side_of = meta["somaSide"].fillna("").to_numpy(dtype=str)
    steering_times = {
        side: result.spike_times_ms[np.isin(result.spike_neurons, np.flatnonzero(steering & (side_of == side)))]
        for side in ("L", "R")
    }
    return {
        "eye": eye,
        "contrast": contrast,
        "result": result,
        "steering": steering,
        "steering_times": steering_times,
        "fired": int((result.spike_counts > 0).sum()),
        "spikes": int(result.spike_counts.sum()),
    }


def save_poster(graph: Graph, picture: np.ndarray, seen: dict, path: Path, name: str | None = None) -> None:
    """Draw the poster."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    small = CANVAS // PATCH
    patches = np.asarray(
        Image.fromarray((picture * 255).astype(np.uint8)).resize((small, small), Image.BOX)
    )
    figure = plt.figure(figsize=(9, 11.25), dpi=120)
    figure.patch.set_facecolor(PAPER)
    grid = figure.add_gridspec(
        2, 3, height_ratios=(1, 1.7), left=0.06, right=0.94, top=0.86, bottom=0.145, hspace=0.13, wspace=0.08
    )

    def frame(axis, title):
        axis.set_facecolor(PAPER)
        axis.set_title(title, color=INK, fontsize=9.5, pad=8)
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_color("#333333")

    eyes = figure.add_subplot(grid[0, 0])
    eyes.imshow(patches, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
    frame(eyes, f"what reached each eye\n{small} x {small} points of light")

    for column, (side, word) in enumerate((("L", "left"), ("R", "right")), start=1):
        axis = figure.add_subplot(grid[0, column])
        rows, cols = view_centres(seen["eye"][side])
        strength = seen["contrast"][side]
        # The picture, faint, under the cells: each dot sits on the spot its cell looks at.
        axis.imshow(patches, cmap="gray", vmin=0, vmax=255, interpolation="nearest", alpha=0.22)
        axis.scatter(cols, rows, s=6 + 150 * strength, c=AMBER, alpha=0.3 + 0.65 * strength, linewidths=0)
        axis.set_xlim(-0.5, small - 0.5)
        axis.set_ylim(small - 0.5, -0.5)
        axis.set_aspect("equal")
        frame(axis, f"where its object cells look, and how\nstrongly they fired: {word} eye, {strength.size} cells")

    result = seen["result"]
    fired = np.zeros(graph.n, dtype=bool)
    fired[result.spike_neurons] = True
    row_of, labels, edges, rows = activity_rows(graph, fired & ~seen["steering"])
    rows = max(rows, 1)
    band = max(rows * 0.07, 1.0)
    base = {"L": rows + band * 0.5, "R": rows + band * 1.75}
    brain = figure.add_subplot(grid[1, :])
    brain.set_facecolor(PAPER)
    label_box = {"facecolor": PAPER, "edgecolor": "none", "alpha": 0.82, "pad": 2.5}
    placed = row_of[result.spike_neurons]
    shown = placed >= 0
    brain.scatter(result.spike_times_ms[shown], placed[shown] + 0.5, s=2.4, c=AMBER, linewidths=0, alpha=0.85)
    for edge in edges[1:-1]:
        brain.axhline(edge, color="#2a2a2e", linewidth=0.6)
    for side, word in (("L", "left"), ("R", "right")):
        times = seen["steering_times"][side]
        brain.axhspan(base[side], base[side] + band, color="#17171b", linewidth=0)
        brain.vlines(times, base[side], base[side] + band, color=ACCENT, linewidth=0.9)
        brain.text(
            DURATION_MS * 0.992, base[side] + band / 2, f"steering neuron, {word}: {times.size} spikes",
            color=ACCENT, fontsize=8, ha="right", va="center", bbox=label_box,
        )
    brain.set_xlim(0, DURATION_MS)
    brain.set_ylim(0, rows + band * 3)
    brain.set_xlabel("one second of looking, in milliseconds", color=INK, fontsize=9)
    for label, count, middle in labels:
        if count:
            brain.text(
                DURATION_MS * 0.008, middle, f"{label}: {count} cells",
                color="#f2f2f2", fontsize=8, ha="left", va="center", bbox=label_box,
            )
    brain.set_yticks([])
    brain.tick_params(colors="#8a8a8a", labelsize=8, length=0)
    for spine in brain.spines.values():
        spine.set_color("#333333")
    brain.set_title("every neuron that fired", color=INK, fontsize=9.5, pad=8)

    heading = f"{name}, through a fly's eyes" if name else "Portrait through a fly's eyes"
    figure.text(0.06, 0.955, heading, color="#f2f2f2", fontsize=20, ha="left", va="center")
    figure.text(
        0.06, 0.915,
        f"{seen['fired']:,} of {graph.n:,} neurons fired, {seen['spikes']:,} spikes in one second",
        color=AMBER, fontsize=11, ha="left", va="center",
    )
    figure.text(
        0.06, 0.066,
        "Dro is a simulation of a fruit fly's wiring diagram. It is not alive and it saw no face: only light and dark.\n"
        "The eyes and the brain are the fly's wiring. Turning the picture into the object cells' firing is done by the rig.",
        color=INK, fontsize=8, ha="left", va="center", linespacing=1.5,
    )
    figure.text(0.06, 0.024, ATTRIBUTION, color="#8a8a8a", fontsize=5.6, ha="left", va="center")
    figure.savefig(path, facecolor=figure.get_facecolor())
    plt.close(figure)


def make(graph: Graph, photo: Path, out: Path, name: str | None = None) -> dict:
    """Photo in, poster out. Returns the numbers shown on the poster."""
    picture = load_square(photo)
    # The seed comes from the photo, so the same photo gives the same poster.
    seed = int.from_bytes(hashlib.sha256(photo.read_bytes()).digest()[:4], "big")
    seen = look(graph, picture, seed)
    save_poster(graph, picture, seen, out, name)
    return {
        "neurons": graph.n,
        "fired": seen["fired"],
        "spikes": seen["spikes"],
        "steering_left": int(seen["steering_times"]["L"].size),
        "steering_right": int(seen["steering_times"]["R"].size),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Make a poster of how the brain reacted to a photo.")
    parser.add_argument("photo", type=Path)
    parser.add_argument("--out", type=Path, default=Path("portrait.png"))
    parser.add_argument("--name", help="a name for the heading")
    parser.add_argument("--graph", type=Path, default=Path("data/compiled"))
    args = parser.parse_args(argv)
    numbers = make(load(args.graph), args.photo, args.out, args.name)
    print(f"{args.out}: {numbers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
