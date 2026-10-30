from src.preprocess import clean_text, strip_salutations, strip_signatures


def test_clean_text_removes_extra_spaces():
    text = "Hello     World"
    result = clean_text(text)
    assert result == "Hello World"


def test_clean_text_removes_urls():
    text = "Visit http://google.com now"
    result = clean_text(text)
    assert "http" not in result
    assert result == "Visit now"


def test_clean_text_multiple_urls():
    text = "Check http://example.com/one and https://test.org/two for details"
    result = clean_text(text)
    assert "http" not in result
    assert result == "Check and for details"


def test_clean_text_removes_newlines():
    text = "Hello\nWorld"
    result = clean_text(text)
    assert result == "Hello World"


def test_clean_text_preserves_paragraphs():
    text = "First paragraph here.\n\nSecond paragraph content."
    result = clean_text(text)
    assert "First paragraph here." in result
    assert "Second paragraph content." in result
    assert "\n\n" in result


def test_clean_text_strips_salutations():
    text = "Hi Team,\nWe detected a critical bug in production."
    result = clean_text(text)
    assert result.startswith("We detected a critical bug")
    assert "Hi Team" not in result


def test_clean_text_strips_dear_salutation():
    text = "Dear Alexander,\nWe are thrilled to extend an offer."
    result = clean_text(text)
    assert result.startswith("We are thrilled to extend an offer")
    assert "Dear Alexander" not in result


def test_clean_text_strips_signatures():
    text = "Please submit the report by Friday.\n\nBest regards,\nJohn Doe\nVP Engineering"
    result = clean_text(text)
    assert "Please submit the report by Friday." in result
    assert "Best regards" not in result
    assert "John Doe" not in result


def test_clean_text_normalizes_bullet_points():
    text = "Action items:\n• Complete security audit\n* Review architecture\n- Deploy updates"
    result = clean_text(text)
    assert "Complete security audit" in result
    assert "Review architecture" in result
    assert "Deploy updates" in result


def test_clean_text_unicode_normalization():
    # Non-breaking space \u00a0 and full-width characters
    text = "System\u00a0performance is\u200b stable."
    result = clean_text(text)
    assert result == "System performance is stable."


def test_clean_text_empty_input():
    result = clean_text("")
    assert result == ""


def test_clean_text_none_input():
    result = clean_text(None)
    assert result == ""


def test_clean_text_whitespace_only():
    result = clean_text("   \r\n\t   ")
    assert result == ""
