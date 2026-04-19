from src.domain.entities.observation import Observation
from src.infrastructure.retrieval.reranker import detect_intention, rerank_by_intention


def _observation(obs_id: str, obs_type: str, origin_hint: str = '', status: str = '', stability: str = '') -> Observation:
    return Observation(
        id=obs_id,
        timestamp=1,
        content=f'{obs_type} content',
        metadata={
            'type': obs_type,
            'origin_hint': origin_hint,
            'status': status,
            'stability': stability,
        },
    )


def test_detect_intention_identifies_official_queries() -> None:
    assert detect_intention('official guidance beat memory notes') == 'official'


def test_rerank_by_intention_boosts_official_docs_reference() -> None:
    results = [
        _observation('1', 'learning', origin_hint='memory/2026-03-08.md'),
        _observation('2', 'reference', origin_hint='docs/retrieval.md', status='current', stability='canonical'),
    ]
    reranked = rerank_by_intention(results, 'official', 'official guidance beat memory notes')
    assert reranked[0].id == '2'


def test_rerank_by_intention_boosts_historical_memory_discovery() -> None:
    results = [
        _observation('1', 'reference', origin_hint='docs/file.md'),
        _observation('2', 'discovery', origin_hint='memory/2026-03-02.md'),
    ]
    reranked = rerank_by_intention(results, 'historical', 'why paths get hyphens instead of underscores')
    assert reranked[0].id == '2'


def test_rerank_by_intention_boosts_operational_procedure() -> None:
    results = [
        _observation('1', 'reference'),
        _observation('2', 'procedure', status='active', stability='stable'),
    ]
    reranked = rerank_by_intention(results, 'operational', 'how do I kick off branch review from cli')
    assert reranked[0].id == '2'
