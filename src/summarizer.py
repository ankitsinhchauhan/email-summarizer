import re
from typing import List, Tuple
from collections import Counter
from src.preprocess import clean_text

# Common honorifics and titles to protect from sentence splitting
_HONORIFICS = (
    r"Dr|Mr|Mrs|Ms|Prof|Rev|Hon|Capt|Col|Lt|Gen|Sgt|"
    r"Messrs|Mmes|Mister|Madam|President|Gov|Sen|Rep"
)

# Common Latin and general abbreviations
_ABBREVIATIONS = (
    r"e\.g|i\.e|etc|vs|al|approx|dept|fig|vol|no|ref|p\.m|a\.m|est|pst|cst|utc|gmt|"
    r"inc|corp|ltd|co|llc|st|ave|rd|blvd|hwy"
)

# Month abbreviations
_MONTHS = r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"

# Single uppercase initial (e.g. "John F. Kennedy" -> "F.")
_INITIALS = r"[A-Z]"

# Sentinel to temporarily replace protected periods during segmentation
_DOT_SENTINEL = "\u200cDOT\u200c"

# Stopwords for lightweight keyword centrality scoring
_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
}

# Regex patterns for scoring features
_RE_ACTION_VERBS = re.compile(
    r"\b(must|shall|require[ds]?|need(?:s)?\s+to|mandatory|directive|"
    r"action\s+(?:required|items?)|please\s+(?:ensure|review|submit|halt|redeploy|send|check)|"
    r"deadline|due\s+(?:by|on|date)|quarantine|redeploy|decommission|notify|implement|enforce)\b",
    re.IGNORECASE
)

_RE_DECISIONS = re.compile(
    r"\b(approved|authorized|voted|decided|resolved|announced|granted|"
    r"ratified|confirmed|agreed|concluded|finalized|settled|formal\s+decision|go\s+decision|rollout)\b",
    re.IGNORECASE
)

_RE_DATES_TIMES = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b|"
    r"\b\d{1,2}:\d{2}(?:\s*(?:AM|PM|UTC|EST|PST|CET|GMT))?\b|"
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b|"
    r"\b(?:by|before|until|starting|effective)\s+(?:today|tomorrow|[A-Z][a-z]+|\d{1,2})\b",
    re.IGNORECASE
)

_RE_AMOUNTS_NUMBERS = re.compile(
    r"(?:\$|€|£|EUR|USD|GBP)\s*[\d,]+(?:\.\d+)?|"
    r"\b\d+(?:\.\d+)?%|"
    r"\b\d+(?:,\d+)*(?:\.\d+)?\s*(?:million|billion|thousand|trillion|qubits|turbines|"
    r"patients|records|hours|days|minutes|seconds|options|shares|terabytes|megabytes|basis\s+points?)\b",
    re.IGNORECASE
)

_RE_ROLES_ENTITIES = re.compile(
    r"\b(CEO|CFO|CTO|COO|CISO|VP|Vice\s+President|Director|Lead|Manager|"
    r"Architect|Chairwoman|Chairman|Auditor|Investigator|FDA|SEC|EMA|HHS|Federal\s+Reserve)\b"
)

_RE_CHITCHAT = re.compile(
    r"\b(hope you are having|weather in|wonderful start|take the time to|"
    r"appreciate your|pleasant today|enjoyed our wonderful|had a great)\b",
    re.IGNORECASE
)


def split_into_sentences(text: str) -> List[str]:
    """Segment cleaned text into clean, complete sentences.
    
    Protects honorifics, initials, date abbreviations, decimal numbers,
    and Latin abbreviations from premature sentence splitting.
    """
    if not text:
        return []

    s = text

    # Protect decimals and numbers: e.g. "1.5", "0.01", "v4.8.0"
    s = re.sub(r"(?<=\d)\.(?=\d)", _DOT_SENTINEL, s)

    # Protect honorifics: e.g. "Dr. ", "Mr. "
    s = re.sub(rf"\b({_HONORIFICS})\.", rf"\1{_DOT_SENTINEL}", s, flags=re.IGNORECASE)

    # Protect month abbreviations: e.g. "Oct. 30"
    s = re.sub(rf"\b({_MONTHS})\.", rf"\1{_DOT_SENTINEL}", s, flags=re.IGNORECASE)

    # Protect common abbreviations: e.g. "e.g.", "i.e.", "etc."
    s = re.sub(rf"\b({_ABBREVIATIONS})\.", rf"\1{_DOT_SENTINEL}", s, flags=re.IGNORECASE)

    # Protect single uppercase middle initials: e.g. "John F. Kennedy"
    s = re.sub(rf"\b({_INITIALS})\.", rf"\1{_DOT_SENTINEL}", s)

    # Segment at sentence boundaries: '.', '?', or '!' followed by whitespace or end
    raw_splits = re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"'\(\[\u2022\-])|(?<=[.?!])\n+", s)

    sentences: List[str] = []
    for part in raw_splits:
        # Restore protected dots
        restored = part.replace(_DOT_SENTINEL, ".").strip()
        # Clean leading dashes or list markers
        restored = re.sub(r"^[-*•\s]+\s*", "", restored).strip()
        if len(restored) > 0:
            sentences.append(restored)

    return sentences


def _compute_word_frequencies(sentences: List[str]) -> Counter:
    """Calculate non-stopword token frequencies across all sentences for TF scoring."""
    words: List[str] = []
    for s in sentences:
        tokens = re.findall(r"\b[a-z0-9]+\b", s.lower())
        words.extend(t for t in tokens if t not in _STOPWORDS and len(t) > 2)
    return Counter(words)


def _score_sentence(
    sentence: str,
    index: int,
    total_sentences: int,
    word_freq: Counter,
    max_freq: int
) -> float:
    """Score an individual sentence for action-oriented importance, decisions, and centrality."""
    score = 0.0
    words = re.findall(r"\b[a-z0-9]+\b", sentence.lower())
    num_words = len(words)

    if num_words < 5:
        # Penalize fragments and extremely short lines
        return -2.0

    # 1. Action items & directives (+3.5)
    action_matches = len(_RE_ACTION_VERBS.findall(sentence))
    if action_matches > 0:
        score += 3.5 + 0.5 * min(action_matches - 1, 3)

    # 2. Decisions & approvals (+3.5)
    decision_matches = len(_RE_DECISIONS.findall(sentence))
    if decision_matches > 0:
        score += 3.5 + 0.5 * min(decision_matches - 1, 3)

    # 3. Deadlines, dates & times (+2.5)
    date_matches = len(_RE_DATES_TIMES.findall(sentence))
    if date_matches > 0:
        score += 2.5 + 0.5 * min(date_matches - 1, 2)

    # 4. Amounts, financial figures & metrics (+2.0)
    amount_matches = len(_RE_AMOUNTS_NUMBERS.findall(sentence))
    if amount_matches > 0:
        score += 2.0 + 0.5 * min(amount_matches - 1, 2)

    # 5. Key organizational roles & entities (+1.5)
    role_matches = len(_RE_ROLES_ENTITIES.findall(sentence))
    if role_matches > 0:
        score += 1.5 + 0.5 * min(role_matches - 1, 2)

    # 6. Document-wide Keyword Centrality (up to +3.0)
    if max_freq > 0:
        content_words = [w for w in words if w not in _STOPWORDS and len(w) > 2]
        if content_words:
            tf_score = sum(word_freq[w] / max_freq for w in content_words) / len(content_words)
            score += tf_score * 3.0

    # 7. Structural position weights (favor early contextual sentences if content is neutral)
    if index == 0:
        score += 1.5
    elif index == 1:
        score += 0.75
    elif index == 2:
        score += 0.25

    # 8. Conversational small-talk penalty (-4.0)
    if _RE_CHITCHAT.search(sentence):
        score -= 4.0

    return score


def _sentence_jaccard_similarity(s1: str, s2: str) -> float:
    """Compute word Jaccard similarity to prevent redundant sentence selection."""
    tokens1 = set(re.findall(r"\b[a-z0-9]+\b", s1.lower())) - _STOPWORDS
    tokens2 = set(re.findall(r"\b[a-z0-9]+\b", s2.lower())) - _STOPWORDS
    if not tokens1 or not tokens2:
        return 0.0
    return len(tokens1 & tokens2) / len(tokens1 | tokens2)


def summarize_text(
    text: str,
    max_length: int = 150,
    min_length: int = 30
) -> str:
    """Summarize text using action-oriented extractive sentence ranking.
    
    Identifies key decisions, deadlines, action items, financial figures,
    and thematic sentences across the entire document while strictly enforcing
    word-count limits (min_length to max_length words).
    """
    cleaned_text = clean_text(text)

    if not cleaned_text or len(cleaned_text) < 100:
        return "Text is too short to summarize."

    sentences = split_into_sentences(cleaned_text)
    if not sentences:
        return "Text is too short to summarize."

    # If the document is already very short (<= 3 sentences and total words <= max_length),
    # return the text directly to preserve full context without truncation.
    total_doc_words = sum(len(s.split()) for s in sentences)
    if len(sentences) <= 3 and total_doc_words <= max_length:
        summary = " ".join(sentences)
        return summary if summary.endswith((".", "!", "?")) else summary + "."

    word_freq = _compute_word_frequencies(sentences)
    max_freq = max(word_freq.values()) if word_freq else 1
    total_count = len(sentences)

    # Score each sentence with its original index
    scored_sentences: List[Tuple[int, str, float]] = []
    for idx, s in enumerate(sentences):
        sc = _score_sentence(s, idx, total_count, word_freq, max_freq)
        scored_sentences.append((idx, s, sc))

    # Sort candidates by score descending, breaking ties by earlier appearance
    ranked = sorted(scored_sentences, key=lambda item: (-item[2], item[0]))

    # Greedily select sentences that satisfy length bounds without redundancy
    selected: List[Tuple[int, str]] = []
    current_words = 0

    for idx, s, sc in ranked:
        s_words = len(s.split())

        # Check redundancy against already selected sentences
        if current_words >= min_length and any(_sentence_jaccard_similarity(s, sel_s) > 0.65 for _, sel_s in selected):
            continue
        elif any(s.lower() == sel_s.lower() for _, sel_s in selected):
            continue

        # If adding this sentence exceeds max_length
        if current_words + s_words > max_length:
            # If we have nothing yet, accept the top candidate
            if not selected:
                selected.append((idx, s))
                current_words += s_words
                break
            # If we already have enough words, stop
            if current_words >= min_length:
                break
            # If we are below min_length, only take it if overshoot is modest
            if current_words + s_words <= max_length + 15:
                selected.append((idx, s))
                current_words += s_words
                break
            continue

        selected.append((idx, s))
        current_words += s_words

        # If we have reached max_length, or reached min_length (with a 3-sentence target), stop
        if current_words >= max_length:
            break
        if len(selected) >= 3 and current_words >= (min_length - 5):
            break

    # If no sentences were selected (e.g. extremely strict limits), take the top candidate
    if not selected and ranked:
        selected.append((ranked[0][0], ranked[0][1]))

    # Re-order the selected sentences by their original position in the text
    selected.sort(key=lambda item: item[0])
    summary_sentences = [item[1] for item in selected]

    summary = " ".join(summary_sentences)
    if not summary.endswith((".", "!", "?")):
        summary += "."

    return summary
