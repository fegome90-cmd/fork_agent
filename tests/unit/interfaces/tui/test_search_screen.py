"""Tests for SearchScreen."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.domain.entities.observation import Observation


def _make_obs(
    id: str = "a" * 32,
    content: str = "test content",
    type: str | None = "decision",
    project: str | None = "proj",
    topic_key: str | None = "key",
    title: str | None = "Title",
) -> Observation:
    return Observation(
        id=id,
        timestamp=1_700_000_000_000,
        content=content,
        type=type,
        project=project,
        topic_key=topic_key,
        title=title,
    )


class TestSearchScreen:
    def test_instantiation_with_query(self) -> None:
        from src.interfaces.tui.screens.search_screen import SearchScreen

        screen = SearchScreen(db_path=None, initial_query="test")
        assert screen._initial_query == "test"

    def test_instantiation_without_query(self) -> None:
        from src.interfaces.tui.screens.search_screen import SearchScreen

        screen = SearchScreen(db_path=None)
        assert screen._initial_query == ""

    def test_service_cached(self) -> None:
        from src.interfaces.tui.screens.search_screen import SearchScreen

        mock_service = MagicMock()
        mock_container = MagicMock()
        mock_container.memory_service.return_value = mock_service

        with patch(
            "src.infrastructure.persistence.container.create_container",
            return_value=mock_container,
        ):
            screen = SearchScreen(db_path=None)
            svc1 = screen._get_service()
            svc2 = screen._get_service()

        assert svc1 is svc2

    def test_do_search_calls_service(self) -> None:
        from src.interfaces.tui.screens.search_screen import SearchScreen

        mock_service = MagicMock()
        mock_service.search.return_value = [
            _make_obs(id="a" * 32, type="decision"),
        ]

        screen = SearchScreen(db_path=None)
        screen._service = mock_service
        screen._result_ids = []

        mock_table = MagicMock()
        mock_static = MagicMock()

        with patch.object(
            screen,
            "query_one",
            side_effect=lambda s, _w=None: {
                "#search-input": MagicMock(value="hello"),
                "#type-filter": MagicMock(value=""),
                "#project-filter": MagicMock(value=""),
                "#search-results": mock_table,
                "#search-status": mock_static,
            }.get(s if isinstance(s, str) else "", MagicMock()),
        ):
            screen._do_search()

        mock_service.search.assert_called_once_with("hello", limit=100, project=None)

    def test_do_search_empty_query_no_op(self) -> None:
        from src.interfaces.tui.screens.search_screen import SearchScreen

        mock_service = MagicMock()
        screen = SearchScreen(db_path=None)
        screen._service = mock_service

        mock_static = MagicMock()

        with patch.object(
            screen,
            "query_one",
            side_effect=lambda s, _w=None: {
                "#search-input": MagicMock(value="  "),
                "#type-filter": MagicMock(value=""),
                "#project-filter": MagicMock(value=""),
                "#search-status": mock_static,
            }.get(s if isinstance(s, str) else "", MagicMock()),
        ):
            screen._do_search()

        mock_service.search.assert_not_called()

    def test_type_filter_post_filters(self) -> None:
        from src.interfaces.tui.screens.search_screen import SearchScreen

        mock_service = MagicMock()
        mock_service.search.return_value = [
            _make_obs(id="a" * 32, type="decision"),
            _make_obs(id="b" * 32, type="bugfix"),
        ]

        screen = SearchScreen(db_path=None)
        screen._service = mock_service
        screen._result_ids = []

        mock_table = MagicMock()
        mock_static = MagicMock()

        with patch.object(
            screen,
            "query_one",
            side_effect=lambda s, _w=None: {
                "#search-input": MagicMock(value="test"),
                "#type-filter": MagicMock(value="decision"),
                "#project-filter": MagicMock(value=""),
                "#search-results": mock_table,
                "#search-status": mock_static,
            }.get(s if isinstance(s, str) else "", MagicMock()),
        ):
            screen._do_search()

        assert mock_table.add_row.call_count == 1

    def test_results_populate_data_table(self) -> None:
        from src.interfaces.tui.screens.search_screen import SearchScreen

        mock_service = MagicMock()
        mock_service.search.return_value = [
            _make_obs(id="a" * 32, title="First"),
            _make_obs(id="b" * 32, title="Second"),
        ]

        screen = SearchScreen(db_path=None)
        screen._service = mock_service
        screen._result_ids = []

        mock_table = MagicMock()
        mock_static = MagicMock()

        with patch.object(
            screen,
            "query_one",
            side_effect=lambda s, _w=None: {
                "#search-input": MagicMock(value="test"),
                "#type-filter": MagicMock(value=""),
                "#project-filter": MagicMock(value=""),
                "#search-results": mock_table,
                "#search-status": mock_static,
            }.get(s if isinstance(s, str) else "", MagicMock()),
        ):
            screen._do_search()

        assert mock_table.add_row.call_count == 2
        assert len(screen._result_ids) == 2

    def test_open_detail_pushes_screen(self) -> None:
        from textual._context import active_app

        from src.interfaces.tui.screens.search_screen import SearchScreen

        screen = SearchScreen(db_path=None)
        screen._result_ids = ["a" * 32, "b" * 32]

        mock_table = MagicMock()
        mock_table.cursor_row = 0
        mock_app = MagicMock()

        token = active_app.set(mock_app)
        try:
            with patch.object(screen, "query_one", return_value=mock_table):
                screen.action_open_detail()
        finally:
            active_app.reset(token)

        mock_app.push_screen.assert_called_once()

    def test_open_detail_no_op_when_empty(self) -> None:
        from textual._context import active_app

        from src.interfaces.tui.screens.search_screen import SearchScreen

        screen = SearchScreen(db_path=None)
        screen._result_ids = []

        mock_table = MagicMock()
        mock_table.cursor_row = 0
        mock_app = MagicMock()

        token = active_app.set(mock_app)
        try:
            with patch.object(screen, "query_one", return_value=mock_table):
                screen.action_open_detail()
        finally:
            active_app.reset(token)

        mock_app.push_screen.assert_not_called()
