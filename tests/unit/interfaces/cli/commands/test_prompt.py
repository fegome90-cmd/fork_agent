"""Tests for CLI prompt command."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

runner = CliRunner()


def _create_in_memory_db() -> sqlite3.Connection:
    """Create an in-memory SQLite DB with prompts schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_text TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            provider TEXT NOT NULL DEFAULT '',
            session_id TEXT,
            timestamp INTEGER NOT NULL DEFAULT (strftime('%s','now') * 1000),
            metadata TEXT
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS prompts_fts USING fts5(
            prompt_text,
            role,
            model,
            provider,
            session_id,
            content='prompts',
            content_rowid=rowid
        );

        CREATE TRIGGER IF NOT EXISTS prompts_ai AFTER INSERT ON prompts BEGIN
            INSERT INTO prompts_fts(rowid, prompt_text, role, model, provider, session_id)
            VALUES (new.rowid, new.prompt_text, new.role, new.model, new.provider, new.session_id);
        END;

        CREATE TRIGGER IF NOT EXISTS prompts_ad AFTER DELETE ON prompts BEGIN
            INSERT INTO prompts_fts(prompts_fts, rowid, prompt_text, role, model, provider, session_id)
            VALUES ('delete', old.rowid, old.prompt_text, old.role, old.model, old.provider, old.session_id);
        END;

        CREATE TRIGGER IF NOT EXISTS prompts_au AFTER UPDATE ON prompts BEGIN
            INSERT INTO prompts_fts(prompts_fts, rowid, prompt_text, role, model, provider, session_id)
            VALUES ('delete', old.rowid, old.prompt_text, old.role, old.model, old.provider, old.session_id);
            INSERT INTO prompts_fts(rowid, prompt_text, role, model, provider, session_id)
            VALUES (new.rowid, new.prompt_text, new.role, new.model, new.provider, new.session_id);
        END;
    """)
    return conn


class TestPromptSave:
    """Tests for prompt save command."""

    @patch("src.interfaces.cli.commands.prompt._ensure_prompt_tables")
    @patch("src.interfaces.cli.commands.prompt.DatabaseConnection")
    def test_save_creates_prompt(self, mock_db_cls: MagicMock, _mock_ensure: MagicMock) -> None:
        from src.interfaces.cli.commands.prompt import app

        mock_conn = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx_obj = MagicMock()
        mock_ctx.parent = MagicMock()
        mock_ctx.parent.params = {"db_path": ":memory:"}

        mock_db_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_cls.return_value.__exit__ = MagicMock(return_value=False)

        runner.invoke(app, ["save", "test prompt"], obj=mock_ctx_obj, standalone_mode=False)

        mock_conn.execute.assert_called_once()
        args = mock_conn.execute.call_args
        assert args[0][0].startswith("INSERT INTO prompts")

    @patch("src.interfaces.cli.commands.prompt._ensure_prompt_tables")
    @patch("src.interfaces.cli.commands.prompt.DatabaseConnection")
    def test_save_with_all_optional_fields(self, mock_db_cls: MagicMock, _mock_ensure: MagicMock) -> None:
        from src.interfaces.cli.commands.prompt import app

        mock_conn = MagicMock()
        mock_db_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_cls.return_value.__exit__ = MagicMock(return_value=False)

        runner.invoke(
            app,
            ["save", "full prompt", "--role", "coder", "--model", "gpt-4", "--provider", "openai", "--session-id", "sess-1"],
            standalone_mode=False,
        )

        mock_conn.execute.assert_called_once()
        args = mock_conn.execute.call_args
        values = args[0][1]
        assert values == ("full prompt", "coder", "gpt-4", "openai", "sess-1")


class TestPromptSearch:
    """Tests for prompt search command."""

    @patch("src.interfaces.cli.commands.prompt._ensure_prompt_tables")
    @patch("src.interfaces.cli.commands.prompt.DatabaseConnection")
    def test_search_finds_by_text(self, mock_db_cls: MagicMock, _mock_ensure: MagicMock) -> None:
        from src.interfaces.cli.commands.prompt import app

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            {"id": 1, "prompt_text": "test prompt for search", "role": "", "model": "", "provider": "", "session_id": None},
        ]
        mock_db_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["search", "test"], standalone_mode=False)

        assert "test prompt" in result.stdout
        assert mock_conn.execute.called

    @patch("src.interfaces.cli.commands.prompt._ensure_prompt_tables")
    @patch("src.interfaces.cli.commands.prompt.DatabaseConnection")
    def test_empty_search_returns_nothing(self, mock_db_cls: MagicMock, _mock_ensure: MagicMock) -> None:
        from src.interfaces.cli.commands.prompt import app

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_db_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["search", "nonexistent"], standalone_mode=False)

        assert "No results found" in result.stdout

    @patch("src.interfaces.cli.commands.prompt._ensure_prompt_tables")
    @patch("src.interfaces.cli.commands.prompt.DatabaseConnection")
    def test_search_ranks_by_relevance(self, mock_db_cls: MagicMock, _mock_ensure: MagicMock) -> None:
        from src.interfaces.cli.commands.prompt import app

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            {"id": 1, "prompt_text": "exact match", "role": "", "model": "", "provider": "", "session_id": None, "rank": -1.0},
            {"id": 2, "prompt_text": "partial match only", "role": "", "model": "", "provider": "", "session_id": None, "rank": -0.5},
        ]
        mock_db_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["search", "exact match"], standalone_mode=False)

        output_lines = result.stdout.strip().split("\n")
        assert "exact match" in output_lines[0]
        assert "partial match" in output_lines[1]

        # Verify BM25 ordering in SQL
        sql = mock_conn.execute.call_args[0][0]
        assert "bm25(prompts_fts)" in sql
        assert "ORDER BY rank" in sql


class TestPromptList:
    """Tests for prompt list command."""

    @patch("src.interfaces.cli.commands.prompt._ensure_prompt_tables")
    @patch("src.interfaces.cli.commands.prompt.DatabaseConnection")
    def test_list_returns_recent(self, mock_db_cls: MagicMock, _mock_ensure: MagicMock) -> None:
        from src.interfaces.cli.commands.prompt import app

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            {"id": 2, "prompt_text": "recent prompt", "role": "", "model": "kimi", "provider": "", "session_id": None, "timestamp": 1000},
            {"id": 1, "prompt_text": "older prompt", "role": "", "model": "", "provider": "", "session_id": None, "timestamp": 500},
        ]
        mock_db_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["list"], standalone_mode=False)

        assert "recent prompt" in result.stdout
        assert "older prompt" in result.stdout
        assert "model=kimi" in result.stdout

    @patch("src.interfaces.cli.commands.prompt._ensure_prompt_tables")
    @patch("src.interfaces.cli.commands.prompt.DatabaseConnection")
    def test_list_empty(self, mock_db_cls: MagicMock, _mock_ensure: MagicMock) -> None:
        from src.interfaces.cli.commands.prompt import app

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_db_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["list"], standalone_mode=False)

        assert "No prompts stored" in result.stdout


class TestPromptStats:
    """Tests for prompt stats command."""

    @patch("src.interfaces.cli.commands.prompt._ensure_prompt_tables")
    @patch("src.interfaces.cli.commands.prompt.DatabaseConnection")
    def test_stats_aggregates_by_model(self, mock_db_cls: MagicMock, _mock_ensure: MagicMock) -> None:
        from src.interfaces.cli.commands.prompt import app

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = [
            MagicMock(fetchone=lambda: {"cnt": 5}),
            MagicMock(fetchall=lambda: [
                {"model": "gpt-4", "cnt": 3},
                {"model": "claude-3", "cnt": 2},
            ]),
            MagicMock(fetchall=lambda: [
                {"provider": "openai", "cnt": 3},
                {"provider": "anthropic", "cnt": 2},
            ]),
        ]
        mock_db_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["stats"], standalone_mode=False)

        assert "Total prompts: 5" in result.stdout
        assert "gpt-4: 3" in result.stdout
        assert "claude-3: 2" in result.stdout
        assert "openai: 3" in result.stdout


class TestPromptIntegration:
    """Integration tests with real in-memory SQLite (FTS5)."""

    def test_duplicate_prompts_both_saved(self) -> None:
        conn = _create_in_memory_db()

        conn.execute("INSERT INTO prompts (prompt_text) VALUES (?)", ("duplicate prompt",))
        conn.execute("INSERT INTO prompts (prompt_text) VALUES (?)", ("duplicate prompt",))

        count = conn.execute("SELECT COUNT(*) AS cnt FROM prompts").fetchone()["cnt"]
        assert count == 2

        fts_count = conn.execute("SELECT COUNT(*) AS cnt FROM prompts_fts").fetchone()["cnt"]
        assert fts_count == 2

        conn.close()

    def test_fts_search_returns_matching_rows(self) -> None:
        conn = _create_in_memory_db()

        conn.execute("INSERT INTO prompts (prompt_text, model) VALUES (?, ?)", ("python async patterns", "gpt-4"))
        conn.execute("INSERT INTO prompts (prompt_text, model) VALUES (?, ?)", ("rust ownership rules", "claude-3"))
        conn.execute("INSERT INTO prompts (prompt_text, model) VALUES (?, ?)", ("python type hints", "gpt-4"))

        rows = conn.execute("""
            SELECT p.prompt_text FROM prompts_fts f
            JOIN prompts p ON p.rowid = f.rowid
            WHERE prompts_fts MATCH 'python'
        """).fetchall()

        assert len(rows) == 2

        conn.close()

    def test_save_and_search_roundtrip(self) -> None:
        conn = _create_in_memory_db()

        conn.execute(
            "INSERT INTO prompts (prompt_text, role, model, provider) VALUES (?, ?, ?, ?)",
            ("implement FTS5 search", "coder", "gpt-4", "openai"),
        )

        rows = conn.execute("""
            SELECT p.prompt_text, p.model, p.provider FROM prompts_fts f
            JOIN prompts p ON p.rowid = f.rowid
            WHERE prompts_fts MATCH 'FTS5'
        """).fetchall()

        assert len(rows) == 1
        assert rows[0]["prompt_text"] == "implement FTS5 search"
        assert rows[0]["model"] == "gpt-4"

        conn.close()
