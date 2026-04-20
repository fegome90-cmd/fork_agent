"""Unit tests for ObservationRepository Protocol — new methods."""

from __future__ import annotations

import inspect

from src.domain.ports.observation_repository import ObservationRepository


class TestUpdateMethod:
    """Protocol must define update() method accepting an Observation entity."""

    def test_has_update_method(self) -> None:
        assert hasattr(ObservationRepository, "update")

    def test_update_signature_has_observation_param(self) -> None:
        sig = inspect.signature(ObservationRepository.update)
        assert "observation" in sig.parameters

    def test_update_returns_none(self) -> None:
        sig = inspect.signature(ObservationRepository.update)
        assert sig.return_annotation == "None"


class TestGetByTopicKey:
    """Protocol must define get_by_topic_key() method."""

    def test_has_get_by_topic_key_method(self) -> None:
        assert hasattr(ObservationRepository, "get_by_topic_key")

    def test_get_by_topic_key_takes_topic_key_param(self) -> None:
        sig = inspect.signature(ObservationRepository.get_by_topic_key)
        assert "topic_key" in sig.parameters

    def test_get_by_topic_key_takes_project_param(self) -> None:
        sig = inspect.signature(ObservationRepository.get_by_topic_key)
        assert "project" in sig.parameters

    def test_get_by_topic_key_returns_optional_observation(self) -> None:
        sig = inspect.signature(ObservationRepository.get_by_topic_key)
        assert sig.return_annotation == "Observation | None"


class TestUpsertTopicKey:
    """Protocol must define upsert_topic_key() method."""

    def test_has_upsert_topic_key_method(self) -> None:
        assert hasattr(ObservationRepository, "upsert_topic_key")

    def test_upsert_topic_key_takes_observation(self) -> None:
        sig = inspect.signature(ObservationRepository.upsert_topic_key)
        assert "observation" in sig.parameters

    def test_upsert_topic_key_returns_observation(self) -> None:
        sig = inspect.signature(ObservationRepository.upsert_topic_key)
        assert sig.return_annotation == "Observation"


class TestGetAllWithTypeFilter:
    """get_all() must accept optional type parameter."""

    def test_get_all_has_type_param(self) -> None:
        sig = inspect.signature(ObservationRepository.get_all)
        assert "type" in sig.parameters

    def test_get_all_type_defaults_to_none(self) -> None:
        sig = inspect.signature(ObservationRepository.get_all)
        type_param = sig.parameters["type"]
        assert type_param.default is None


class TestGetBySessionId:
    """Protocol must define get_by_session_id() method."""

    def test_has_get_by_session_id_method(self) -> None:
        assert hasattr(ObservationRepository, "get_by_session_id")

    def test_get_by_session_id_takes_session_id_param(self) -> None:
        sig = inspect.signature(ObservationRepository.get_by_session_id)
        assert "session_id" in sig.parameters

    def test_get_by_session_id_takes_project_param(self) -> None:
        sig = inspect.signature(ObservationRepository.get_by_session_id)
        assert "project" in sig.parameters

    def test_get_by_session_id_returns_list_of_observations(self) -> None:
        sig = inspect.signature(ObservationRepository.get_by_session_id)
        assert sig.return_annotation == "list[Observation]"
