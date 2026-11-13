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
    python -m dro.gate --patch pr.patch                  # inside Azure Pipelines

Inside GitHub Actions the changed lines come from the pull request named in
the event, the verdict is written to the job summary, and a comment is
posted to the pull request (and updated on later pushes) if the token
allows it.

Inside Azure Pipelines the diff is given with ``--patch``, taken from the
merge commit the build checked out. For a pull request in Azure Repos the
verdict is posted as a closed comment thread, so it never counts as an
unresolved comment, and updated on later pushes. This needs the variable
``SYSTEM_ACCESSTOKEN`` and, for the build service, the permission to
contribute to pull requests.

With ``--enforce`` the command fails when the fly prefers the old lines.
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
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

from .decide import STEERING_TYPES, decide, save_raster
from .graph import Graph, load
from .stimulus import render_lines

MARKER = "<!-- fly-gate -->"
HEADING = "### Fly Gate:"
AZURE_API = "api-version=7.0"
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


def comment(
    graph: Graph, record: dict, results: list, picture_url: str | None = None, plain: bool = False
) -> str:
    """The text posted to the pull request.

    ``plain`` leaves out the hidden marker and the small print tags, for
    places that would show them as text.
    """
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
    small_print = " · ".join(links)
    return "\n".join(
        ([] if plain else [MARKER])
        + [
            f"{HEADING} {HEADINGS[choice]}",
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
            small_print if plain else f"<sub>{small_print}</sub>",
        ]
    )


def nothing_to_see(plain: bool = False) -> str:
    """The comment for a pull request without changed text lines."""
    link = f"[how it works]({HOME})"
    return "\n".join(
        ([] if plain else [MARKER])
        + [
            f"{HEADING} nothing to look at",
            "",
            "This pull request adds and removes no lines of text, so the fly was shown nothing.",
            "",
            link if plain else f"<sub>{link}</sub>",
        ]
    )


def _api(url: str, token: str, opener, method: str = "GET", body: dict | None = None, github: bool = True):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if github:
        headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    else:
        headers["Accept"] = "application/json"
    request = urllib.request.Request(
        url, data=json.dumps(body).encode() if body is not None else None, method=method, headers=headers
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


def azure_context(environment) -> dict | None:
    """The pull request an Azure Pipelines build was started for, if any."""
    number = environment.get("SYSTEM_PULLREQUEST_PULLREQUESTID")
    if not (environment.get("TF_BUILD") and number):
        return None
    collection = environment.get("SYSTEM_COLLECTIONURI", "").rstrip("/")
    project = urllib.parse.quote(environment.get("SYSTEM_TEAMPROJECT", ""))
    repository_id = environment.get("BUILD_REPOSITORY_ID", "")
    return {
        "number": int(number),
        "head": environment.get("SYSTEM_PULLREQUEST_SOURCECOMMITID", ""),
        "repository": f"{collection}/{project}/{repository_id}",
        "pull": f"{collection}/{project}/_apis/git/repositories/{repository_id}/pullRequests/{number}",
        "run": f"{collection}/{project}/_build/results?buildId={environment.get('BUILD_BUILDID', '')}",
        # Comment threads exist only for pull requests in Azure Repos.
        "azure_repos": environment.get("BUILD_REPOSITORY_PROVIDER") == "TfsGit",
    }


def azure_head(pull: str, token: str, opener=urllib.request.urlopen) -> str:
    """The source commit the Azure Repos pull request has right now."""
    answer = _api(f"{pull}?{AZURE_API}", token, opener, github=False)
    return answer["lastMergeSourceCommit"]["commitId"]


def post_azure_thread(pull: str, token: str, body: str, opener=urllib.request.urlopen) -> str:
    """Create the Fly Gate thread on an Azure Repos pull request, or update its comment."""
    threads = _api(f"{pull}/threads?{AZURE_API}", token, opener, github=False)["value"]
    for thread in threads:
        for existing in thread.get("comments") or []:
            if (existing.get("content") or "").startswith(HEADING):
                address = f"{pull}/threads/{thread['id']}/comments/{existing['id']}?{AZURE_API}"
                _api(address, token, opener, "PATCH", {"content": body}, github=False)
                return "updated"
    # A closed thread does not count as an unresolved comment in branch policies.
    thread = {"comments": [{"parentCommentId": 0, "content": body, "commentType": 1}], "status": "closed"}
    _api(f"{pull}/threads?{AZURE_API}", token, opener, "POST", thread, github=False)
    return "created"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Let the fly look at a pull request.")
    parser.add_argument("--graph", type=Path, default=Path("data/compiled"))
    parser.add_argument("--patch", help="read a unified diff from this file, or - for standard input")
    parser.add_argument("--out", type=Path, help="directory for the activity picture and the record")
    parser.add_argument("--enforce", action="store_true", help="fail when the fly prefers the old lines")
    args = parser.parse_args(argv)

    environment = os.environ
    azure = azure_context(environment)
    github_token = environment.get("GITHUB_TOKEN", "")
    azure_token = environment.get("SYSTEM_ACCESSTOKEN", "")
    api = environment.get("GITHUB_API_URL", "https://api.github.com")
    repository, number, picture_url = environment.get("GITHUB_REPOSITORY", "local"), 0, None
    if args.patch:
        text = sys.stdin.read() if args.patch == "-" else Path(args.patch).read_text(encoding="utf-8")
        patches, head = [text], hashlib.sha256(text.encode()).hexdigest()
        if azure:
            repository, number, picture_url = azure["repository"], azure["number"], azure["run"]
            head = azure["head"] or head
            # The patch was cut from the commit this build checked out. If the
            # pull request has moved on, a newer build will bring the verdict.
            if azure["azure_repos"] and azure_token and head:
                try:
                    stale = azure_head(azure["pull"], azure_token) != head
                except (urllib.error.URLError, KeyError, TypeError):
                    stale = False  # cannot tell; go on
                if stale:
                    print(f"commit {head[:7]} is no longer the head of the pull request; nothing done", file=sys.stderr)
                    return 0
    elif azure:
        print("in Azure Pipelines the diff must be given with --patch", file=sys.stderr)
        return 2
    else:
        event = json.loads(Path(environment["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        pull = event.get("pull_request")
        if not pull:
            print("this event has no pull request; Fly Gate runs on pull_request events", file=sys.stderr)
            return 2
        number, head = pull["number"], pull["head"]["sha"]
        patches = fetch_patches(api, repository, number, github_token)
        # The list of files always describes the newest commit. If the pull
        # request has moved on since this job was started, the files no longer
        # belong to the commit this job, and its seed, stand for.
        if current_head(api, repository, number, github_token) != head:
            print(f"commit {head[:7]} is no longer the head of the pull request; nothing done", file=sys.stderr)
            return 0
        if environment.get("GITHUB_RUN_ID"):
            server = environment.get("GITHUB_SERVER_URL", "https://github.com")
            picture_url = f"{server}/{repository}/actions/runs/{environment['GITHUB_RUN_ID']}"

    plain = azure is not None
    added, removed = changed_lines(patches)
    choice = None
    if added or removed:
        graph = load(args.graph)
        title = f"Pull request #{number}: new lines or old lines?" if number else "New lines or old lines?"
        record, results = look(graph, added, removed, make_seed(repository, number, head), title)
        choice = record["choice"]
        body = comment(graph, record, results, picture_url, plain)
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            save_raster(graph, results, record, args.out / "fly-gate.png")
            (args.out / "fly-gate.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    else:
        body = nothing_to_see(plain)

    print(body)
    summary = environment.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(body + "\n")
    if azure and args.out:
        # Show the verdict on the summary page of the build.
        args.out.mkdir(parents=True, exist_ok=True)
        page = (args.out / "fly-gate.md").resolve()
        page.write_text(body + "\n", encoding="utf-8")
        print(f"##vso[task.uploadsummary]{page}")

    try:
        if azure and azure["azure_repos"] and azure_token:
            print(f"comment: {post_azure_thread(azure['pull'], azure_token, body)}", file=sys.stderr)
        elif azure:
            print("comment: not posted (needs an Azure Repos pull request and SYSTEM_ACCESSTOKEN)", file=sys.stderr)
        elif number and github_token:
            print(f"comment: {post_comment(api, repository, number, github_token, body)}", file=sys.stderr)
    except urllib.error.HTTPError as error:
        # On GitHub, pull requests from forks get a read-only token. In Azure
        # DevOps the build service may lack the permission. The verdict is
        # still on the page of the run.
        print(f"comment: not posted, the server answered {error.code}", file=sys.stderr)
        if azure:
            print(
                'Allow "Contribute to pull requests" for the build service on this repository '
                "(Project settings, Repositories, Security).",
                file=sys.stderr,
            )
    except urllib.error.URLError as error:
        print(f"comment: not posted, {error.reason}", file=sys.stderr)
    if args.enforce and choice == "b":
        print("the fly prefers the old lines, and --enforce is set", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
