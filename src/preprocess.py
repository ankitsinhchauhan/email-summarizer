import re
import unicodedata

# Matches http, https, and www URLs
_RE_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)

# Matches multiple inline horizontal spaces (tabs, non-breaking spaces)
_RE_INLINE_SPACES = re.compile(r"[^\S\r\n]+")

# Conservative greeting pattern at the start of document or first line
# e.g., "Hi Team,", "Dear Alexander,", "Good morning executives,", "Hello everyone:"
_RE_SALUTATION = re.compile(
    r"^(?:\s*(?:hi|hello|hey|dear|good\s+(?:morning|afternoon|evening)|attention\s+all(?:\s+\w+)*|greetings)"
    r"[\s,:\-][^\n.!?]{0,80}(?:[,\-:]|\n))(?:\s*\n+)?",
    re.IGNORECASE
)

# Conservative signature pattern at the end of document
# e.g., "Best regards,\nJane Doe", "Sincerely,\nTeam", "Thanks,\nAlex"
_RE_SIGNATURE = re.compile(
    r"(?:\n\s*(?:--\s*\n|best\s+regards|warm\s+regards|kind\s+regards|regards|sincerely|thanks|thank\s+you|cheers|best|respectfully|yours\s+truly)[,\s]*\n+[\s\S]{1,150}$)",
    re.IGNORECASE
)

# Common bullet markers to normalize
_RE_BULLETS = re.compile(r"^[\s\t]*[\u2022\u2023\u25cf\u25cb\u25aa\u25ba\*\-]\s*", re.MULTILINE)


def strip_salutations(text: str) -> str:
    """Remove standard email opening salutations without deleting substantive text."""
    if not text:
        return ""
    cleaned = _RE_SALUTATION.sub("", text).strip()
    return cleaned if cleaned else text


def strip_signatures(text: str) -> str:
    """Remove common trailing email sign-offs and signature blocks."""
    if not text:
        return ""
    cleaned = _RE_SIGNATURE.sub("", text).rstrip()
    return cleaned if cleaned else text


def clean_text(text: str, strip_envelope: bool = True) -> str:
    """Sanitize and clean text by normalizing whitespace, removing URLs,
    and conservatively stripping email salutations and signatures.
    
    Preserves meaningful paragraph boundaries while normalizing intra-paragraph wrapping.
    """
    if not text or not isinstance(text, str):
        return ""

    # Normalize Unicode characters (NFKC) and strip zero-width formatting artifacts
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    # Normalize carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove URLs cleanly without leaving awkward double spaces
    text = _RE_URL.sub("", text)

    # Normalize bullet list markers
    text = _RE_BULLETS.sub("- ", text)

    # Conservatively strip salutations and signatures
    if strip_envelope:
        text = strip_salutations(text)
        text = strip_signatures(text)

    # Split into paragraphs by double newlines
    raw_paragraphs = re.split(r"\n{2,}", text)
    cleaned_paragraphs = []

    for para in raw_paragraphs:
        # Collapse soft line breaks inside a paragraph into a single space
        para = _RE_INLINE_SPACES.sub(" ", para)
        para = re.sub(r"\n+", " ", para)
        para = re.sub(r" +", " ", para).strip()
        if para:
            cleaned_paragraphs.append(para)

    # Rejoin paragraphs with standard double newline if multi-paragraph, or space
    if len(cleaned_paragraphs) <= 1:
        return cleaned_paragraphs[0] if cleaned_paragraphs else ""

    return "\n\n".join(cleaned_paragraphs)
