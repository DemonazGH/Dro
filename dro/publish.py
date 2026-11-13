"""Send a finished post to the channels the owner has switched on.

Usage::

    python -m dro.publish runs/2026-11-13.md
    python -m dro.publish                      # the newest post in runs/

A channel is switched on by giving it credentials in the environment; in
GitHub Actions these come from repository secrets. Without credentials
nothing is sent and the command says so.

Telegram: ``TELEGRAM_BOT_TOKEN`` (from @BotFather) and ``TELEGRAM_CHAT_ID``
(a channel name such as ``@flycorp``, or a numeric chat id). The bot must be
an administrator of the channel.

Only the post and its footer are sent, never the notes for the editor. The
activity picture that belongs to the same run is attached if it exists.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.request
from pathlib import Path

from .decide import log_order
from .draft import post_text
from .telegram import CAPTION_LIMIT, multipart, send_message, send_photo  # noqa: F401 (multipart is re-exported)


def send_telegram(
    text: str, photo: Path | None, token: str, chat: str, opener=urllib.request.urlopen
) -> list[str]:
    """Send the post to a Telegram chat. Returns the API methods that were called."""
    called = []
    if photo is not None:
        fits = len(text) <= CAPTION_LIMIT
        send_photo(token, chat, photo.name, photo.read_bytes(), text if fits else None, opener)
        called.append("sendPhoto")
        if fits:
            return called
    send_message(token, chat, text, opener)
    called.append("sendMessage")
    return called


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send a post to the channels that are switched on.")
    parser.add_argument("draft", nargs="?", type=Path, help="a post written by python -m dro.draft")
    parser.add_argument("--runs", type=Path, default=Path("runs"), help="where to look for the newest post")
    args = parser.parse_args(argv)

    draft = args.draft
    if draft is None:
        posts = [path for path in args.runs.glob("*.md") if log_order(path)[0]]
        if not posts:
            print(f"no posts in {args.runs}", file=sys.stderr)
            return 1
        draft = max(posts, key=log_order)
    print(f"post: {draft}")
    text = post_text(draft.read_text(encoding="utf-8"))
    photo = draft.with_suffix(".png")
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print("telegram: not switched on (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not both set)")
        return 0
    try:
        called = send_telegram(text, photo if photo.exists() else None, token, chat)
    except RuntimeError as error:
        print(f"telegram: failed. {error}", file=sys.stderr)
        print(
            "Check that TELEGRAM_CHAT_ID names the channel (@its_name, or a numeric id that starts "
            "with -100), not the bot, and that the bot is an administrator of that channel.",
            file=sys.stderr,
        )
        return 1
    print(f"telegram: sent ({', '.join(called)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
