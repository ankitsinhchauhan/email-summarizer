from src.preprocess import clean_text


def test_clean_text_removes_extra_spaces():
    text = "Hello     World"
    result = clean_text(text)

    assert result == "Hello World"


def test_clean_text_removes_urls():
    text = "Visit http://google.com now"
    result = clean_text(text)

    assert "http" not in result


def test_clean_text_removes_newlines():
    text = "Hello\nWorld"
    result = clean_text(text)

    assert result == "Hello World"


def test_clean_text_empty_input():
    result = clean_text("")

    assert result == ""