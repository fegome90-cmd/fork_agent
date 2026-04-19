"""Prompt command for CLI - save, search, list, and stats for agent prompts."""

from __future__ import annotations

from pathlib import Path

import typer

from src.infrastructure.persistence.container import get_default_db_path
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection

app = typer.Typer(name="prompt", help="Manage agent prompts with FTS5 search")

DEFAULT_DB_PATH = get_default_db_path()


def _get_db_path(ctx: typer.Context) -> Path:
    """Get database path from typer context or default."""
    if ctx.parent and ctx.parent.params:
        return Path(ctx.parent.params.get("db_path", str(get_default_db_path())))
    return get_default_db_path()


def _ensure_prompt_tables(db_path: Path) -> None:
    """Create prompts tables and FTS if they do not exist (migration 017)."""
    config = DatabaseConfig(db_path=db_path)
    connection = DatabaseConnection(config)
    with connection as conn:
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


@app.command()
def save(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Prompt text to save"),
    role: str = typer.Option("", "--role", "-r", help="Agent role"),
    model: str = typer.Option("", "--model", "-m", help="Model name"),
    provider: str = typer.Option("", "--provider", "-p", help="Provider name"),
    session_id: str | None = typer.Option(None, "--session-id", "-s", help="Session ID"),
) -> None:
    """Save a prompt to the database (auto-indexed for FTS)."""
    db_path = _get_db_path(ctx)
    _ensure_prompt_tables(db_path)

    config = DatabaseConfig(db_path=db_path)
    connection = DatabaseConnection(config)
    with connection as conn:
        conn.execute(
            "INSERT INTO prompts (prompt_text, role, model, provider, session_id) VALUES (?, ?, ?, ?, ?)",
            (text, role, model, provider, session_id),
        )

    typer.echo(f"Saved prompt: {text[:80]}{'...' if len(text) > 80 else ''}")


@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="FTS5 search query"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results"),
) -> None:
    """Search prompts using FTS5 with BM25 ranking."""
    db_path = _get_db_path(ctx)
    _ensure_prompt_tables(db_path)

    config = DatabaseConfig(db_path=db_path)
    connection = DatabaseConnection(config)
    with connection as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.prompt_text, p.role, p.model, p.provider, p.session_id,
                   bm25(prompts_fts) AS rank
            FROM prompts_fts f
            JOIN prompts p ON p.rowid = f.rowid
            WHERE prompts_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()

    if not rows:
        typer.echo("No results found")
        return

    for row in rows:
        meta_parts: list[str] = []
        if row["role"]:
            meta_parts.append(f"role={row['role']}")
        if row["model"]:
            meta_parts.append(f"model={row['model']}")
        if row["provider"]:
            meta_parts.append(f"provider={row['provider']}")
        meta_str = f" [{', '.join(meta_parts)}]" if meta_parts else ""
        typer.echo(f"[{row['id']}] {row['prompt_text'][:80]}{'...' if len(row['prompt_text']) > 80 else ''}{meta_str}")


@app.command(name="list")
def list_prompts(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit", "-l", help="Max results"),
) -> None:
    """List recent prompts."""
    db_path = _get_db_path(ctx)
    _ensure_prompt_tables(db_path)

    config = DatabaseConfig(db_path=db_path)
    connection = DatabaseConnection(config)
    with connection as conn:
        rows = conn.execute(
            "SELECT id, prompt_text, role, model, provider, session_id, timestamp FROM prompts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    if not rows:
        typer.echo("No prompts stored")
        return

    for row in rows:
        parts: list[str] = []
        if row["role"]:
            parts.append(f"role={row['role']}")
        if row["model"]:
            parts.append(f"model={row['model']}")
        if row["provider"]:
            parts.append(f"provider={row['provider']}")
        meta_str = f" [{', '.join(parts)}]" if parts else ""
        typer.echo(f"[{row['id']}] {row['prompt_text'][:80]}{'...' if len(row['prompt_text']) > 80 else ''}{meta_str}")


@app.command()
def stats(ctx: typer.Context) -> None:
    """Show prompt counts by model and provider."""
    db_path = _get_db_path(ctx)
    _ensure_prompt_tables(db_path)

    config = DatabaseConfig(db_path=db_path)
    connection = DatabaseConnection(config)
    with connection as conn:
        total = conn.execute("SELECT COUNT(*) AS cnt FROM prompts").fetchone()["cnt"]

        model_rows = conn.execute(
            "SELECT model, COUNT(*) AS cnt FROM prompts GROUP BY model ORDER BY cnt DESC"
        ).fetchall()

        provider_rows = conn.execute(
            "SELECT provider, COUNT(*) AS cnt FROM prompts GROUP BY provider ORDER BY cnt DESC"
        ).fetchall()

    typer.echo(f"Total prompts: {total}")
    if model_rows:
        typer.echo("\nBy model:")
        for row in model_rows:
            label = row["model"] if row["model"] else "(empty)"
            typer.echo(f"  {label}: {row['cnt']}")
    if provider_rows:
        typer.echo("\nBy provider:")
        for row in provider_rows:
            label = row["provider"] if row["provider"] else "(empty)"
            typer.echo(f"  {label}: {row['cnt']}")
