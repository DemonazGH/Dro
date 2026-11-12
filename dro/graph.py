"""Build and load the compiled MaleCNS v1.0 graph.

The build step downloads three public tables from the Janelia FlyEM release,
keeps the traced neurons, signs every connection by the presynaptic neuron's
predicted neurotransmitter and stores the result as one compact ``.npz`` file.

Run it with::

    python -m dro.graph --out data/compiled
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc
from scipy import sparse

RELEASE = "male-cns-v1.0"
BASE_URL = (
    "https://storage.googleapis.com/flyem-male-cns/v1.0/"
    "connectome-data/flat-connectome/"
)
TABLES = {
    "annotations": "body-annotations-male-cns-v1.0-minconf-0.5.feather",
    "neurotransmitters": "body-neurotransmitters-male-cns-v1.0.feather",
    "weights": "connectome-weights-male-cns-v1.0-minconf-0.5.feather",
}

# Sign of a connection, by the presynaptic neuron's consensus transmitter.
# Acetylcholine excites; GABA, glutamate and histamine inhibit. Dopamine,
# serotonin and octopamine act as slow modulators and are not modelled, so
# their connections are dropped. "unclear" is treated as excitatory.
NT_SIGN = {
    "acetylcholine": 1,
    "gaba": -1,
    "glutamate": -1,
    "histamine": -1,
    "dopamine": 0,
    "serotonin": 0,
    "octopamine": 0,
    "unclear": 1,
}

# Connections with fewer synapses than this are treated as noise and dropped.
MIN_SYNAPSES = 3

META_COLUMNS = ["bodyId", "type", "instance", "somaSide", "superclass", "class", "hex1", "hex2"]


@dataclass
class Graph:
    """Signed connectome in CSR form: row = presynaptic, column = postsynaptic."""

    weights: sparse.csr_matrix  # signed synapse counts, float32
    meta: pd.DataFrame  # one row per neuron, same order as the matrix
    info: dict

    @property
    def n(self) -> int:
        return self.weights.shape[0]


def _download(name: str, dest: Path) -> str:
    """Download one release table unless it is already there. Returns sha256."""
    target = dest / name
    if not target.exists():
        print(f"downloading {name}", flush=True)
        partial = target.with_suffix(".part")
        with urllib.request.urlopen(BASE_URL + name) as response, open(partial, "wb") as out:
            while chunk := response.read(1 << 22):
                out.write(chunk)
        partial.rename(target)
    digest = hashlib.sha256()
    with open(target, "rb") as handle:
        while chunk := handle.read(1 << 22):
            digest.update(chunk)
    return digest.hexdigest()


def build(raw_dir: Path, out_dir: Path, min_synapses: int = MIN_SYNAPSES) -> Path:
    """Download the release tables and write ``graph.npz`` + ``neurons.csv``."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    hashes = {key: _download(name, raw_dir) for key, name in TABLES.items()}

    annotations = pd.read_feather(raw_dir / TABLES["annotations"])
    neurons = annotations[annotations["status"] == "Traced"].rename(
        columns={"assignedOlHex1": "hex1", "assignedOlHex2": "hex2"}
    )
    neurons = neurons[META_COLUMNS].sort_values("bodyId").reset_index(drop=True)
    body_ids = neurons["bodyId"].to_numpy()

    transmitters = pd.read_feather(
        raw_dir / TABLES["neurotransmitters"], columns=["body", "consensus_nt"]
    ).drop_duplicates("body")
    consensus = (
        neurons[["bodyId"]]
        .merge(transmitters, left_on="bodyId", right_on="body", how="left")["consensus_nt"]
        .fillna("unclear")
    )
    neurons["nt"] = consensus.to_numpy()
    sign = consensus.map(NT_SIGN).fillna(1).to_numpy(dtype=np.int8)

    # The weights table has ~150 million rows, so it is streamed batch by batch.
    reader = ipc.open_file(pa.memory_map(str(raw_dir / TABLES["weights"])))
    rows, cols, vals = [], [], []
    for index in range(reader.num_record_batches):
        batch = reader.get_batch(index)
        weight = batch.column("weight").to_numpy()
        keep = weight >= min_synapses
        if not keep.any():
            continue
        pre = batch.column("body_pre").to_numpy()[keep]
        post = batch.column("body_post").to_numpy()[keep]
        weight = weight[keep]
        pre_pos = np.searchsorted(body_ids, pre).clip(max=len(body_ids) - 1)
        post_pos = np.searchsorted(body_ids, post).clip(max=len(body_ids) - 1)
        known = (body_ids[pre_pos] == pre) & (body_ids[post_pos] == post)
        known &= sign[pre_pos] != 0
        rows.append(pre_pos[known].astype(np.int32))
        cols.append(post_pos[known].astype(np.int32))
        vals.append((weight[known] * sign[pre_pos[known]]).astype(np.float32))

    n = len(body_ids)
    matrix = sparse.csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(n, n),
        dtype=np.float32,
    )
    matrix.sum_duplicates()

    info = {
        "release": RELEASE,
        "neurons": int(n),
        "connections": int(matrix.nnz),
        "min_synapses": int(min_synapses),
        "nt_sign": NT_SIGN,
        "source_sha256": hashes,
    }
    sparse.save_npz(out_dir / "graph.npz", matrix, compressed=True)
    neurons.to_csv(out_dir / "neurons.csv", index=False)
    (out_dir / "info.json").write_text(json.dumps(info, indent=2) + "\n")
    print(
        f"built {n:,} neurons, {matrix.nnz:,} connections "
        f"in {time.time() - started:.0f} s -> {out_dir}",
        flush=True,
    )
    return out_dir


def load(compiled_dir: Path) -> Graph:
    """Load a graph written by :func:`build`."""
    compiled_dir = Path(compiled_dir)
    weights = sparse.load_npz(compiled_dir / "graph.npz").tocsr()
    meta = pd.read_csv(compiled_dir / "neurons.csv", dtype={"bodyId": np.int64})
    info = json.loads((compiled_dir / "info.json").read_text())
    if weights.shape[0] != len(meta):
        raise ValueError("graph.npz and neurons.csv describe different neuron counts")
    return Graph(weights=weights, meta=meta, info=info)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the compiled MaleCNS graph.")
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data/compiled"))
    parser.add_argument("--min-synapses", type=int, default=MIN_SYNAPSES)
    args = parser.parse_args(argv)
    build(args.raw, args.out, args.min_synapses)
    return 0


if __name__ == "__main__":
    sys.exit(main())
