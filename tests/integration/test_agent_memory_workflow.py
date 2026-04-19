"""Integration tests for Agent + Memory workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.services.memory_service import MemoryService
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


@pytest.fixture
def db_connection(tmp_path: Path) -> DatabaseConnection:
    db_path = tmp_path / "test_memory.db"
    config = DatabaseConfig(db_path=db_path)
    migrations_dir = (
        Path(__file__).parent.parent.parent / "src/infrastructure/persistence/migrations"
    )
    run_migrations(config, migrations_dir)
    return DatabaseConnection(config)


@pytest.fixture
def observation_repository(db_connection: DatabaseConnection) -> ObservationRepository:
    return ObservationRepository(db_connection)


@pytest.fixture
def memory_service(observation_repository: ObservationRepository) -> MemoryService:
    return MemoryService(repository=observation_repository)


@pytest.fixture
def orchestrator() -> TmuxOrchestrator:
    return TmuxOrchestrator(safety_mode=False)


class TestAgentMemoryWorkflow:
    def test_agent_saves_observation(self, memory_service: MemoryService) -> None:
        obs = memory_service.save(
            content="Analicé el código de auth.py - tiene 3 funciones principales",
            metadata={"agent": "agent-1", "file": "auth.py"},
        )

        assert obs.id is not None
        assert obs.content == "Analicé el código de auth.py - tiene 3 funciones principales"
        assert obs.metadata is not None
        assert obs.metadata.get("agent") == "agent-1"

    def test_agent_searches_observations(self, memory_service: MemoryService) -> None:
        memory_service.save(
            content="Analicé auth.py",
            metadata={"agent": "agent-1"},
        )
        memory_service.save(
            content="Revisé user.py para",
            metadata={"agent": "agent-1"},
        )
        memory_service.save(
            content="Analicé database.py",
            metadata={"agent": "agent-2"},
        )

        results = memory_service.search("auth")

        assert len(results) >= 1
        assert any("auth" in obs.content.lower() for obs in results)

    def test_multiple_agents_save_and_retrieve(self, memory_service: MemoryService) -> None:
        memory_service.save(
            content="Implementé autenticación JWT en auth.py",
            metadata={"agent": "agent-1", "role": "backend"},
        )
        memory_service.save(
            content="Creé componente de login en React",
            metadata={"agent": "agent-2", "role": "frontend"},
        )
        memory_service.save(
            content="Configuré pipeline de CI/CD",
            metadata={"agent": "agent-3", "role": "devops"},
        )

        all_obs = memory_service.get_recent(limit=10)
        assert len(all_obs) == 3

        agent1_obs = memory_service.search("autenticación")
        assert len(agent1_obs) >= 1

        agent2_obs = memory_service.search("login")
        assert len(agent2_obs) >= 1

        agent3_obs = memory_service.search("pipeline")
        assert len(agent3_obs) >= 1

    def test_complete_agent_collaboration_flow(
        self,
        memory_service: MemoryService,
        orchestrator: TmuxOrchestrator,
    ) -> None:
        obs1 = memory_service.save(
            content="Encontré 3 vulnerabilidades en auth.py: XSS, CSRF, SQLi",
            metadata={"agent": "agent-1", "phase": "analysis"},
        )

        memory_service.save(
            content="Confirmo las vulnerabilidades - prioridad alta",
            metadata={"agent": "agent-2", "phase": "review"},
        )

        orchestrator.create_session("agent_1_session")

        try:
            sessions = orchestrator.get_sessions()
            agent1 = next(s for s in sessions if s.name == "agent_1_session")
            assert agent1 is not None

            obs3 = memory_service.save(
                content="Corregí SQL injection usando prepared statements",
                metadata={
                    "agent": "agent-3",
                    "phase": "fix",
                    "related_to": obs1.id,
                },
            )

            all_recent = memory_service.get_recent(limit=10)
            assert len(all_recent) >= 3

            fix_obs = memory_service.get_by_id(obs3.id)
            assert fix_obs.metadata is not None
            assert fix_obs.metadata.get("related_to") == obs1.id

        finally:
            orchestrator.kill_session("agent_1_session")


class TestAgentContextPreservation:
    def test_agent_resumes_work_from_memory(self, memory_service: MemoryService) -> None:
        memory_service.save(
            content="Working on feature X - need to implement Y tomorrow",
            metadata={"agent": "agent-1", "status": "in_progress"},
        )
        memory_service.save(
            content="TODO: Fix the bug in auth.py line 42",
            metadata={"agent": "agent-1", "status": "pending"},
        )

        pending = memory_service.search("TODO")
        assert len(pending) >= 1
        assert "TODO" in pending[0].content

    def test_cross_agent_context_sharing(self, memory_service: MemoryService) -> None:
        memory_service.save(
            content="API response format: {status: string, data: object}",
            metadata={"agent": "agent-1", "category": "context"},
        )

        api_context = memory_service.search("API")
        assert len(api_context) >= 1
        assert "API" in api_context[0].content
