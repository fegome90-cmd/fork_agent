"""Stats screen — database statistics with bar charts."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from src.domain.entities.observation import Observation


class StatsScreen(Screen[None]):
    """Displays database statistics and activity charts."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self._db_path = db_path
        self._service: object | None = None
        self._health_check: object | None = None

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("[bold]Database Statistics[/bold]")
            yield Static("", id="stats-summary")
            yield Static("[bold]Observations by Type[/bold]")
            yield Static("", id="stats-by-type")
            yield Static("[bold]Observations by Project[/bold]")
            yield Static("", id="stats-by-project")
            yield Static("[bold]Recent Activity (7 days)[/bold]")
            yield Static("", id="stats-activity")
        yield Static("[dim][r] Refresh  [Esc] Back[/dim]", id="stats-footer")

    def on_mount(self) -> None:
        self._load_stats()

    def _get_service(self) -> object:
        if self._service is None:
            from src.infrastructure.persistence.container import (
                create_container,
                get_default_db_path,
            )

            db = self._db_path or get_default_db_path()
            container = create_container(db_path=db)
            self._service = container.memory_service()
        return self._service

    def _get_health_check(self) -> object:
        if self._health_check is None:
            from src.infrastructure.persistence.container import (
                create_container,
                get_default_db_path,
            )

            db = self._db_path or get_default_db_path()
            container = create_container(db_path=db)
            self._health_check = container.health_check_service()
        return self._health_check

    def _load_stats(self) -> None:
        # Summary
        health = self._get_health_check()
        stats = health.get_stats()
        self.query_one("#stats-summary", Static).update(
            f"Total Observations: [bold]{stats['observation_count']:,}[/bold]\n"
            f"FTS Entries: [bold]{stats['fts_count']:,}[/bold]\n"
            f"Storage: [bold]{stats['db_size_human']}[/bold]"
        )

        # Type and project breakdowns from recent observations
        service = self._get_service()
        recent: list[Observation] = service.get_recent(limit=500)

        by_type: dict[str, int] = defaultdict(int)
        by_project: dict[str, int] = defaultdict(int)
        for obs in recent:
            if obs.type:
                by_type[obs.type] += 1
            if obs.project:
                by_project[obs.project] += 1

        self.query_one("#stats-by-type", Static).update(
            self._render_bar_chart(dict(by_type))
        )
        self.query_one("#stats-by-project", Static).update(
            self._render_bar_chart(dict(by_project))
        )

        # 7-day activity
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        start_ms = int(seven_days_ago.timestamp() * 1000)
        end_ms = int(now.timestamp() * 1000)

        by_day: dict[str, int] = defaultdict(int)
        try:
            recent_obs: list[Observation] = service.get_by_time_range(start_ms, end_ms)
            for obs in recent_obs:
                if obs.timestamp:
                    day_str = datetime.fromtimestamp(
                        obs.timestamp / 1000
                    ).strftime("%Y-%m-%d")
                    by_day[day_str] += 1
        except Exception:
            pass  # get_by_time_range may not be available in all backends

        self.query_one("#stats-activity", Static).update(
            self._render_bar_chart(dict(by_day))
        )

    @staticmethod
    def _render_bar_chart(data: dict[str, int], max_bar: int = 30) -> str:
        """Render a horizontal bar chart using block characters."""
        if not data:
            return "  [dim]No data[/dim]"

        max_count = max(data.values())
        if max_count == 0:
            return "  [dim]No data[/dim]"

        total = sum(data.values())
        lines: list[str] = []
        for label, count in sorted(data.items(), key=lambda x: -x[1]):
            bar_len = int(count / max_count * max_bar)
            pct = count / total * 100 if total > 0 else 0
            lines.append(f"  {label:<20} {'█' * bar_len} {count} ({pct:.0f}%)")

        return "\n".join(lines)

    def action_refresh(self) -> None:
        self._load_stats()
