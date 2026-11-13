"""Fly Gate: let the fly look at a pull request.

The lines a pull request adds are drawn as one picture and the lines it
removes as another. The simulated brain is shown one picture per eye, then
the eyes are swapped, exactly as for a daily question. If its steering
neuron fires more towards the new lines, the verdict is "LGTM"; towards the
old lines, "changes requested"; equally, no opinion.

This is not a code review. The fly cannot read, and the picture with more
contrast usually wins. The comment says so every time.

Usage::

    git diff main... | python -m dro.gate --patch -      # try it on any diff
    python -m dro.gate --graph data/compiled             # inside GitHub Actions

Inside GitHub Actions the changed lines come from the pull request named in
the event, the verdict is written to the job summary, and a comment is
posted to the pull request (and updated on later pushes) if the token
allows it. With ``--enforce`` the command fails when the fly prefers the
old lines.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

from .decide import STEERING_TYPES, decide, save_raster
from .graph import Graph, load
from .stimulus import render_lines

MARKER = "<!-- fly-gate -->"
OPTIONS = {"a": "the new lines", "b": "the old lines"}
STRIP_WIDTH = 50  # characters in a spike strip
SMALL_MARGIN = 5  # below this many spikes of difference the comment calls it a coin toss
HEADINGS = {
    "a": "LGTM. I did not read it.",
    "b": "Changes requested. I did not read it.",
    "undecided": "No opinion. I did not read it either way.",
}
HOME = "https://github.com/DemonazGH/Dro"


HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")


def changed_lines(patches: list[str]) -> tuple[list[str], list[str]]:
    """Added and removed lines of unified diffs, without the +/- markers.

    Lines are read only inside hunks, and each hunk is as long as its header
    says. So a file header such as ``+++ b/file`` is never taken for a
    change, and a changed line that itself starts with ``++`` or ``--`` is.
    Blank lines are left out: they draw nothing.
    """
    added, removed = [], []
    for patch in patches:
        old_left = new_left = 0
        for line in patch.splitlines():
            header = HUNK.match(line)
            if header:
                old_left = int(header.group(1) or 1)
                new_left = int(header.group(2) or 1)
            elif line.startswith("\\"):  # "\ No newline at end of file"
                continue
            elif old_left or new_left:
                if line.startswith("+"):
                    new_left -= 1
                    if line[1:].strip():
                        added.append(line[1:])
                elif line.startswith("-"):
                    old_left -= 1
                    if line[1:].strip():
                        removed.append(line[1:])
                else:  # a context line counts on both sides
                    old_left -= 1
                    new_left -= 1
    return added, removed


def make_seed(repository: str, number: int, head: str) -> int:
    """Fixed by the pull request and its head commit: a rerun cannot change the answer."""
    text = "\n".join(["fly-gate", repository, str(number), head]).encode()
    return int.from_bytes(hashlib.sha256(text).digest()[:4], "big")


def look(graph: Graph, added: list[str], removed: list[str], seed: int, title: str) -> tuple[dict, list]:
    """Show the fly the new lines against the old lines."""
    pictures = {"a": render_lines(added), "b": render_lines(removed)}
    record, results = decide(graph, title, OPTIONS["a"], OPTIONS["b"], seed, pictures=pictures)
    record = {"date": dt.datetime.now(dt.timezone.utc).date().isoformat(), **record}
    record["lines"] = {"added": len(added), "removed": len(removed)}
    return record, results


def spike_strip(times_ms: np.ndarray, duration_ms: float, width: int = STRIP_WIDTH) -> str:
    """Spike times as a row of characters: | where the neuron fired, · where it did not."""
    cells = ["·"] * width
    for time in times_ms:
        cells[min(int(time / duration_ms * width), width - 1)] = "|"
    return "".join(cells)


def strips(graph: Graph, record: dict, results: list) -> str:
    """The two steering neurons in both trials, as text."""
    meta = graph.meta
    steering = meta["type"].isin(STEERING_TYPES).to_numpy(dtype=bool, na_value=False)
    side = meta["somaSide"].fillna("").to_numpy(dtype=str)
    lines = []
    for trial, result in zip(record["trials"], results):
        lines.append(
            f"left eye: {OPTIONS[trial['left_eye']]}, right eye: {OPTIONS[trial['right_eye']]}"
        )
        for name, letter in (("left ", "L"), ("right", "R")):
            cells = np.flatnonzero(steering & (side == letter))
            times = result.spike_times_ms[np.isin(result.spike_neurons, cells)]
            lines.append(f"  steering {name} {spike_strip(times, result.duration_ms)} {times.size:>3}")
    return "\n".join(lines)


def comment(graph: Graph, record: dict, results: list, picture_url: str | None = None) -> str:
    """The text posted to the pull request."""
    toward = record["steering_spikes_toward"]
    choice = record["choice"]
    count = record["lines"]
    if choice == "undecided":
        what = f"Dro turned towards neither: {toward['a']} steering spikes each way."
    else:
        other = "b" if choice == "a" else "a"
        what = (
            f"Dro turned towards **{OPTIONS[choice]}**: {toward[choice]} steering spikes "
            f"against {toward[other]}."
        )
        if toward[choice] - toward[other] < SMALL_MARGIN:
            what += " That is a small margin: treat it as a coin toss."
    by_input = record["choice_by_input_alone"]
    if by_input == "tie":
        contrast = "Here the two pictures had the same contrast."
    elif by_input == choice:
        contrast = "Here it did."
    else:
        contrast = f"Here that was {OPTIONS[by_input]}, and the fly did not follow."
    links = [f"seed {record['seed']}"]
    if picture_url:
        links.append(f"[activity picture]({picture_url})")
    links.append(f"[how it works]({HOME})")
    return "\n".join(
        [
            MARKER,
            f"### Fly Gate: {HEADINGS[choice]}",
            "",
            what,
            "",
            "```text",
            strips(graph, record, results),
            "```",
            "",
            f"**What the fly did.** A simulation of a fruit fly's wiring diagram ({graph.n:,} "
            "neurons) was shown one picture per eye, then the eyes were swapped. The spikes "
            "above are its steering neuron DNa02, left and right; more spikes on one side is "
            "read as a turn towards the picture on that side.",
            "",
            f"**What the rig did.** It drew the first lines this pull request adds ({count['added']} "
            f"in all) as one picture and the first lines it removes ({count['removed']} in all) as the "
            "other, and turned the contrast of each picture into input for the brain. The "
            f"picture with more contrast usually wins. {contrast}",
            "",
            "**What this is not.** A code review. The fly cannot read, and Dro is a simulation, "
            "not a fly and not alive.",
            "",
            "<sub>" + " · ".join(links) + "</sub>",
        ]
    )


def nothing_to_see() -> str:
    """The comment for a pull request without changed text lines."""
    return "\n".join(
        [
            MARKER,
            "### Fly Gate: nothing to look at",
            "",
            "This pull request adds and removes no lines of text, so the fly was shown nothing.",
            "",
            f"<sub>[how it works]({HOME})</sub>",
        ]
    )


def _api(url: str, token: str, opener, method: str = "GET", body: dict | None = None):
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with opener(request, timeout=60) as response:
        return json.loads(response.read().decode() or "null")


def fetch_patches(api: str, repository: str, number: int, token: str, opener=urllib.request.urlopen) -> list[str]:
    """The patches of all files of a pull request. Files without a text patch are skipped."""
    patches = []
    for page in range(1, 31):  # GitHub lists at most 3,000 files
        files = _api(f"{api}/repos/{repository}/pulls/{number}/files?per_page=100&page={page}", token, opener)
        patches += [entry["patch"] for entry in files if entry.get("patch")]
        if len(files) < 100:
            break
    return patches


def current_head(api: str, repository: str, number: int, token: str, opener=urllib.request.urlopen) -> str:
    """The head commit the pull request has right now."""
    return _api(f"{api}/repos/{repository}/pulls/{number}", token, opener)["head"]["sha"]


def post_comment(
    api: str, repository: str, number: int, token: str, body: str, opener=urllib.request.urlopen
) -> str:
    """Create the Fly Gate comment, or update the one from an earlier push."""
    page = 1
    while True:
        comments = _api(
            f"{api}/repos/{repository}/issues/{number}/comments?per_page=100&page={page}", token, opener
        )
        for existing in comments:
            if MARKER in (existing.get("body") or ""):
                _api(
                    f"{api}/repos/{repository}/issues/comments/{existing['id']}",
                    token, opener, "PATCH", {"body": body},
                )
                return "updated"
        if len(comments) < 100:
            break
        page += 1
    _api(f"{api}/repos/{repository}/issues/{number}/comments", token, opener, "POST", {"body": body})
    return "created"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Let the fly look at a pull request.")
    parser.add_argument("--graph", type=Path, default=Path("data/compiled"))
    parser.add_argument("--patch", help="read a unified diff from this file, or - for standard input")
    parser.add_argument("--out", type=Path, help="directory for the activity picture and the record")
    parser.add_argument("--enforce", action="store_true", help="fail when the fly prefers the old lines")
    args = parser.parse_args(argv)

    environment = os.environ
    token = environment.get("GITHUB_TOKEN", "")
    api = environment.get("GITHUB_API_URL", "https://api.github.com")
    repository, number, picture_url = environment.get("GITHUB_REPOSITORY", "local"), 0, None
    if args.patch:
        text = sys.stdin.read() if args.patch == "-" else Path(args.patch).read_text(encoding="utf-8")
        patches, head = [text], hashlib.sha256(text.encode()).hexdigest()
    else:
        event = json.loads(Path(environment["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        pull = event.get("pull_request")
        if not pull:
            print("this event has no pull request; Fly Gate runs on pull_request events", file=sys.stderr)
            return 2
        number, head = pull["number"], pull["head"]["sha"]
        patches = fetch_patches(api, repository, number, token)
        # The list of files always describes the newest commit. If the pull
        # request has moved on since this job was started, the files no longer
        # belong to the commit this job, and its seed, stand for.
        if current_head(api, repository, number, token) != head:
            print(f"commit {head[:7]} is no longer the head of the pull request; nothing done", file=sys.stderr)
            return 0
        if environment.get("GITHUB_RUN_ID"):
            server = environment.get("GITHUB_SERVER_URL", "https://github.com")
            picture_url = f"{server}/{repository}/actions/runs/{environment['GITHUB_RUN_ID']}"

    added, removed = changed_lines(patches)
    choice = None
    if added or removed:
        graph = load(args.graph)
        title = f"Pull request #{number}: new lines or old lines?" if number else "New lines or old lines?"
        record, results = look(graph, added, removed, make_seed(repository, number, head), title)
        choice = record["choice"]
        body = comment(graph, record, results, picture_url)
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            save_raster(graph, results, record, args.out / "fly-gate.png")
            (args.out / "fly-gate.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    else:
        body = nothing_to_see()

    print(body)
    summary = environment.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(body + "\n")
    if number and token:
        try:
            print(f"comment: {post_comment(api, repository, number, token, body)}", file=sys.stderr)
        except urllib.error.HTTPError as error:
            # Pull requests from forks get a read-only token. The summary still has the verdict.
            print(f"comment: not posted, GitHub answered {error.code}", file=sys.stderr)
        except urllib.error.URLError as error:
            print(f"comment: not posted, {error.reason}", file=sys.stderr)
    if args.enforce and choice == "b":
        print("the fly prefers the old lines, and --enforce is set", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
