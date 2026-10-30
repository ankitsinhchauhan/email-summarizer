from src.summarizer import summarize_text, split_into_sentences


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
    sentences = [
        f"Sentence number {i} provides detailed information about system performance."
        for i in range(1, 101)
    ]
    text = " ".join(sentences)

    summary = summarize_text(text)

    assert isinstance(summary, str)
    assert "Sentence number 1" in summary
    assert "Sentence number 2" in summary
    assert "Sentence number 3" in summary
    assert "Sentence number 4" not in summary
    assert summary.endswith(".")


def test_summarize_exactly_three_sentences():
    text = (
        "Sentence one is clear and informative. "
        "Sentence two provides essential technical context. "
        "Sentence three concludes the main point cleanly."
    )
    summary = summarize_text(text)
    assert summary == text


def test_sentence_tokenizer_protects_honorifics():
    text = "Lead Physicist Dr. Hans Zimmer demonstrated 100 logical qubits with high accuracy. Commercial testing begins soon."
    sentences = split_into_sentences(text)
    assert len(sentences) == 2
    assert "Dr. Hans Zimmer" in sentences[0]


def test_sentence_tokenizer_protects_decimals_and_abbreviations():
    text = "Inflation decelerated to 2.3% year-over-year in Sept. as noted e.g. by analysts. The benchmark rate dropped by 0.50% today."
    sentences = split_into_sentences(text)
    assert len(sentences) == 2
    assert "2.3%" in sentences[0]
    assert "Sept." in sentences[0]
    assert "0.50%" in sentences[1]


def test_sentence_tokenizer_handles_questions_and_exclamations():
    text = "Did the database crash? Yes! We detected a memory leak."
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "Did the database crash?"
    assert sentences[1] == "Yes!"
    assert sentences[2] == "We detected a memory leak."


def test_summarize_extracts_tail_action_item():
    text = (
        "Good morning everyone. The weather has been nice this week. "
        "We held our weekly operational review. "
        "All engineers must complete the mandatory security patching by 5:00 PM EST today. "
        "Unpatched nodes will be quarantined."
    )
    summary = summarize_text(text, max_length=150, min_length=30)
    # Must capture the tail action item instead of just the opening pleasantry
    assert "must complete the mandatory security patching" in summary
    assert "5:00 PM EST" in summary
    assert "Good morning everyone" not in summary


def test_summarize_extracts_middle_decision():
    text = (
        "Thank you for attending the quarterly budget meeting yesterday. "
        "The committee formally approved the revised capital budget of $450,000 for AWS cloud migration. "
        "We are continuing general planning for subsequent quarters."
    )
    summary = summarize_text(text, max_length=150, min_length=30)
    assert "formally approved" in summary
    assert "$450,000" in summary


def test_summarize_enforces_max_length_word_count():
    long_sentences = [
        f"Critical decision number {i} requires immediate deployment by the operational staff across availability zone {i}."
        for i in range(1, 25)
    ]
    text = " ".join(long_sentences)
    # Request max length of 50 words
    summary = summarize_text(text, max_length=50, min_length=20)
    word_count = len(summary.split())
    # Word count should be bounded near or at max_length (within modest boundary)
    assert word_count <= 60
    assert len(summary) > 0


def test_summarize_deduplicates_redundant_sentences():
    text = (
        "The infrastructure migration team deployed the new Kubernetes cluster today. "
        "The infrastructure migration team deployed the new Kubernetes cluster today. "
        "All tests passed with zero regressions. "
        "Operations will monitor latency overnight."
    )
    summary = summarize_text(text, max_length=150, min_length=30)
    # The duplicate sentence should not appear twice
    assert summary.count("The infrastructure migration team deployed") == 1
