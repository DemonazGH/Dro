"""The few calls to the Telegram Bot API this project needs.

Standard library only, and nothing else of the project is imported here, so
this module can be used before the simulation's dependencies are installed.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid

API = "https://api.telegram.org/bot{token}/{method}"
FILES = "https://api.telegram.org/file/bot{token}/{path}"
CAPTION_LIMIT = 1024  # Telegram's limit for the text under a photo
PAUSES_S = (5, 20, 60)  # waits before the second, third and fourth attempt
LONGEST_WAIT_S = 120  # never wait longer than this, whatever Telegram asks for


class TelegramError(RuntimeError):
    """A call that failed. ``passing`` is true when trying again later may help."""

    def __init__(self, message: str, passing: bool = False, wait_s: float | None = None):
        super().__init__(message)
        self.passing = passing
        self.wait_s = wait_s


def multipart(fields: dict[str, str], file_field: str, file_name: str, content: bytes) -> tuple[bytes, str]:
    """Encode form fields and one file as multipart/form-data."""
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_name}"\r\nContent-Type: image/png\r\n\r\n'
        ).encode()
        + content
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def call_once(token: str, method: str, body: bytes, content_type: str, opener=urllib.request.urlopen) -> dict:
    """Call one method of the Bot API, once. Errors never contain the token."""
    request = urllib.request.Request(
        API.format(token=token, method=method), data=body, headers={"Content-Type": content_type}
    )
    try:
        with opener(request, timeout=60) as response:
            answer = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        # The address holds the token, so only Telegram's own explanation is passed on.
        try:
            said = json.loads(error.read().decode() or "{}")
        except ValueError:
            said = {}
        raise TelegramError(
            f"Telegram refused {method}: {error.code}, {said.get('description', 'no explanation')}",
            # A fault on Telegram's side, or a request to slow down.
            passing=error.code >= 500 or error.code == 429,
            wait_s=(said.get("parameters") or {}).get("retry_after"),
        ) from None
    except urllib.error.URLError as error:
        raise TelegramError(f"Telegram could not be reached: {error.reason}", passing=True) from None
    if not answer.get("ok"):
        raise TelegramError(f"Telegram refused {method}: {answer.get('description', 'no explanation')}")
    return answer


def call(
    token: str, method: str, body: bytes, content_type: str, opener=urllib.request.urlopen, sleep=None
) -> dict:
    """Call one method of the Bot API, trying again when the failure may pass.

    A fault on Telegram's side (a 5xx answer), a request to slow down (429)
    and a broken connection are tried again after a pause. A refusal that
    will not change, such as a wrong chat or a bot without rights, is raised
    at once. The daily post was lost on 2026-11-20 to a single 500.
    """
    for pause in (*PAUSES_S, None):
        try:
            return call_once(token, method, body, content_type, opener)
        except TelegramError as error:
            if pause is None or not error.passing:
                raise
            (sleep or time.sleep)(min(error.wait_s or pause, LONGEST_WAIT_S))
    raise AssertionError("unreachable")


def ask(token: str, method: str, payload: dict, opener=urllib.request.urlopen):
    """Call a method with a JSON payload and return its result."""
    return call(token, method, json.dumps(payload).encode(), "application/json", opener).get("result")


def send_message(token: str, chat, text: str, opener=urllib.request.urlopen) -> None:
    ask(token, "sendMessage", {"chat_id": chat, "text": text}, opener)


def send_photo(
    token: str, chat, name: str, content: bytes, caption: str | None = None, opener=urllib.request.urlopen
) -> None:
    fields = {"chat_id": str(chat)}
    if caption:
        fields["caption"] = caption
    body, content_type = multipart(fields, "photo", name, content)
    call(token, "sendPhoto", body, content_type, opener)


def download(token: str, path: str, opener=urllib.request.urlopen) -> bytes:
    """Fetch a file that getFile pointed to."""
    try:
        with opener(urllib.request.Request(FILES.format(token=token, path=path)), timeout=60) as response:
            return response.read()
    except urllib.error.URLError:
        raise RuntimeError("a file could not be fetched from Telegram") from None
