"""Tests for SaveScreen."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.domain.entities.observation import Observation


class TestSaveScreen:
    def test_instantiation(self) -> None:
        from src.interfaces.tui.screens.save_screen import SaveScreen

        screen = SaveScreen(db_path=None)
        assert screen._db_path is None

    def test_validate_empty_content(self) -> None:
        from src.interfaces.tui.screens.save_screen import SaveScreen

        screen = SaveScreen(db_path=None)

        with patch.object(screen, "query_one", side_effect=lambda s, w=None: {
            "#save-content": MagicMock(text="  "),
            "#save-type": MagicMock(value="decision"),
            "#save-topic-key": MagicMock(value=""),
        }.get(s if isinstance(s, str) else "", MagicMock())):
            errors = screen._validate()

        assert any("Content is required" in e for e in errors)

    def test_validate_invalid_type(self) -> None:
        from src.interfaces.tui.screens.save_screen import SaveScreen

        screen = SaveScreen(db_path=None)

        with patch.object(screen, "query_one", side_effect=lambda s, w=None: {
            "#save-content": MagicMock(text="some content"),
            "#save-type": MagicMock(value="invalid_type"),
            "#save-topic-key": MagicMock(value=""),
        }.get(s if isinstance(s, str) else "", MagicMock())):
            errors = screen._validate()

        assert any("Invalid type" in e for e in errors)

    def test_validate_topic_key_spaces(self) -> None:
        from src.interfaces.tui.screens.save_screen import SaveScreen

        screen = SaveScreen(db_path=None)

        with patch.object(screen, "query_one", side_effect=lambda s, w=None: {
            "#save-content": MagicMock(text="content"),
            "#save-type": MagicMock(value=""),
            "#save-topic-key": MagicMock(value="has spaces"),
        }.get(s if isinstance(s, str) else "", MagicMock())):
            errors = screen._validate()

        assert any("spaces" in e for e in errors)

    def test_validate_all_valid(self) -> None:
        from src.interfaces.tui.screens.save_screen import SaveScreen

        screen = SaveScreen(db_path=None)

        with patch.object(screen, "query_one", side_effect=lambda s, w=None: {
            "#save-content": MagicMock(text="valid content"),
            "#save-type": MagicMock(value="decision"),
            "#save-topic-key": MagicMock(value="valid-key"),
        }.get(s if isinstance(s, str) else "", MagicMock())):
            errors = screen._validate()

        assert errors == []

    def test_action_save_calls_service(self) -> None:
        from textual._context import active_app

        from src.interfaces.tui.screens.save_screen import SaveScreen

        mock_service = MagicMock()
        screen = SaveScreen(db_path=None)
        screen._service = mock_service

        mock_app = MagicMock()
        mock_app.pop_screen = MagicMock()
        mock_app.notify = MagicMock()
        mock_static = MagicMock()

        token = active_app.set(mock_app)
        try:
            with patch.object(screen, "query_one", side_effect=lambda s, w=None: {
                "#save-content": MagicMock(text="content here"),
                "#save-type": MagicMock(value="decision"),
                "#save-topic-key": MagicMock(value="my-key"),
                "#save-project": MagicMock(value="proj"),
                "#save-title": MagicMock(value="Title"),
                "#save-validation": mock_static,
            }.get(s if isinstance(s, str) else "", MagicMock())):
                screen.action_save()
        finally:
            active_app.reset(token)

        mock_service.save.assert_called_once_with(
            content="content here",
            type="decision",
            topic_key="my-key",
            project="proj",
            title="Title",
        )
        mock_app.pop_screen.assert_called_once()

    def test_action_save_invalid_shows_errors(self) -> None:
        from textual._context import active_app

        from src.interfaces.tui.screens.save_screen import SaveScreen

        screen = SaveScreen(db_path=None)
        mock_static = MagicMock()

        token = active_app.set(MagicMock())
        try:
            with patch.object(screen, "query_one", side_effect=lambda s, w=None: {
                "#save-content": MagicMock(text=""),
                "#save-type": MagicMock(value=""),
                "#save-topic-key": MagicMock(value=""),
                "#save-validation": mock_static,
            }.get(s if isinstance(s, str) else "", MagicMock())):
                screen.action_save()
        finally:
            active_app.reset(token)

        mock_static.update.assert_called_once()
        update_text = mock_static.update.call_args[0][0]
        assert "Content is required" in update_text

    def test_preview_updates(self) -> None:
        from src.interfaces.tui.screens.save_screen import SaveScreen

        screen = SaveScreen(db_path=None)
        mock_static = MagicMock()

        with patch.object(screen, "query_one", side_effect=lambda s, w=None: {
            "#save-content": MagicMock(text="hello world"),
            "#save-type": MagicMock(value="decision"),
            "#save-topic-key": MagicMock(value=""),
            "#save-project": MagicMock(value="proj"),
            "#save-title": MagicMock(value=""),
            "#save-preview": mock_static,
        }.get(s if isinstance(s, str) else "", MagicMock())):
            screen._update_preview()

        mock_static.update.assert_called_once()
        text = mock_static.update.call_args[0][0]
        assert "decision" in text
        assert "proj" in text
