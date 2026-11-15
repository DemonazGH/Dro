"""Reading run logs and posts. Standard library only.

Nothing of the simulation is imported here, so the website can be built
without installing its dependencies.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

NOTES_MARKER = "--- notes for the editor, not part of the post ---"


def log_order(path: Path) -> tuple:
    """Sort key for run logs: date, then the run number within that date."""
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:-(\d+))?", path.stem)
    return (match.group(1), int(match.group(2) or 1)) if match else ("", 0)


def run_logs(runs: Path) -> list[Path]:
    """All run logs of a folder, oldest first."""
    return sorted((path for path in runs.glob("*.json") if log_order(path)[0]), key=log_order)


def next_question(queue: list[dict], runs: Path) -> dict:
    """The question to ask next.

    The first entry of the queue whose pair of options has no run log yet.
    Once every entry has been asked, the one asked longest ago. The choice
    depends only on the queue and the logs, never on a result.
    """
    last_asked = {}
    for position, path in enumerate(run_logs(runs)):
        options = json.loads(path.read_text(encoding="utf-8")).get("options", {})
        last_asked[frozenset(options.values())] = position
    return min(queue, key=lambda entry: last_asked.get(frozenset((entry["a"], entry["b"])), -1))


def post_text(draft: str) -> str:
    """The part of a draft that is published: the post and its footer."""
    return draft.split(NOTES_MARKER)[0].strip()
