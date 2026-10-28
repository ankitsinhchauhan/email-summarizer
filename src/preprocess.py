import re

_RE_URL = re.compile(r"http\S+")
_RE_WHITESPACE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = _RE_URL.sub("", text)
    text = _RE_WHITESPACE.sub(" ", text).strip()

    return text