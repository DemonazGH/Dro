"""Build the website from the run logs.

Usage::

    python -m dro.site --out _site

The page shows the newest decision, what the fly did and what the rig did,
how far the answers can be trusted, every earlier decision, Fly Gate and
the portraits. It is one HTML file with one stylesheet and no scripts.

Standard library only: the site is built in a job that installs nothing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import shutil
import struct
import sys
from pathlib import Path

from .logs import log_order, next_question, post_text, run_logs

REPOSITORY = "https://github.com/DemonazGH/Dro"
ADDRESS = "https://demonazgh.github.io/Dro/"
CHANNEL = ""  # address of the Telegram channel; no link is shown while this is empty
NEURONS = 165_122
# Measured in experiments 21 and 22 of docs/CALIBRATION_NOTES.md.
PAIRS_MEASURED, PAIRS_REPEATING, PAIRS_FOLLOWING_CONTRAST = 42, 34, 30
FOOTER_STARTS = "Decided by the fly:"
GATE_EXAMPLE = """name: Fly Gate
on: pull_request
permissions:
  contents: read
  pull-requests: write
jobs:
  fly-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: DemonazGH/Dro@v1"""


def text(value) -> str:
    """Escape anything that goes into the page."""
    return html.escape(str(value), quote=True)


def long_date(day: str) -> str:
    date = dt.date.fromisoformat(day)
    return f"{date.day} {date:%B} {date.year}"


def png_size(path: Path) -> tuple[int, int]:
    """Width and height of a PNG file, read from its header."""
    with open(path, "rb") as handle:
        header = handle.read(24)
    return struct.unpack(">II", header[16:24])


def load(log: Path) -> dict:
    """One decision, with what the page needs from its log and its post."""
    record = json.loads(log.read_text(encoding="utf-8"))
    day, number = log_order(log)
    options, toward, choice = record["options"], record["steering_spikes_toward"], record["choice"]
    decision = {
        "stem": log.stem,
        "date": day,
        "run": number,
        "question": record["question"],
        "a": options["a"],
        "b": options["b"],
        "toward_a": toward["a"],
        "toward_b": toward["b"],
        "choice": choice,
        "winner": options.get(choice),
        "by_input": record.get("choice_by_input_alone"),
        "by_input_label": options.get(record.get("choice_by_input_alone")),
        "picture": None,
        "post": [],
        "footer": [],
    }
    picture = log.with_suffix(".png")
    if picture.exists():
        decision["picture"] = (picture.name, *png_size(picture))
    post = log.with_suffix(".md")
    if post.exists():
        body, _, footer = post_text(post.read_text(encoding="utf-8")).partition(FOOTER_STARTS)
        decision["post"] = [part.strip() for part in body.split("\n\n") if part.strip()]
        decision["footer"] = [line.strip() for line in (FOOTER_STARTS + footer).splitlines() if line.strip()] if footer else []
    return decision


def verdict(decision: dict) -> str:
    if decision["choice"] == "undecided":
        return "undecided"
    return decision["winner"]


def spikes(decision: dict) -> str:
    """The two steering counts as a small chart that also reads as text."""
    most = max(decision["toward_a"], decision["toward_b"], 1)
    rows = []
    for option, count in ((decision["a"], decision["toward_a"]), (decision["b"], decision["toward_b"])):
        rows.append(
            f'<div><dt>{text(option)}</dt><dd><span class="bar" style="--share: {count / most:.3f}" '
            f'aria-hidden="true"></span>{count} spikes</dd></div>'
        )
    return '<dl class="spikes">' + "".join(rows) + "</dl>"


def contrast_note(decision: dict) -> str:
    """Whether the fly went with the rig's contrast number."""
    by_input = decision["by_input"]
    if by_input is None:
        return ""
    if by_input == "tie":
        return "The two pictures had the same contrast, so the rig had no favourite."
    favourite = f"“{text(decision['by_input_label'])}”"
    if decision["choice"] == "undecided":
        return f"The picture with more contrast was {favourite}; the fly did not follow."
    if by_input == decision["choice"]:
        return f"The picture with more contrast was {favourite} as well, so the fly agreed with the rig."
    return f"The picture with more contrast was {favourite}; the fly went the other way."


def picture(decision: dict, first: bool) -> str:
    if not decision["picture"]:
        return ""
    name, width, height = decision["picture"]
    # The first picture is the largest thing on the page; the others wait until they are scrolled to.
    priority = 'fetchpriority="high"' if first else 'loading="lazy"'
    alt = (
        f"Spikes of every neuron that fired while the fly was shown “{decision['a']}” and "
        f"“{decision['b']}”, with the two steering neurons on top."
    )
    return (
        f'<figure class="picture"><img src="runs/{text(name)}" width="{width}" height="{height}" {priority} '
        f'alt="{text(alt)}"><figcaption>Every neuron that fired, in both trials. The white marks on top are the '
        f"steering neuron, left and right.</figcaption></figure>"
    )


def post(decision: dict) -> str:
    if not decision["post"]:
        return ""
    paragraphs = "".join(f"<p>{text(part)}</p>" for part in decision["post"])
    footer = "".join(f"<li>{text(line)}</li>" for line in decision["footer"])
    return f'<blockquote class="post">{paragraphs}<ul>{footer}</ul></blockquote>'


def today(decision: dict) -> str:
    return f"""
<section id="today" class="decision" aria-labelledby="today-title">
  <div class="wrap">
    <p class="date">Decision of {text(long_date(decision['date']))}</p>
    <div class="decision-grid">
      <div>
        <h2 id="today-title" class="question">{text(decision['question'])}</h2>
        <p class="verdict">Dro turned towards <strong>{text(verdict(decision))}</strong></p>
        {spikes(decision)}
        <p class="small">{contrast_note(decision)}</p>
        {post(decision)}
      </div>
      {picture(decision, first=True)}
    </div>
  </div>
</section>"""


def archive(decisions: list[dict]) -> str:
    if not decisions:
        return ""
    items = []
    for decision in decisions:
        when = long_date(decision["date"]) + (f", run {decision['run']}" if decision["run"] > 1 else "")
        log = f"{REPOSITORY}/blob/main/runs/{decision['stem']}.json"
        items.append(
            f"""
    <details>
      <summary><span class="when">{text(when)}</span><span class="what">{text(decision['question'])}
        <span class="won">{text(verdict(decision))}</span>, {decision['toward_a']} to {decision['toward_b']}</span></summary>
      <div class="entry"><div class="entry-grid">
        <div>{spikes(decision)}<p class="small">{contrast_note(decision)}</p>{post(decision)}
          <p class="small"><a href="{text(log)}">The full log of this run</a></p></div>
        {picture(decision, first=False)}
      </div></div>
    </details>"""
        )
    return f"""
<section id="archive" class="archive" aria-labelledby="archive-title">
  <div class="wrap">
    <h2 id="archive-title" class="section-title">Earlier decisions</h2>
    <p class="intro">Every run is kept, including the ones that came out undecided.</p>
    {''.join(items)}
  </div>
</section>"""


def page(decisions: list[dict], upcoming: str | None, waiting: int) -> str:
    newest, earlier = decisions[-1], decisions[-2::-1]
    judged = [d for d in decisions if d["by_input"] in ("a", "b") and d["choice"] in ("a", "b")]
    agreed = sum(d["by_input"] == d["choice"] for d in judged)
    title = "Dro: a fruit fly's wiring diagram that makes one decision a day"
    summary = (
        f"Dro is a simulation of a fruit fly's wiring diagram, {NEURONS:,} neurons. Once a day it is shown two "
        "options as pictures and turns towards one. It is not alive and it cannot read."
    )
    share_picture = f'<meta property="og:image" content="{ADDRESS}runs/{text(newest["picture"][0])}">' if newest["picture"] else ""
    channel = f'<li><a href="{text(CHANNEL)}">Telegram channel</a></li>' if CHANNEL else ""
    next_up = (
        f"<p class=\"small\">Next in the queue: “{text(upcoming)}”. {waiting} measured "
        f"question{'s' if waiting != 1 else ''} are waiting.</p>"
        if upcoming
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#f6f3ec">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0b0b0d">
<title>{text(title)}</title>
<meta name="description" content="{text(summary)}">
<meta property="og:title" content="{text(title)}">
<meta property="og:description" content="{text(summary)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{ADDRESS}">
{share_picture}
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip" href="#today">Skip to today's decision</a>
<header class="masthead">
  <div class="wrap">
    <p class="eyebrow">FlyCorp · Office of the Chief Fruit Officer</p>
    <h1>Dro makes one decision a day.</h1>
    <p class="lede">Dro is a simulation of the complete wiring diagram of a fruit fly's nervous system. Every day
      it is shown two options as pictures, one per eye, and whichever one its steering neuron turns towards
      wins.</p>
    <ul class="facts">
      <li>{NEURONS:,} neurons</li>
      <li>not alive</li>
      <li>cannot read</li>
      <li>decides anyway</li>
    </ul>
    <nav class="jump" aria-label="On this page">
      <ul>
        <li><a href="#today">Today</a></li>
        <li><a href="#who">Who did what</a></li>
        <li><a href="#how">How it works</a></li>
        <li><a href="#trust">How far to trust it</a></li>
        <li><a href="#archive">Earlier decisions</a></li>
        <li><a href="#gate">Fly Gate</a></li>
        <li><a href="#portraits">Portraits</a></li>
      </ul>
    </nav>
  </div>
</header>
<main>
{today(newest)}
<section id="who" aria-labelledby="who-title">
  <div class="wrap">
    <h2 id="who-title" class="section-title">Who did what</h2>
    <p class="intro">Every log and every post keeps the same split between the fly and the rig around it.</p>
    <div class="pair">
      <div class="card">
        <h3>The fly</h3>
        <ul>
          <li>Where each of its object-detecting cells looks</li>
          <li>How their firing spreads through the brain and competes between the two sides</li>
          <li>Which side its steering neuron fired on, and so the choice</li>
        </ul>
      </div>
      <div class="card">
        <h3>The rig: code and a human</h3>
        <ul>
          <li>The question and the two options</li>
          <li>Drawing the options as pictures</li>
          <li>The early vision: turning the contrast of a picture into firing of the object-detecting cells</li>
          <li>The rule that reads a turn as a choice, and every word written about it</li>
        </ul>
      </div>
    </div>
  </div>
</section>
<section id="how" aria-labelledby="how-title">
  <div class="wrap">
    <h2 id="how-title" class="section-title">How a decision is made</h2>
    <ol class="steps">
      <li>Each option is drawn as a small grey picture. Text is dark on a bright page; to the fly it is a
        texture, not words.</li>
      <li>The rig hands each picture to about 140 cells of one eye's side that respond to visual objects. Where
        each cell looks comes from the wiring; how strongly it fires depends on the contrast of the picture at
        that spot.</li>
      <li>The simulated brain runs for one second with option A on the left and option B on the right, then for
        another second with the sides swapped, so that a built-in preference for one side cancels out.</li>
      <li>The spikes of the steering neuron DNa02 are counted on the left and on the right. More spikes on one
        side is read as a turn towards the picture shown there.</li>
      <li>The option the fly turned towards more, over both seconds, wins. Equal counts are logged as
        undecided.</li>
    </ol>
    {next_up}
  </div>
</section>
<section id="trust" aria-labelledby="trust-title">
  <div class="wrap">
    <h2 id="trust-title" class="section-title">How far to trust it</h2>
    <ul class="numbers">
      <li class="card"><span class="figure">{PAIRS_REPEATING} of {PAIRS_MEASURED}</span>
        test pairs gave the same winner in at least 16 of 20 runs with different random seeds. The rest are a
        coin toss and are kept out of the queue.</li>
      <li class="card"><span class="figure">{PAIRS_FOLLOWING_CONTRAST} of {PAIRS_REPEATING}</span>
        of those winners were simply the picture with more contrast, a number the rig computes before the brain
        runs. The brain passes the difference on and sharpens it.</li>
      <li class="card"><span class="figure">{agreed} of {len(judged)}</span>
        decisions on this page went the same way as the contrast alone. The rest are the times the wiring
        overruled the rig.</li>
    </ul>
    <p class="intro">The model is a wiring diagram with a very simple neuron on top: nothing is trained, and one
      constant is fitted, against a published experiment. A picture fed into the fly's eye is lost two cells
      later in this model, which is why the rig does the early vision itself. The right side of the brain wins
      more often than the left, probably because of the data rather than the animal.
      <a href="{REPOSITORY}/blob/main/docs/CALIBRATION_NOTES.md">Every experiment, including the failed ones</a>.</p>
  </div>
</section>
{archive(earlier)}
<section id="gate" aria-labelledby="gate-title">
  <div class="wrap">
    <h2 id="gate-title" class="section-title">Fly Gate</h2>
    <div class="split">
      <div>
        <p>Fly Gate lets the fly look at pull requests. The lines a pull request adds become one picture, the
          lines it removes the other, and the fly turns towards the new or the old. It then says so in a
          comment: “LGTM. I did not read it.”</p>
        <p class="small">It is not a code review, and the comment says that too. By default it never blocks a
          merge. <a href="{REPOSITORY}#fly-gate">How to set it up, also for Azure Pipelines</a>.</p>
      </div>
      <pre tabindex="0" aria-label="Workflow file that adds Fly Gate to a repository"><code>{text(GATE_EXAMPLE)}</code></pre>
    </div>
  </div>
</section>
<section id="portraits" aria-labelledby="portraits-title">
  <div class="wrap">
    <h2 id="portraits-title" class="section-title">Portrait through a fly's eyes</h2>
    <div class="split">
      <div>
        <p>A poster of how the brain reacted to a photograph: what reached the eyes as 32 by 32 points of
          light, what the object-detecting cells reported, and every neuron that fired in one second of
          looking.</p>
        <p class="small">The fly sees no face, only light and dark. Portraits are not open to everyone yet.
          The example was made from a public-domain photograph of Grace Hopper.</p>
      </div>
      <figure class="portrait"><img src="portrait.png" width="1080" height="1350" loading="lazy"
        alt="Example poster: a pixelated photograph, two maps of dots showing where the object-detecting cells look, and a field of spikes."></figure>
    </div>
  </div>
</section>
</main>
<footer>
  <div class="wrap">
    <ul class="facts">
      <li><a href="{REPOSITORY}">Code and every run log on GitHub</a></li>
      {channel}
    </ul>
    <p>Dro is not conscious, not alive and not an uploaded fly. It gives no financial, medical or legal
      advice.</p>
    <p>Connectome: MaleCNS v1.0 by the FlyEM Project Team at HHMI Janelia, the Cambridge Connectomics Group, the
      MRC Laboratory of Molecular Biology and Google Research, CC BY 4.0 (Berg et al., Cell 2026). Neuron model:
      Shiu et al., Nature 2024. Code: MIT.</p>
  </div>
</footer>
</body>
</html>
"""


def build(root: Path, out: Path) -> dict:
    """Write the site into ``out``. Returns a few numbers about what was written."""
    runs = root / "runs"
    decisions = [load(log) for log in run_logs(runs)]
    if not decisions:
        raise FileNotFoundError(f"no run logs in {runs}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "runs").mkdir(exist_ok=True)
    for decision in decisions:
        if decision["picture"]:
            shutil.copyfile(runs / decision["picture"][0], out / "runs" / decision["picture"][0])
    for name in ("style.css", "favicon.svg"):
        shutil.copyfile(root / "web" / name, out / name)
    shutil.copyfile(root / "docs" / "sample-portrait" / "grace.png", out / "portrait.png")

    upcoming, waiting = None, 0
    queue_file = root / "questions.json"
    if queue_file.exists():
        queue = json.loads(queue_file.read_text(encoding="utf-8"))
        asked = {frozenset((decision["a"], decision["b"])) for decision in decisions}
        waiting = sum(frozenset((entry["a"], entry["b"])) not in asked for entry in queue)
        if queue:
            upcoming = next_question(queue, runs)["question"]
    (out / "index.html").write_text(page(decisions, upcoming, waiting), encoding="utf-8")
    return {"decisions": len(decisions), "newest": decisions[-1]["stem"], "waiting": waiting}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the website from the run logs.")
    parser.add_argument("--root", type=Path, default=Path("."), help="the repository")
    parser.add_argument("--out", type=Path, default=Path("_site"))
    args = parser.parse_args(argv)
    print(f"{args.out}: {build(args.root, args.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
