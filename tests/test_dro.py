"""Tests that run on a tiny hand-made network, without the real connectome."""

import json

import numpy as np
import pandas as pd
from scipy import sparse

from dro.decide import decide, main, make_seed
from dro.graph import Graph
from dro.paths import cells, drive, path_strength
from dro.repeat import run as repeat_run
from dro.repeat import summary
from dro.sanity import sugar_neurons, verdict
from dro.sim import simulate
from dro.stimulus import CANVAS, local_contrast, render, views


def chain(weight: float) -> sparse.csr_matrix:
    """Neuron 0 -> neuron 1, with the given signed synapse count."""
    return sparse.csr_matrix(([weight], ([0], [1])), shape=(2, 2), dtype=np.float32)


def test_excitation_spreads_and_inhibition_does_not():
    rates = np.array([200.0, 0.0])
    excited = simulate(chain(200.0), rates, 300.0, seed=1)
    inhibited = simulate(chain(-200.0), rates, 300.0, seed=1)
    assert excited.spike_counts[0] > 0
    assert excited.spike_counts[1] > 0
    assert inhibited.spike_counts[1] == 0


def test_silent_without_input():
    result = simulate(chain(200.0), np.zeros(2), 100.0, seed=1)
    assert result.spike_counts.sum() == 0


def test_same_seed_same_spikes():
    rates = np.array([150.0, 0.0])
    first = simulate(chain(50.0), rates, 200.0, seed=7)
    second = simulate(chain(50.0), rates, 200.0, seed=7)
    assert np.array_equal(first.spike_neurons, second.spike_neurons)
    assert np.array_equal(first.spike_times_ms, second.spike_times_ms)


def test_input_neuron_fires_once_per_input_spike():
    """Input goes straight to the voltage and input neurons are never refractory."""
    alone = sparse.csr_matrix((1, 1), dtype=np.float32)
    result = simulate(alone, np.array([600.0]), 1000.0, seed=1)
    # Well above the 455 Hz ceiling a 2.2 ms refractory period would impose.
    assert 480 < result.spike_counts[0] <= 650


def test_a_spike_clears_the_synaptic_drive():
    """One very strong input spike makes the target fire once, not in a burst."""
    rates = np.array([5.0, 0.0])
    result = simulate(chain(2000.0), rates, 2000.0, seed=1)
    sent, received = result.spike_counts
    assert sent > 0
    assert sent - 1 <= received <= sent


def test_sanity_verdict():
    good = [
        {"rate_hz": 50.0, "seed": 1, "mn9_hz": 0.0, "active": 90, "spikes": 3000},
        {"rate_hz": 200.0, "seed": 1, "mn9_hz": 60.0, "active": 250, "spikes": 14000},
    ]
    assert verdict(good, max_active=1000) == (True, [])
    runaway = [dict(good[0]), {**good[1], "active": 6000}]
    assert not verdict(runaway, max_active=1000)[0]
    falling = [{**good[0], "mn9_hz": 80.0}, dict(good[1])]
    assert not verdict(falling, max_active=1000)[0]
    silent = [dict(good[0]), {**good[1], "mn9_hz": 0.0}]
    assert not verdict(silent, max_active=1000)[0]


def test_sugar_neurons_are_picked_by_type_and_side():
    meta = pd.DataFrame(
        {
            "type": ["LB3a", "LB3d", "LB1c", "MN9", None],
            "instance": ["LB3a_R", "LB3d_L", "LB1c_R", "MN9_R", None],
        }
    )
    graph = Graph(weights=sparse.csr_matrix((5, 5), dtype=np.float32), meta=meta, info={})
    assert sugar_neurons(graph, "R").tolist() == [0]
    assert sugar_neurons(graph, "L").tolist() == [1]


def test_seed_depends_on_date_and_question():
    assert make_seed("2026-11-12", "q", "a", "b") == make_seed("2026-11-12", "q", "a", "b")
    assert make_seed("2026-11-12", "q", "a", "b") != make_seed("2026-11-13", "q", "a", "b")


def test_render_text_is_dark_on_bright():
    picture = render("yes")
    assert picture.shape == (CANVAS, CANVAS)
    assert 0.5 < picture.mean() < 1.0
    assert picture.min() < 0.5


def eye_graph() -> Graph:
    """Per side: a 6 x 6 patch of eye columns -> one LC10a cell -> DNa02."""
    rows = []
    for side in ("L", "R"):
        for hex1 in range(6):
            for hex2 in range(6):
                rows.append(("Tm1", side, "ol_intrinsic", float(hex1), float(hex2)))
        rows.append(("LC10a", side, "visual_projection", np.nan, np.nan))
        rows.append(("DNa02", side, "descending_neuron", np.nan, np.nan))
    meta = pd.DataFrame(rows, columns=["type", "somaSide", "superclass", "hex1", "hex2"])
    meta["bodyId"] = np.arange(len(meta)) + 1
    pre, post, synapses = [], [], []
    for start in (0, 38):
        pre += list(range(start, start + 36)) + [start + 36]
        post += [start + 36] * 36 + [start + 37]
        synapses += [10.0] * 36 + [400.0]
    weights = sparse.csr_matrix((synapses, (pre, post)), shape=(76, 76), dtype=np.float32)
    return Graph(weights=weights, meta=meta, info={"release": "toy"})


def test_view_comes_from_the_wiring():
    eye = views(eye_graph())
    assert eye["L"].cells.tolist() == [36] and eye["R"].cells.tolist() == [74]
    assert eye["L"].weights.shape == (36, 1)
    assert np.isclose(eye["L"].weights.sum(), 1.0)


def test_local_contrast_ignores_uniform_pictures():
    eye = views(eye_graph())["L"]
    bright = np.ones((CANVAS, CANVAS), dtype=np.float32)
    dark = np.zeros((CANVAS, CANVAS), dtype=np.float32)
    split = bright.copy()
    split[:, : CANVAS // 2] = 0.0
    assert local_contrast(bright, eye)[0] == 0.0
    assert local_contrast(dark, eye)[0] == 0.0
    assert local_contrast(split, eye)[0] > 0.9


def test_decide_on_toy_graph():
    """A picture with contrast reaches the steering neuron of its own side."""
    record, results = decide(eye_graph(), "q", "yes", "no", seed=3, duration_ms=200.0)
    assert record["choice"] in {"a", "b", "undecided"}
    assert len(record["trials"]) == 2 and len(results) == 2
    assert sum(record["steering_spikes_toward"].values()) > 0
    assert record["steering_types"] == ["DNa02"]
    assert record["trials"][0]["input_rate_hz_left"] > 0


def relay_graph() -> Graph:
    """Eye cell 0 -> relay 1 -> right steering neuron 2. Neuron 3 inhibits the relay."""
    meta = pd.DataFrame(
        {
            "bodyId": [1, 2, 3, 4, 5],
            "type": ["LC10a", "AOTU025", "DNa02", "LT51", "DNa02"],
            "somaSide": ["R", "R", "R", "R", "L"],
            "superclass": ["visual_projection", "cb_intrinsic", "descending_neuron",
                           "visual_projection", "descending_neuron"],
        }
    )
    weights = sparse.csr_matrix(
        ([300.0, 400.0, -100.0], ([0, 1, 3], [1, 2, 1])), shape=(5, 5), dtype=np.float32
    )
    return Graph(weights=weights, meta=meta, info={})


def test_path_strength_multiplies_input_shares():
    graph = relay_graph()
    one_step, two_steps = path_strength(graph, cells(graph, ["DNa02"], "R"), steps=2)
    assert one_step[1] == 1.0  # the relay supplies all of the target's input
    assert one_step[0] == 0.0
    assert two_steps[0] == 0.75  # 300 of the relay's 400 input synapses
    assert two_steps[3] == 0.0  # inhibitory connections are not followed


def test_drive_reaches_the_steering_neuron_on_the_same_side():
    row = drive(relay_graph(), ["LC10a"], "R", rate_hz=200.0, duration_ms=500.0)
    assert row["cells_driven"] == 1
    assert row["DNa02_R"] > 0
    assert row["DNa02_L"] == 0


def test_repeat_counts_winners():
    rows = repeat_run(eye_graph(), "yes", "no", runs=2)
    assert [row["seed"] for row in rows] == [10, 20]
    counted = summary(
        [
            {"choice": "a", "toward_a": 9, "toward_b": 3},
            {"choice": "a", "toward_a": 7, "toward_b": 5},
            {"choice": "b", "toward_a": 2, "toward_b": 4},
            {"choice": "undecided", "toward_a": 2, "toward_b": 2},
        ]
    )
    assert (counted["a"], counted["b"], counted["undecided"]) == (2, 1, 1)
    assert counted["same_winner_share"] == 0.5
    assert counted["mean_toward_a"] == 5.0


def test_cli_writes_a_log_and_passes_on_the_repeatability_note(tmp_path):
    graph = eye_graph()
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    sparse.save_npz(compiled / "graph.npz", graph.weights)
    graph.meta.to_csv(compiled / "neurons.csv", index=False)
    (compiled / "info.json").write_text(json.dumps(graph.info))
    question = tmp_path / "question.json"
    question.write_text(
        json.dumps({"question": "q", "a": "yes", "b": "no", "repeatability": "measured: 20 of 20"})
    )
    arguments = ["--question", str(question), "--graph", str(compiled), "--runs", str(tmp_path / "runs")]
    arguments += ["--date", "2026-01-01", "--duration-ms", "100", "--no-raster"]
    assert main(arguments) == 0
    log = json.loads((tmp_path / "runs" / "2026-01-01.json").read_text())
    assert log["repeatability"] == "measured: 20 of 20"
    assert log["options"] == {"a": "yes", "b": "no"}
    assert main(arguments) == 0  # a second run on the same date gets its own file
    assert (tmp_path / "runs" / "2026-01-01-2.json").exists()
