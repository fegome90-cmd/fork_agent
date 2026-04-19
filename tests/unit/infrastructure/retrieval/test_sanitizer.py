from src.infrastructure.retrieval.sanitizer import sanitize_fts5


def test_sanitize_fts5_removes_punctuation_and_reserved_words() -> None:
    assert sanitize_fts5('gemini faster than claude workers? AND NOT') == 'gemini faster than claude workers'


def test_sanitize_fts5_normalizes_hyphens_and_underscores() -> None:
    assert sanitize_fts5('before_agent-start foo_bar') == 'before agent start foo bar'


def test_sanitize_fts5_empty_safe() -> None:
    assert sanitize_fts5('   ') == ''
