"""Answer photos sent to the Telegram bot with portraits.

Usage::

    python -m dro.portrait_bot --peek     # how many messages are waiting
    python -m dro.portrait_bot            # answer them

Someone sends the bot a photo in a private chat; the bot answers with a
"portrait through a fly's eyes" (see ``portrait.py``). A caption on the
photo becomes the name in the heading.

Only administrators of the channel in ``TELEGRAM_CHAT_ID`` are served, which
in practice means the owner. Everyone else gets one sentence saying that
portraits are not open yet, and their photo is not fetched.

Photos are kept only for the seconds it takes to make the poster, in a
temporary folder that is deleted afterwards. Nothing about a message is
written to the log: no names, no numbers of chats, no text.

Needs ``TELEGRAM_BOT_TOKEN`` and ``TELEGRAM_CHAT_ID`` in the environment.
There is no server: a scheduled job runs this now and then, so an answer
can take up to an hour.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

from . import telegram

MAX_PHOTOS = 10  # per run; the rest wait for the next run
NAME_LIMIT = 40
NOT_OPEN = "Portraits are not open to everyone yet. Follow the channel to hear when they are."
HOW_TO = "Send me a photo and I will answer with a portrait through a fly's eyes. A caption becomes the name on it."
UNREADABLE = "I could not read that picture. Please send it as a photo."
CAPTION = (
    "{fired} of {neurons} simulated neurons fired. Dro is a simulation of a fruit fly's wiring "
    "diagram: it is not alive, and it saw light and dark, not a face."
)


def waiting(token: str, opener=urllib.request.urlopen) -> list[dict]:
    """Messages sent to the bot that have not been answered yet."""
    return telegram.ask(token, "getUpdates", {"timeout": 0, "allowed_updates": ["message"]}, opener) or []


def administrators(token: str, channel: str, opener=urllib.request.urlopen) -> set[int]:
    """The people who may ask for a portrait: the administrators of the channel."""
    members = telegram.ask(token, "getChatAdministrators", {"chat_id": channel}, opener) or []
    return {member["user"]["id"] for member in members if not member["user"].get("is_bot")}


def photo_of(message: dict) -> str | None:
    """The file id of the picture in a message, if it has one."""
    if message.get("photo"):
        return message["photo"][-1]["file_id"]  # sizes come smallest first
    document = message.get("document") or {}
    if (document.get("mime_type") or "").startswith("image/"):
        return document["file_id"]
    return None


def serve(token: str, channel: str, graph_dir: Path, opener=urllib.request.urlopen, make=None) -> dict:
    """Answer the waiting messages. Returns counts only."""
    counts = {"portraits": 0, "refused": 0, "other": 0, "failed": 0}
    updates = waiting(token, opener)
    if not updates:
        return counts
    allowed = administrators(token, channel, opener)
    graph, told, last = None, set(), None
    for update in updates:
        if counts["portraits"] >= MAX_PHOTOS:
            break
        last = update["update_id"]
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        if chat.get("type") != "private":
            continue
        sender = (message.get("from") or {}).get("id")
        if sender not in allowed:
            if sender not in told:  # one answer per person and run is enough
                telegram.send_message(token, chat["id"], NOT_OPEN, opener)
                told.add(sender)
            counts["refused"] += 1
            continue
        file_id = photo_of(message)
        if not file_id:
            telegram.send_message(token, chat["id"], HOW_TO, opener)
            counts["other"] += 1
            continue
        try:
            if make is None:  # the simulation is loaded only when there is a photo to look at
                from .graph import load
                from .portrait import make as make_portrait

                graph = graph or load(graph_dir)
                make = lambda photo, out, name: make_portrait(graph, photo, out, name)  # noqa: E731
            path = telegram.ask(token, "getFile", {"file_id": file_id}, opener)["file_path"]
            with tempfile.TemporaryDirectory() as folder:
                photo, poster = Path(folder) / "photo", Path(folder) / "portrait.png"
                photo.write_bytes(telegram.download(token, path, opener))
                name = (message.get("caption") or "").strip()[:NAME_LIMIT] or None
                numbers = make(photo, poster, name)
                caption = CAPTION.format(fired=f"{numbers['fired']:,}", neurons=f"{numbers['neurons']:,}")
                telegram.send_photo(token, chat["id"], "portrait.png", poster.read_bytes(), caption, opener)
            counts["portraits"] += 1
        except Exception:  # one bad picture must not stop the others; nothing about it is logged
            telegram.send_message(token, chat["id"], UNREADABLE, opener)
            counts["failed"] += 1
    if last is not None:
        # Tell Telegram these messages are dealt with, so they are not delivered again.
        telegram.ask(token, "getUpdates", {"offset": last + 1, "timeout": 0}, opener)
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Answer photos sent to the bot with portraits.")
    parser.add_argument("--graph", type=Path, default=Path("data/compiled"))
    parser.add_argument("--peek", action="store_true", help="only print how many messages are waiting")
    args = parser.parse_args(argv)

    token, channel = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and channel):
        print("waiting=0")
        print("portraits: not switched on (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not both set)", file=sys.stderr)
        return 0
    try:
        if args.peek:
            print(f"waiting={len(waiting(token))}")
            return 0
        counts = serve(token, channel, args.graph)
    except RuntimeError as error:
        print(f"portraits: failed. {error}", file=sys.stderr)
        return 1
    print("portraits: " + ", ".join(f"{count} {name}" for name, count in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
