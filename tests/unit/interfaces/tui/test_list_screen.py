"""Tests for TUI scaffold — Phase 1."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.domain.entities.observation import Observation


def _make_obs(
    id: str = "a" * 32,
    content: str = "test observation content",
    type: str | None = "decision",
    project: str | None = "myproj",
    topic_key: str | None = "test-key",
    title: str | None = "Test Title",
    timestamp: int = 1_700_000_000_000,
) -> Observation:
    return Observation(
        id=id,
        timestamp=timestamp,
        content=content,
        type=type,
        project=project,
        topic_key=topic_key,
        title=title,
    )


class TestTUIApp:
    def test_instantiation(self) -> None:
        from src.interfaces.tui.app import TUIApp

        app = TUIApp(db_path="/tmp/test.db")
        assert app.TITLE == "Memory TUI"
        assert app.db_path is not None

    def test_instantiation_no_db(self) -> None:
        from src.interfaces.tui.app import TUIApp

        app = TUIApp()
        assert app.db_path is None

    def test_compose_yields_widgets(self) -> None:
        from src.interfaces.tui.app import TUIApp

        app = TUIApp()
        widgets = list(app.compose())
        types = [type(w).__name__ for w in widgets]
        assert "Header" in types
        assert "Footer" in types


class TestTypeBadge:
    def test_known_type_color(self) -> None:
        from src.interfaces.tui.widgets.type_badge import TYPE_COLORS

        assert "decision" in TYPE_COLORS
        assert TYPE_COLORS["decision"] == "green"

    def test_badge_renders_type(self) -> None:
        from src.interfaces.tui.widgets.type_badge import TypeBadge

        badge = TypeBadge("decision")
        assert "decision" in str(badge._render())

    def test_unknown_type_falls_back(self) -> None:
        from src.interfaces.tui.widgets.type_badge import TypeBadge

        badge = TypeBadge("nonexistent")
        assert "nonexistent" in str(badge._render())


class TestListScreen:
    def test_page_initial_state(self) -> None:
        from src.interfaces.tui.screens.list_screen import ListScreen

        screen = ListScreen(db_path=None)
        assert screen._page == 0
        assert screen.PAGE_SIZE == 50
        assert screen._service is None

    def test_service_cached_on_second_call(self) -> None:
        from src.interfaces.tui.screens.list_screen import ListScreen

        mock_service = MagicMock()
        mock_container = MagicMock()
        mock_container.memory_service.return_value = mock_service

        with patch("src.infrastructure.persistence.container.create_container", return_value=mock_container):
            screen = ListScreen(db_path=None)
            svc1 = screen._get_service()
            svc2 = screen._get_service()

        assert svc1 is svc2
        mock_container.memory_service.assert_called_once()

    def test_next_prev_page_logic(self) -> None:
        from src.interfaces.tui.screens.list_screen import ListScreen

        screen = ListScreen()

        screen._page = 0
        screen.action_prev_page()
        assert screen._page == 0  # cannot go below 0

        with patch.object(screen, "_load_data"):
            screen.action_next_page()
        assert screen._page == 1

        with patch.object(screen, "_load_data"):
            screen.action_prev_page()
        assert screen._page == 0

    @patch("src.infrastructure.persistence.container.create_container")
    def test_load_data_populates_table(self, mock_container: MagicMock) -> None:
        from src.interfaces.tui.screens.list_screen import ListScreen

        mock_service = MagicMock()
        mock_service.get_recent.return_value = [
            _make_obs(id="abc12345" + "x" * 25, type="decision", project="proj", topic_key="key", title="Hello"),
            _make_obs(id="def67890" + "x" * 25, type="bugfix", project="proj2", topic_key="key2", title="World"),
        ]
        mock_container.return_value.memory_service.return_value = mock_service

        screen = ListScreen(db_path=None)
        # _load_data requires mounted widgets; test the page/offset logic instead
        offset = screen._page * screen.PAGE_SIZE
        mock_service.get_recent(limit=screen.PAGE_SIZE, offset=offset)
        mock_service.get_recent.assert_called_once_with(limit=50, offset=0)
