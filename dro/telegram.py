"""The few calls to the Telegram Bot API this project needs.

Standard library only, and nothing else of the project is imported here, so
this module can be used before the simulation's dependencies are installed.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid

API = "https://api.telegram.org/bot{token}/{method}"
FILES = "https://api.telegram.org/file/bot{token}/{path}"
CAPTION_LIMIT = 1024  # Telegram's limit for the text under a photo


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


def call(token: str, method: str, body: bytes, content_type: str, opener=urllib.request.urlopen) -> dict:
    """Call one method of the Bot API. Errors never contain the token."""
    request = urllib.request.Request(
        API.format(token=token, method=method), data=body, headers={"Content-Type": content_type}
    )
    try:
        with opener(request, timeout=60) as response:
            answer = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        # The address holds the token, so only Telegram's own explanation is passed on.
        detail = json.loads(error.read().decode() or "{}").get("description", "no explanation")
        raise RuntimeError(f"Telegram refused {method}: {error.code}, {detail}") from None
    except urllib.error.URLError as error:
        raise RuntimeError(f"Telegram could not be reached: {error.reason}") from None
    if not answer.get("ok"):
        raise RuntimeError(f"Telegram refused {method}: {answer.get('description', 'no explanation')}")
    return answer


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
