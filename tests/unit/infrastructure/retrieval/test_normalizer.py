from src.infrastructure.retrieval.normalizer import normalize_query


def test_normalize_query_removes_stopwords_and_singularizes() -> None:
    normalized = normalize_query("how do I kick off branch review from cli sessions")
    assert normalized.keywords == ("kick", "off", "branch", "review", "cli", "session")
    assert normalized.simplified == "kick off branch review cli session"


def test_normalize_query_normalizes_accents() -> None:
    normalized = normalize_query("como está la configuración de memoria")
    assert "configuracion" in normalized.sanitized
    assert "memoria" in normalized.keywords
