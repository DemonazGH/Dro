"""Turn an option (a short text or an image file) into input for the brain.

The fly cannot read. Each option becomes a small grayscale picture; text is
drawn dark on a bright page, so to the fly it is a texture of light and dark.

The picture does not enter at the eye. In this model a picture fed into the
first cells of the eye is lost two cells later (``docs/CALIBRATION_NOTES.md``,
experiment 14), so the rig does the early vision itself and hands the result
to the LC10a cells, which respond to visual objects and lead to the steering
neurons:

1. **Where each LC10a cell looks** comes from the wiring. The release gives
   eye coordinates for some cell types of the optic lobe. An LC10a cell's
   view is the set of those cells that feed it, directly or through one
   cell in between, weighted by synapse count.
2. **What it reports** is a rule of the rig: the local contrast of the
   picture within that view. A uniform patch, bright or dark, gives no
   input; a patch that is half dark and half bright gives the maximum.

Step 1 is the fly's. Step 2 is not, and every run log says so.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import sparse

from .graph import Graph

CANVAS = 96  # side of the square picture an option is drawn on, in pixels
PATCH = 3  # one eye column sees a patch of this many pixels across
INPUT_TYPE = "LC10a"  # cell type that receives the picture
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
# An in-between cell is placed on the eye only if at least this many of its
# input synapses come from cells with eye coordinates.
MIN_LOCATING_SYNAPSES = 5
# Brightness is in [0, 1], so its standard deviation is at most 0.5.
MAX_CONTRAST = 0.5
RULE = (
    "rate = max rate x local contrast, where local contrast is the standard "
    "deviation of picture brightness over the eye columns that feed the cell, "
    "weighted by synapse count and divided by 0.5"
)


def render(option: str, base_dir: Path = Path(".")) -> np.ndarray:
    """Return a ``CANVAS x CANVAS`` array in [0, 1] for a text or image option."""
    path = base_dir / option
    if Path(option).suffix.lower() in IMAGE_SUFFIXES and path.is_file():
        image = Image.open(path).convert("L").resize((CANVAS, CANVAS), Image.BOX)
        return np.asarray(image, dtype=np.float32) / 255.0

    image = Image.new("L", (CANVAS, CANVAS), 255)
    draw = ImageDraw.Draw(image)
    words = option.split() or [option]
    # Largest font at which the wrapped text still fits the canvas.
    for size in range(40, 7, -2):
        font = ImageFont.load_default(size=size)
        lines, line = [], ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=font) <= CANVAS - 4 or not line:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
        text = "\n".join(lines)
        left, top, right, bottom = draw.multiline_textbbox((0, 0), text, font=font)
        if right - left <= CANVAS - 4 and bottom - top <= CANVAS - 4:
            break
    position = ((CANVAS - (right - left)) / 2 - left, (CANVAS - (bottom - top)) / 2 - top)
    draw.multiline_text(position, text, fill=0, font=font, align="center")
    return np.asarray(image, dtype=np.float32) / 255.0


@dataclass
class View:
    """Where the input cells of one side look."""

    cells: np.ndarray  # neuron index of every input cell
    rows: np.ndarray  # picture row of every eye column cell
    cols: np.ndarray  # picture column of every eye column cell
    weights: sparse.csc_matrix  # eye column cells x input cells; each column sums to 1


def views(graph: Graph) -> dict[str, View]:
    """The view of every LC10a cell, for the left and the right side.

    Eye coordinates are used only from cell types that have them on both
    sides, so that both eyes are treated alike. The two hex axes are turned
    into picture coordinates as (hex1 - hex2) and (hex1 + hex2); which way is
    up on the real eye is not verified here.
    """
    meta = graph.meta
    index = np.arange(graph.n)
    kind = meta["type"].fillna("").to_numpy()
    side_of = meta["somaSide"].fillna("").to_numpy()
    located = (meta["hex1"].notna() & meta["hex2"].notna()).to_numpy()
    on_both_sides = set(kind[located & (side_of == "L")]) & set(kind[located & (side_of == "R")])
    located = located & np.isin(kind, sorted(on_both_sides))
    optic_lobe = (meta["superclass"] == "ol_intrinsic").to_numpy(dtype=bool, na_value=False)

    x = (meta["hex1"] - meta["hex2"]).to_numpy()
    y = (meta["hex1"] + meta["hex2"]).to_numpy()
    unit_x, unit_y = x, y
    if located.any():
        unit_x = (x - x[located].min()) / max(x[located].max() - x[located].min(), 1)
        unit_y = (y - y[located].min()) / max(y[located].max() - y[located].min(), 1)
    small = CANVAS // PATCH

    all_synapses = abs(graph.weights).tocsc()
    excitatory = graph.weights.maximum(0).tocsc()
    out = {}
    for side in ("L", "R"):
        columns = index[located & (side_of == side)]
        between = index[optic_lobe & (side_of == side) & ~located]
        cells = index[(kind == INPUT_TYPE) & (side_of == side)]

        # Place every in-between cell on the eye by the columns that feed it.
        placing = all_synapses[:, between][columns]
        total = np.asarray(placing.sum(axis=0)).ravel()
        share = np.where(total >= MIN_LOCATING_SYNAPSES, 1.0 / np.maximum(total, 1), 0.0)
        placing = placing @ sparse.diags(share)

        # An input cell's view: its excitatory input from columns, directly
        # and through the in-between cells.
        weights = excitatory[:, cells][columns] + placing @ excitatory[:, cells][between]
        total = np.asarray(weights.sum(axis=0)).ravel()
        weights = (weights @ sparse.diags(1.0 / np.maximum(total, 1e-9))).tocsc()
        out[side] = View(
            cells=cells,
            rows=np.clip((unit_y[columns] * (small - 1)).round().astype(int), 0, small - 1),
            cols=np.clip((unit_x[columns] * (small - 1)).round().astype(int), 0, small - 1),
            weights=weights,
        )
    return out


def local_contrast(picture: np.ndarray, view: View) -> np.ndarray:
    """Contrast of the picture within each input cell's view, in [0, 1]."""
    # Average small neighbourhoods so one eye column sees a patch, not a pixel.
    small = CANVAS // PATCH
    patches = np.asarray(
        Image.fromarray((picture * 255).astype(np.uint8)).resize((small, small), Image.BOX)
    ).astype(np.float64) / 255.0
    seen = patches[view.rows, view.cols]
    mean = view.weights.T @ seen
    variance = np.maximum(view.weights.T @ seen**2 - mean**2, 0.0)
    return np.clip(np.sqrt(variance) / MAX_CONTRAST, 0.0, 1.0)


def input_rates(
    graph: Graph,
    left_picture: np.ndarray,
    right_picture: np.ndarray,
    max_rate_hz: float,
    eye: dict[str, View] | None = None,
) -> np.ndarray:
    """External input rate for every neuron when each eye sees one picture."""
    eye = eye or views(graph)
    rates = np.zeros(graph.n, dtype=np.float64)
    for side, picture in (("L", left_picture), ("R", right_picture)):
        rates[eye[side].cells] = local_contrast(picture, eye[side]) * max_rate_hz
    return rates
