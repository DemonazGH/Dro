"""Tests that run on a tiny hand-made network, without the real connectome."""

import json

import numpy as np
import pandas as pd
from scipy import sparse

from dro.decide import decide, input_by_option, main, make_seed, next_question, save_raster
from dro.draft import NOTES_MARKER, acceptable, build, facts, footer, latest_log, post_text
from dro.draft import main as draft_main
from dro.gate import MARKER, changed_lines, comment, current_head, fetch_patches, look, post_comment, spike_strip
from dro.gate import main as gate_main
from dro.gate import make_seed as gate_seed
from dro.graph import Graph
from dro.paths import cells, drive, path_strength
from dro.publish import main as publish_main
from dro.publish import multipart, send_telegram
from dro.repeat import add_to_queue, note, repeats, summary
from dro.repeat import run as repeat_run
from dro.sanity import sugar_neurons, verdict
from dro.sim import simulate
from dro.stimulus import CANVAS, local_contrast, render, render_lines, views


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
    assert record["choice_by_input_alone"] in {"a", "b", "tie"}
    assert set(record["input_rate_hz"]) == {"a", "b"}


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


def test_input_by_option_follows_the_swap_of_sides():
    trials = [
        {"left_eye": "a", "right_eye": "b", "input_rate_hz_left": 40.0, "input_rate_hz_right": 30.0},
        {"left_eye": "b", "right_eye": "a", "input_rate_hz_left": 32.0, "input_rate_hz_right": 44.0},
    ]
    assert input_by_option(trials) == ({"a": 42.0, "b": 31.0}, "a")
    trials[1]["input_rate_hz_right"] = 22.0
    assert input_by_option(trials) == ({"a": 31.0, "b": 31.0}, "tie")


def run_log(choice="a", toward=(33, 0), rates=(41.8, 34.2), note="measured: 20 of 20"):
    """A run log with only the fields a draft needs."""
    log = {
        "date": "2026-11-12",
        "question": "Tabs or spaces?",
        "options": {"a": "tabs", "b": "spaces"},
        "choice": choice,
        "steering_spikes_toward": {"a": toward[0], "b": toward[1]},
        "seed": 7,
        "trials": [
            {"left_eye": "a", "right_eye": "b",
             "input_rate_hz_left": rates[0], "input_rate_hz_right": rates[1]},
            {"left_eye": "b", "right_eye": "a",
             "input_rate_hz_left": rates[1], "input_rate_hz_right": rates[0]},
        ],
    }
    if note:
        log["repeatability"] = note
    return log


def test_draft_states_the_decision_and_keeps_the_footer():
    draft = build(run_log(), "2026-11-12.json")
    post, rest = draft.split("\n\nDecided by the fly:", 1)
    assert "tabs" in post and "33" in post
    assert 'Decided by the fly: "tabs", 33 steering spikes against 0.' in draft
    assert "today it did." in draft
    assert "Worded from a template, edited by the human." in draft
    assert "It is not alive" in draft
    assert NOTES_MARKER in rest
    assert "Choice by input alone: a; choice of the pipeline: a" in draft


def test_footer_says_when_the_fly_went_against_the_contrast():
    known = facts(run_log(choice="b", toward=(3, 9)))
    text = footer(known, worded_by_model=False)
    assert 'Decided by the fly: "spaces", 9 steering spikes against 3.' in text
    assert 'today that was "tabs", and the fly went the other way.' in text


def test_footer_warns_about_unmeasured_pairs_and_ties():
    known = facts(run_log(choice="undecided", toward=(4, 4), rates=(30.0, 30.0), note=None))
    text = footer(known, worded_by_model=True)
    assert "Decided by the fly: nothing." in text
    assert "has not been measured for repeatability" in text
    assert "the two had the same contrast" in text
    assert "Worded by a language model, edited by the human." in text
    assert "fewer than five" not in build(run_log(toward=(33, 0)), "x.json")
    assert "fewer than five" in build(run_log(toward=(3, 1)), "x.json")


def test_language_model_gets_only_the_decision_and_never_writes_the_footer():
    class Block:
        type = "text"
        text = "  A post about tabs.  "

    class Response:
        stop_reason = "end_turn"
        content = [Block()]

    class Messages:
        def create(self, **request):
            self.request = request
            return Response()

    class Client:
        def __init__(self):
            self.beta = type("Beta", (), {"messages": Messages()})()

    client = Client()
    draft = build(run_log(), "2026-11-12.json", use_model=True, client=client)
    assert draft.startswith("A post about tabs.\n\nDecided by the fly:")
    assert "Worded by a language model" in draft
    sent = json.loads(client.beta.messages.request["messages"][0]["content"])
    assert sent == {"question": "Tabs or spaces?", "decided": True, "winner": "tabs",
                    "loser": "spaces", "won": 33, "lost": 0}


def test_draft_cli_picks_the_newest_log(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    for name in ("2026-11-11.json", "2026-11-12.json", "2026-11-12-2.json", "notes.json"):
        (runs / name).write_text(json.dumps(run_log()))
    assert latest_log(runs).name == "2026-11-12-2.json"
    assert draft_main(["--runs", str(runs), "--out", str(tmp_path / "drafts")]) == 0
    assert (tmp_path / "drafts" / "2026-11-12-2.md").read_text().count("Decided by the fly:") == 1


def test_next_question_takes_unasked_first_then_the_oldest(tmp_path):
    queue = [{"question": "q1", "a": "tabs", "b": "spaces"},
             {"question": "q2", "a": "yes", "b": "no"},
             {"question": "q3", "a": "cat", "b": "dog"}]
    assert next_question(queue, tmp_path)["question"] == "q1"
    (tmp_path / "2026-11-12.json").write_text(json.dumps({"options": {"a": "ship", "b": "wait"}}))
    (tmp_path / "2026-11-12-2.json").write_text(json.dumps({"options": {"a": "tabs", "b": "spaces"}}))
    assert next_question(queue, tmp_path)["question"] == "q2"
    (tmp_path / "2026-11-13.json").write_text(json.dumps({"options": {"a": "no", "b": "yes"}}))
    (tmp_path / "2026-11-14.json").write_text(json.dumps({"options": {"a": "cat", "b": "dog"}}))
    assert next_question(queue, tmp_path)["question"] == "q1"  # all asked: the oldest comes round again


def test_cli_asks_the_next_question_of_the_queue(tmp_path):
    graph = eye_graph()
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    sparse.save_npz(compiled / "graph.npz", graph.weights)
    graph.meta.to_csv(compiled / "neurons.csv", index=False)
    (compiled / "info.json").write_text(json.dumps(graph.info))
    queue = tmp_path / "questions.json"
    queue.write_text(json.dumps([{"question": "q1", "a": "yes", "b": "no", "repeatability": "r1"},
                                 {"question": "q2", "a": "cat", "b": "dog"}]))
    arguments = ["--queue", str(queue), "--graph", str(compiled), "--runs", str(tmp_path / "runs")]
    arguments += ["--date", "2026-01-01", "--duration-ms", "100", "--no-raster"]
    assert main(arguments) == 0 and main(arguments) == 0
    first = json.loads((tmp_path / "runs" / "2026-01-01.json").read_text())
    second = json.loads((tmp_path / "runs" / "2026-01-01-2.json").read_text())
    assert (first["question"], first["repeatability"]) == ("q1", "r1")
    assert second["question"] == "q2" and "repeatability" not in second


def test_unattended_draft_says_nobody_edited_it():
    draft = build(run_log(), "2026-11-12.json", unattended=True)
    assert "Worded from a template. Automatic post, no human edited it." in draft
    assert "edited by the human" not in draft
    published = post_text(draft)
    assert NOTES_MARKER not in published and "Seed" not in published
    assert published.endswith("It is not alive and it cannot read.")


def test_posts_from_the_language_model_are_filtered():
    assert acceptable("Leadership is a window. I walked into it.")
    assert not acceptable("As a conscious being, I chose tabs.")
    assert not acceptable("You should invest in bananas.")
    assert not acceptable("word " * 200)


def test_repeat_note_and_queue(tmp_path):
    rows = [{"choice": "a", "toward_a": 30, "toward_b": 2, "input_a": 41.8, "input_b": 34.2,
             "by_input": "a"}] * 18
    rows += [{"choice": "b", "toward_a": 1, "toward_b": 3, "input_a": 41.8, "input_b": 34.2,
              "by_input": "a"}] * 2
    assert repeats(summary(rows))
    assert not repeats(summary(rows[:2] + rows[-2:]))
    text = note("tabs", "spaces", rows, "2026-11-12")
    assert "tabs won 18 of 20 runs" in text
    assert "tabs is also the picture with more contrast (41.8 Hz of input against 34.2 Hz)" in text
    queue = tmp_path / "questions.json"
    assert add_to_queue(queue, "Tabs or spaces?", "tabs", "spaces", text)
    assert not add_to_queue(queue, "Spaces or tabs?", "spaces", "tabs", text)
    assert json.loads(queue.read_text()) == [
        {"question": "Tabs or spaces?", "a": "tabs", "b": "spaces", "repeatability": text}
    ]


class FakeTelegram:
    """Stands in for urllib.request.urlopen and records what was sent."""

    def __init__(self, answer=None):
        self.requests = []
        self.answer = answer or {"ok": True}

    def __call__(self, request, timeout):
        self.requests.append(request)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False

    def read(self):
        return json.dumps(self.answer).encode()


def test_telegram_sends_the_picture_with_the_post_as_caption(tmp_path):
    photo = tmp_path / "2026-11-13.png"
    photo.write_bytes(b"png bytes")
    fake = FakeTelegram()
    assert send_telegram("the post", photo, "TOKEN", "@flycorp", opener=fake) == ["sendPhoto"]
    request = fake.requests[0]
    assert request.full_url == "https://api.telegram.org/botTOKEN/sendPhoto"
    assert b'name="caption"\r\n\r\nthe post' in request.data
    assert b"png bytes" in request.data
    assert request.get_header("Content-type").startswith("multipart/form-data; boundary=")


def test_telegram_sends_long_posts_as_a_separate_message(tmp_path):
    photo = tmp_path / "2026-11-13.png"
    photo.write_bytes(b"png bytes")
    fake = FakeTelegram()
    long_post = "word " * 300
    assert send_telegram(long_post, photo, "TOKEN", "1", opener=fake) == ["sendPhoto", "sendMessage"]
    assert b"caption" not in fake.requests[0].data
    assert json.loads(fake.requests[1].data) == {"chat_id": "1", "text": long_post}
    assert send_telegram("short", None, "TOKEN", "1", opener=FakeTelegram()) == ["sendMessage"]


def test_telegram_failure_does_not_leak_the_token():
    try:
        send_telegram("x", None, "SECRET", "1", opener=FakeTelegram({"ok": False, "description": "chat not found"}))
    except RuntimeError as error:
        assert "chat not found" in str(error) and "SECRET" not in str(error)
    else:
        raise AssertionError("a refused message must raise")
    body, content_type = multipart({"chat_id": "1"}, "photo", "a.png", b"x")
    assert body.endswith(b"--\r\n") and "boundary=" in content_type


def test_publish_picks_the_newest_post_and_stays_quiet_without_credentials(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    for name in ("2026-11-12.md", "2026-11-12-4.md", "2026-11-12-3.md"):
        (tmp_path / name).write_text(build(run_log(), name, unattended=True))
    assert publish_main(["--runs", str(tmp_path)]) == 0
    printed = capsys.readouterr().out
    assert "2026-11-12-4.md" in printed and "not switched on" in printed
    assert publish_main(["--runs", str(tmp_path / "empty")]) == 1


def test_activity_picture_is_written_for_decided_and_undecided_runs(tmp_path):
    graph = eye_graph()
    record, results = decide(graph, "q", "yes", "no", seed=3, duration_ms=200.0)
    record = {"date": "2026-01-01", **record}
    save_raster(graph, results, record, tmp_path / "decided.png")
    record.update(choice="undecided", choice_label=None, steering_spikes_toward={"a": 4, "b": 4})
    save_raster(graph, results, record, tmp_path / "undecided.png")
    for name in ("decided.png", "undecided.png"):
        assert (tmp_path / name).stat().st_size > 10_000


PATCH = """@@ -1,4 +1,5 @@
 def area(width, height):
-    return width + height
+    # The area of a rectangle.
+    return width * height
 
+
"""


def test_changed_lines_splits_a_patch_and_skips_headers_and_blank_lines():
    added, removed = changed_lines([PATCH, "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new\n"])
    assert added == ["    # The area of a rectangle.", "    return width * height", "new"]
    assert removed == ["    return width + height", "old"]


def test_changed_lines_keeps_code_that_starts_with_plus_plus_or_minus_minus():
    patch = "@@ -1,2 +1,2 @@\n---counter;\n+++counter;\n context\n"
    assert changed_lines([patch]) == (["++counter;"], ["--counter;"])
    two_files = (
        "diff --git a/a.c b/a.c\n--- a/a.c\n+++ b/a.c\n@@ -1 +1 @@\n-x\n+y\n"
        "\\ No newline at end of file\n"
        "diff --git a/b.c b/b.c\n--- a/b.c\n+++ b/b.c\n@@ -0,0 +1 @@\n+z\n"
    )
    assert changed_lines([two_files]) == (["y", "z"], ["x"])


def test_gate_seed_is_fixed_by_the_commit():
    assert gate_seed("o/r", 7, "abc") == gate_seed("o/r", 7, "abc")
    assert gate_seed("o/r", 7, "abc") != gate_seed("o/r", 7, "abd")
    assert gate_seed("o/r", 7, "abc") != gate_seed("o/r", 8, "abc")


def test_code_is_drawn_from_the_top_left_and_cut_off():
    page = render_lines(["x = 1"] * 40)
    assert page.shape == (CANVAS, CANVAS) and page.min() < 0.5
    assert page[:, CANVAS // 2 :].min() == 1.0  # short lines leave the right half empty
    assert render_lines([]).min() == 1.0


def test_spike_strip_marks_when_the_neuron_fired():
    strip = spike_strip(np.array([0.0, 500.0, 999.0]), 1000.0, width=10)
    assert strip == "|····|···|"


def test_gate_comment_says_what_it_is_and_what_it_is_not():
    graph = eye_graph()
    record, results = look(graph, ["return width * height"] * 6, [], seed=3, title="q")
    assert record["choice"] == "a"  # only the new lines were there to turn to
    text = comment(graph, record, results, "https://example.org/run")
    assert text.startswith(MARKER + "\n### Fly Gate: LGTM. I did not read it.")
    assert "A code review. The fly cannot read" in text
    assert "not a fly and not alive" in text
    assert "left eye: the new lines, right eye: the old lines" in text
    assert "[activity picture](https://example.org/run)" in text
    assert "adds (6 in all)" in text and "removes (0 in all)" in text


class FakeGitHub:
    """Stands in for urllib.request.urlopen and answers by address."""

    def __init__(self, answers):
        self.answers, self.requests = answers, []

    def __call__(self, request, timeout):
        self.requests.append(request)
        self.current = next(body for part, body in self.answers if part in request.full_url)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False

    def read(self):
        return json.dumps(self.current).encode()


def test_gate_comment_is_created_once_and_updated_afterwards():
    fresh = FakeGitHub([("/issues/7/comments", [{"id": 1, "body": "someone else"}])])
    assert post_comment("https://api", "o/r", 7, "T", MARKER + " new", opener=fresh) == "created"
    assert fresh.requests[-1].get_method() == "POST"
    again = FakeGitHub([("/issues/comments/5", {}), ("/issues/7/comments", [{"id": 5, "body": MARKER + " old"}])])
    assert post_comment("https://api", "o/r", 7, "T", MARKER + " new", opener=again) == "updated"
    assert again.requests[-1].get_method() == "PATCH"
    assert again.requests[-1].full_url.endswith("/issues/comments/5")
    assert again.requests[-1].get_header("Authorization") == "Bearer T"


def test_gate_finds_its_comment_on_a_later_page():
    crowd = [{"id": i, "body": "chatter"} for i in range(100)]
    github = FakeGitHub([("/issues/comments/777", {}),
                         ("&page=2", [{"id": 777, "body": MARKER + " old"}]),
                         ("&page=1", crowd)])
    assert post_comment("https://api", "o/r", 7, "T", MARKER + " new", opener=github) == "updated"
    assert [request.get_method() for request in github.requests] == ["GET", "GET", "PATCH"]


def test_gate_asks_for_the_current_head_of_the_pull_request():
    github = FakeGitHub([("/pulls/7", {"head": {"sha": "abc"}})])
    assert current_head("https://api", "o/r", 7, "T", opener=github) == "abc"


def test_gate_reads_all_pages_of_changed_files():
    first = [{"filename": f"f{i}", "patch": "+x"} for i in range(99)] + [{"filename": "binary"}]
    github = FakeGitHub([("&page=2", [{"filename": "last", "patch": "-y"}]), ("&page=1", first)])
    patches = fetch_patches("https://api", "o/r", 7, "T", opener=github)
    assert len(patches) == 100 and patches[-1] == "-y"


def test_gate_cli_on_a_patch_file(tmp_path, monkeypatch, capsys):
    for name in ("GITHUB_TOKEN", "GITHUB_STEP_SUMMARY", "GITHUB_EVENT_PATH"):
        monkeypatch.delenv(name, raising=False)
    graph = eye_graph()
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    sparse.save_npz(compiled / "graph.npz", graph.weights)
    graph.meta.to_csv(compiled / "neurons.csv", index=False)
    (compiled / "info.json").write_text(json.dumps(graph.info))
    removal = tmp_path / "removal.patch"
    removal.write_text("@@ -1,3 +0,0 @@\n-return width + height\n-return width + height\n-return 1\n")
    arguments = ["--graph", str(compiled), "--patch", str(removal), "--out", str(tmp_path / "out")]
    assert gate_main(arguments) == 0
    assert "Changes requested. I did not read it." in capsys.readouterr().out
    assert (tmp_path / "out" / "fly-gate.png").exists()
    assert json.loads((tmp_path / "out" / "fly-gate.json").read_text())["choice"] == "b"
    assert gate_main(arguments + ["--enforce"]) == 1
    empty = tmp_path / "empty.patch"
    empty.write_text("@@ -1 +1 @@\n context only\n")
    assert gate_main(["--graph", str(compiled), "--patch", str(empty), "--enforce"]) == 0
    assert "nothing to look at" in capsys.readouterr().out
