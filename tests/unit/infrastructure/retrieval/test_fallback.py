from dataclasses import dataclass

from src.infrastructure.retrieval.fallback import search_with_fallback


@dataclass(frozen=True)
class FakeObservation:
    id: str
    timestamp: int
    content: str
    metadata: dict | None = None


class FakeRepository:
    def __init__(self, mapping: dict[str, list[FakeObservation]]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    def search(self, query: str, limit: int | None = None) -> list[FakeObservation]:
        self.calls.append(query)
        return self.mapping.get(query, [])[: limit or len(self.mapping.get(query, []))]


def test_search_with_fallback_rescues_on_second_attempt() -> None:
    expected = FakeObservation(id='1', timestamp=1, content='branch review start')
    repository = FakeRepository({'kick off branch review cli session': [expected]})

    results = search_with_fallback(repository, 'how do I kick off branch review from cli sessions', 5)

    assert results == [expected]
    assert repository.calls[0] == 'how do i kick off branch review from cli sessions'


def test_search_with_fallback_uses_alias_variant() -> None:
    expected = FakeObservation(id='1', timestamp=1, content='docs guide official')
    repository = FakeRepository({'docs': [expected]})

    results = search_with_fallback(repository, 'official guidance', 5)

    assert results == [expected]


def test_search_with_fallback_uses_intention_suffix() -> None:
    expected = FakeObservation(id='1', timestamp=1, content='docs guide official reference policy')
    repository = FakeRepository({'official guidance docs guide official reference policy': [expected]})

    results = search_with_fallback(repository, 'official guidance', 5)

    assert results == [expected]
