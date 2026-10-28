from src.preprocess import clean_text


def summarize_text(
    text: str,
    max_length: int = 150,
    min_length: int = 30
) -> str:
    cleaned_text = clean_text(text)

    if len(cleaned_text) < 100:
        return "Text is too short to summarize."

    # Split at most 3 times to find the first 3 sentences without allocating
    # hundreds of thousands of sentence strings for large documents.
    sentences = cleaned_text.split(". ", 3)

    if len(sentences) <= 3:
        return cleaned_text

    summary = ". ".join(sentences[:3])

    if not summary.endswith("."):
        summary += "."

    return summary