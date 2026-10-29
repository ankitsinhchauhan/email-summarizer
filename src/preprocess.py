import re

<<<<<<< HEAD
_RE_URL = re.compile(r"http\S+")
_RE_WHITESPACE = re.compile(r"\s+")


=======
>>>>>>> origin/main
def clean_text(text: str) -> str:
    if not text:
        return ""

<<<<<<< HEAD
    text = _RE_URL.sub("", text)
    text = _RE_WHITESPACE.sub(" ", text).strip()
=======
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[\r\n]+", " ", text)
>>>>>>> origin/main

    return text