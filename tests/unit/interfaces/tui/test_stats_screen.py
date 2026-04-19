"""Tests for StatsScreen."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.domain.entities.observation import Observation


def _make_obs(
    id: str = "a" * 32,
    content: str = "test",
    type: str | None = "decision",
    project: str | None = "proj",
    timestamp: int = 1_700_000_000_000,
) -> Observation:
    return Observation(id=id, timestamp=timestamp, content=content, type=type, project=project)


class TestStatsScreen:
    def test_instantiation(self) -> None:
        from src.interfaces.tui.screens.stats_screen import StatsScreen

        screen = StatsScreen(db_path=None)
        assert screen._db_path is None

    def test_render_bar_chart(self) -> None:
        from src.interfaces.tui.screens.stats_screen import StatsScreen

        result = StatsScreen._render_bar_chart({"a": 10, "b": 5})
        assert "\u2588" in result
        assert "a" in result
        assert "b" in result
        assert "10" in result
        assert "5" in result

    def test_render_bar_chart_empty(self) -> None:
        from src.interfaces.tui.screens.stats_screen import StatsScreen

        result = StatsScreen._render_bar_chart({})
        assert "No data" in result

    def test_render_bar_chart_sorted_by_count(self) -> None:
        from src.interfaces.tui.screens.stats_screen import StatsScreen

        result = StatsScreen._render_bar_chart({"z": 1, "a": 10, "m": 5})
        lines = result.strip().split("\n")
        # First line should contain 'a' (highest count)
        assert "a" in lines[0]

    def test_render_bar_chart_contains_percentages(self) -> None:
        from src.interfaces.tui.screens.stats_screen import StatsScreen

        result = StatsScreen._render_bar_chart({"x": 10, "y": 10})
        assert "50%" in result

    def test_service_cached(self) -> None:
        from src.interfaces.tui.screens.stats_screen import StatsScreen

        mock_service = MagicMock()
        mock_container = MagicMock()
        mock_container.memory_service.return_value = mock_service

        with patch(
            "src.infrastructure.persistence.container.create_container",
            return_value=mock_container,
        ):
            screen = StatsScreen(db_path=None)
            svc1 = screen._get_service()
            svc2 = screen._get_service()

        assert svc1 is svc2

    def test_health_check_cached(self) -> None:
        from src.interfaces.tui.screens.stats_screen import StatsScreen

        mock_hc = MagicMock()
        mock_container = MagicMock()
        mock_container.health_check_service.return_value = mock_hc

        with patch(
            "src.infrastructure.persistence.container.create_container",
            return_value=mock_container,
        ):
            screen = StatsScreen(db_path=None)
            hc1 = screen._get_health_check()
            hc2 = screen._get_health_check()

        assert hc1 is hc2

    def test_load_stats_calls_health_check(self) -> None:
        from src.interfaces.tui.screens.stats_screen import StatsScreen

        mock_hc = MagicMock()
        mock_hc.get_stats.return_value = {
            "observation_count": 100,
            "fts_count": 100,
            "db_size_bytes": 1024,
            "db_size_human": "1.0 KB",
        }
        mock_service = MagicMock()
        mock_service.get_recent.return_value = []
        mock_service.get_by_time_range.return_value = []

        screen = StatsScreen(db_path=None)
        screen._service = mock_service
        screen._health_check = mock_hc

        mock_static = MagicMock()

        selector_map: dict[str, MagicMock] = {}
        for sid in ["#stats-summary", "#stats-by-type", "#stats-by-project", "#stats-activity"]:
            selector_map[sid] = mock_static

        with patch.object(screen, "query_one", side_effect=lambda s, w=None: selector_map.get(s if isinstance(s, str) else "", MagicMock())):
            screen._load_stats()

        mock_hc.get_stats.assert_called_once()
        mock_service.get_recent.assert_called_once_with(limit=500)

    def test_load_stats_renders_summary(self) -> None:
        from src.interfaces.tui.screens.stats_screen import StatsScreen

        mock_hc = MagicMock()
        mock_hc.get_stats.return_value = {
            "observation_count": 42,
            "fts_count": 42,
            "db_size_bytes": 2048,
            "db_size_human": "2.0 KB",
        }
        mock_service = MagicMock()
        mock_service.get_recent.return_value = []
        mock_service.get_by_time_range.return_value = []

        screen = StatsScreen(db_path=None)
        screen._service = mock_service
        screen._health_check = mock_hc

        calls: list[tuple[str, str]] = []

        def fake_query(selector, widget_type=None):
            s = selector if isinstance(selector, str) else ""
            mock = MagicMock()
            calls.append((s, ""))

            def capture_update(text):
                calls[-1] = (s, text)

            mock.update = capture_update
            return mock

        with patch.object(screen, "query_one", side_effect=fake_query):
            screen._load_stats()

        summary_text = [c[1] for c in calls if c[0] == "#stats-summary"][0]
        assert "42" in summary_text
        assert "2.0 KB" in summary_text
