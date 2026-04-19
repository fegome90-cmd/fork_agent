"""Tests for DetailScreen."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.domain.entities.observation import Observation
from src.interfaces.tui.widgets.type_badge import TypeBadge


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


class TestDetailScreen:
    def test_instantiation(self) -> None:
        from src.interfaces.tui.screens.detail_screen import DetailScreen

        screen = DetailScreen(db_path=None, obs_id="abc123")
        assert screen._obs_id == "abc123"
        assert screen._db_path is None
        assert screen._observation is None

    def test_service_cached(self) -> None:
        from src.interfaces.tui.screens.detail_screen import DetailScreen

        mock_service = MagicMock()
        mock_container = MagicMock()
        mock_container.memory_service.return_value = mock_service

        with patch(
            "src.infrastructure.persistence.container.create_container",
            return_value=mock_container,
        ):
            screen = DetailScreen(db_path=None, obs_id="x" * 32)
            svc1 = screen._get_service()
            svc2 = screen._get_service()

        assert svc1 is svc2

    def test_load_observation_calls_get_by_id(self) -> None:
        from src.interfaces.tui.screens.detail_screen import DetailScreen

        obs = _make_obs(id="x" * 32)
        mock_service = MagicMock()
        mock_service.get_by_id.return_value = obs

        screen = DetailScreen(db_path=None, obs_id="x" * 32)
        screen._service = mock_service

        mock_richlog = MagicMock()
        mock_static = MagicMock()
        old_badge = MagicMock()

        def query_one_side_effect(selector, _widget_type=None):
            selector_map = {
                "#detail-header": mock_static,
                "#detail-project-info": mock_static,
                "#detail-meta": mock_static,
                "#detail-content": mock_richlog,
                "#detail-metadata": mock_static,
            }
            if isinstance(selector, type) and issubclass(selector, TypeBadge):
                return old_badge
            return selector_map.get(selector, mock_static)

        with patch.object(screen, "query_one", side_effect=query_one_side_effect):
            screen._load_observation()

        mock_service.get_by_id.assert_called_once_with("x" * 32)
        mock_richlog.write.assert_called_once_with(obs.content)

    def test_action_delete_callback_deletes_on_true(self) -> None:
        from textual._context import active_app

        from src.interfaces.tui.screens.detail_screen import DetailScreen

        mock_service = MagicMock()
        screen = DetailScreen(db_path=None, obs_id="x" * 32)
        screen._service = mock_service

        captured_callback = None

        def fake_push_screen(_screen_obj, callback=None) -> None:
            nonlocal captured_callback
            captured_callback = callback

        mock_app = MagicMock()
        mock_app.push_screen.side_effect = fake_push_screen
        mock_app.pop_screen = MagicMock()
        mock_app.notify = MagicMock()

        token = active_app.set(mock_app)
        try:
            screen.action_delete()
            assert captured_callback is not None
            captured_callback(True)
        finally:
            active_app.reset(token)

        mock_service.delete.assert_called_once_with("x" * 32)
        mock_app.pop_screen.assert_called_once()

    def test_action_delete_callback_skips_on_false(self) -> None:
        from textual._context import active_app

        from src.interfaces.tui.screens.detail_screen import DetailScreen

        mock_service = MagicMock()
        screen = DetailScreen(db_path=None, obs_id="x" * 32)
        screen._service = mock_service

        captured_callback = None

        def fake_push_screen(_screen_obj, callback=None) -> None:
            nonlocal captured_callback
            captured_callback = callback

        mock_app = MagicMock()
        mock_app.push_screen.side_effect = fake_push_screen
        mock_app.pop_screen = MagicMock()
        mock_app.notify = MagicMock()

        token = active_app.set(mock_app)
        try:
            screen.action_delete()
        finally:
            active_app.reset(token)

        assert captured_callback is not None
        captured_callback(False)

        mock_service.delete.assert_not_called()
        mock_app.pop_screen.assert_not_called()

    def test_action_edit_is_stub(self) -> None:
        from textual._context import active_app

        from src.interfaces.tui.screens.detail_screen import DetailScreen

        screen = DetailScreen(db_path=None, obs_id="abc")
        mock_app = MagicMock()
        token = active_app.set(mock_app)
        try:
            screen.action_edit()
        finally:
            active_app.reset(token)
        mock_app.notify.assert_called_once()
        call_args = mock_app.notify.call_args
        assert call_args[0][0] == "Edit coming in Phase 3"
        assert call_args[1]["severity"] == "warning"
