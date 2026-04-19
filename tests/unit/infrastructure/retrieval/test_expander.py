from src.infrastructure.retrieval.expander import expand_aliases
from src.infrastructure.retrieval.normalizer import normalize_query


def test_expand_aliases_adds_token_aliases() -> None:
    expanded = expand_aliases(normalize_query('official guidance'))
    assert 'docs' in expanded.expanded_terms
    assert 'guide' in expanded.expanded_terms


def test_expand_aliases_adds_phrase_aliases() -> None:
    expanded = expand_aliases(normalize_query('kick off branch review'))
    assert 'start' in expanded.variants


def test_expand_aliases_handles_hyphen_underscore_workaround_phrase() -> None:
    expanded = expand_aliases(normalize_query('hyphens instead of underscores'))
    assert 'hyphens underscores workaround' in expanded.variants
