from src.summarizer import summarize_text


def test_summarize_text_returns_summary():
    text = """
    Artificial Intelligence is transforming industries by automating tasks
    and improving efficiency. Many companies are adopting AI technologies
    for better productivity and decision making.
    """

    summary = summarize_text(text)

    assert isinstance(summary, str)
    assert len(summary) > 0


def test_summarize_short_text():
    text = "Hello"

    summary = summarize_text(text)

    assert summary == "Text is too short to summarize."


def test_summarize_large_text_bounded_split():
    # Long text with 100 sentences
    sentences = [f"Sentence number {i} provides detailed information about system performance." for i in range(1, 101)]
    text = " ".join(sentences)

    summary = summarize_text(text)

    assert isinstance(summary, str)
    assert "Sentence number 1" in summary
    assert "Sentence number 2" in summary
    assert "Sentence number 3" in summary
    assert "Sentence number 4" not in summary
    assert summary.endswith(".")


def test_summarize_exactly_three_sentences():
    text = "Sentence one is clear and informative. Sentence two provides essential technical context. Sentence three concludes the main point cleanly."
    summary = summarize_text(text)
    assert summary == text