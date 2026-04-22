"""Memory tool handlers: 17 MCP tools for observation CRUD, search, sessions, topics."""

from __future__ import annotations

import json
import re
from typing import Any

from mcp import McpError
from mcp.types import INVALID_PARAMS, ErrorData

from src.interfaces.mcp.tools._shared import (
    _get_enhanced_search_service,
    _get_health_service,
    _get_memory_service,
    _get_session_service,
    _map_error,
    _resolve_project,
    logger,
)

# ---------------------------------------------------------------------------
# Serialization + Token Capping
# ---------------------------------------------------------------------------


def _cap_json_response(
    data: list[dict[str, Any]] | dict[str, Any], max_tokens: int | None = None
) -> str:
    """Serialize data to JSON with optional token capping.

    If the serialized JSON exceeds max_tokens (default: 8000),
    the response is truncated to fit within the token budget.
    """
    from src.application.services.output_caps import (
        DEFAULT_MAX_TOKENS,
        cap_response,
        estimate_tokens,
    )

    raw_json = json.dumps(data)
    effective_max = max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
    if estimate_tokens(raw_json) > effective_max:
        serialized = data if isinstance(data, list) else [data]
        serialized = cap_response(serialized, effective_max)
        if isinstance(data, dict):
            # Preserve object shape — return first item or empty dict, never a list
            return json.dumps(serialized[0] if serialized else {})
        return json.dumps(serialized)
    return raw_json


def _serialize_observation(obs: Any) -> dict[str, Any]:
    """Serialize Observation to MCP-safe dict.

    Uses dataclasses.asdict() and omits None fields to reduce token usage.
    """
    import dataclasses

    data = dataclasses.asdict(obs)
    return {k: v for k, v in data.items() if v is not None}


def _serialize_observations(obs_list: list[Any]) -> list[dict[str, Any]]:
    """Serialize a list of Observation entities."""
    return [_serialize_observation(obs) for obs in obs_list]


def _serialize_session(session: Any) -> dict[str, Any]:
    """Serialize Session to MCP-safe dict.

    Uses dataclasses.asdict() and omits None fields to reduce token usage.
    """
    import dataclasses

    data = dataclasses.asdict(session)
    return {k: v for k, v in data.items() if v is not None}


def _serialize_sessions(sessions: list[Any]) -> list[dict[str, Any]]:
    """Serialize a list of Session entities."""
    return [_serialize_session(s) for s in sessions]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def memory_save(
    content: str,
    type: str | None = None,
    project: str | None = None,
    topic_key: str | None = None,
    metadata: dict | None = None,
    title: str | None = None,
) -> str:
    """Save an observation to memory.

    Args:
        content: The observation text to save (required).
        type: Observation type (decision, discovery, pattern, bugfix, config, preference, session-summary, etc.).
        project: Optional project name for scoping.
        topic_key: Optional stable key for upsert (no spaces). If an observation with this key exists, it will be updated.
        metadata: Optional dict with metadata fields (what, why, where, learned, etc.).
        title: Optional short searchable title for the observation.

    Returns:
        JSON with observation id and status.
    """
    if not content or not content.strip():
        raise McpError(ErrorData(code=INVALID_PARAMS, message="content must not be empty"))
    effective_project = _resolve_project(project)
    try:
        service = _get_memory_service()
        observation = service.save(
            content=content,
            metadata=metadata,
            topic_key=topic_key,
            project=effective_project,
            type=type,
            title=title,
        )
        return json.dumps(
            {"id": observation.id, "status": "saved", "topic_key": observation.topic_key}
        )
    except Exception as e:
        logger.error("memory_save failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_search(
    query: str, limit: int | None = None, max_tokens: int | None = None, project: str | None = None
) -> str:
    """Search memory for observations matching a query.

    Uses FTS5 full-text search. Returns observations sorted by relevance.

    Args:
        query: Search terms to find matching observations (required).
        limit: Maximum number of results to return (default: 10).
        max_tokens: Optional max tokens in response (default: 8000, ~32KB). Truncates large content.
        project: Optional project name for scoping. Auto-detected from CWD if not provided.

    Returns:
        JSON array of matching observations.
    """
    try:
        service = _get_memory_service()
        effective_project = _resolve_project(project)
        results = service.search(query=query, limit=limit, project=effective_project)
        serialized = _serialize_observations(results)
        return _cap_json_response(serialized, max_tokens)
    except Exception as e:
        logger.error("memory_search failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_retrieve(
    query: str,
    limit: int | None = None,
    project: str | None = None,
    type: str | None = None,
    max_tokens: int | None = None,
) -> str:
    """Enhanced retrieval search using multi-signal scoring (concept overlap, semantic bridges, keyword density). Returns more relevant results than memory_search for complex queries.

    Args:
        query: Search terms to find matching observations (required).
        limit: Maximum number of results to return (default: 5).
        project: Optional project name for scoping.
        type: Optional observation type filter (e.g., 'decision', 'bugfix').
        max_tokens: Optional max tokens in response (default: 8000, ~32KB). Truncates large content.

    Returns:
        JSON array of matching observations ranked by multi-signal score.
    """
    try:
        service = _get_enhanced_search_service()
        effective_project = _resolve_project(project)
        results = service.search(query=query, limit=limit, project=effective_project, type=type)
        serialized = _serialize_observations(results)
        return _cap_json_response(serialized, max_tokens)
    except Exception as e:
        logger.error("memory_retrieve failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_get(id: str, max_tokens: int | None = None) -> str:
    """Retrieve a specific observation by its ID.

    Args:
        id: The UUID of the observation to retrieve (required).
        max_tokens: Optional max tokens in response (default: 8000, ~32KB). Truncates large content.

    Returns:
        JSON with full observation details.
    """
    try:
        service = _get_memory_service()
        observation = service.get_by_id(id)
        serialized = [_serialize_observation(observation)]
        return _cap_json_response(serialized[0] if serialized else {}, max_tokens)
    except Exception as e:
        logger.error("memory_get failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_list(
    limit: int = 10,
    offset: int = 0,
    type: str | None = None,
    project: str | None = None,
    max_tokens: int | None = None,
) -> str:
    """List recent observations with optional filtering and pagination.

    Args:
        limit: Maximum number of observations to return (default: 10).
        offset: Number of observations to skip (default: 0).
        type: Optional type filter (e.g., 'decision', 'session-summary').
        project: Optional project name for scoping. Auto-detected from CWD if not provided.
        max_tokens: Optional max tokens in response (default: 8000, ~32KB). Truncates large content.

    Returns:
        JSON array of observations.
    """
    try:
        service = _get_memory_service()
        effective_project = _resolve_project(project)
        results = service.get_recent(
            limit=limit, offset=offset, type=type, project=effective_project
        )
        serialized = _serialize_observations(results)
        return _cap_json_response(serialized, max_tokens)
    except Exception as e:
        logger.error("memory_list failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_delete(id: str) -> str:
    """Delete an observation by its ID.

    Args:
        id: The UUID of the observation to delete (required).

    Returns:
        JSON with the deleted observation's ID and status.
    """
    try:
        service = _get_memory_service()
        service.delete(id)
        return json.dumps({"id": id, "status": "deleted"})
    except Exception as e:
        logger.error("memory_delete failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_context(
    limit: int = 5, max_tokens: int | None = None, project: str | None = None
) -> str:
    """Get recent session summaries and context observations.

    Tries to return session-summary type first, falls back to all recent
    if no session summaries exist.

    Args:
        limit: Maximum observations to return (default: 5).
        max_tokens: Optional max tokens in response (default: 8000, ~32KB). Truncates large content.
        project: Optional project name for scoping. Auto-detected from CWD if not provided.

    Returns:
        JSON array of context observations.
    """
    try:
        service = _get_memory_service()
        effective_project = _resolve_project(project)
        results = service.get_recent(
            limit=limit, offset=0, type="session-summary", project=effective_project
        )

        if not results:
            results = service.get_recent(
                limit=limit, offset=0, type=None, project=effective_project
            )

        serialized = _serialize_observations(results)
        return _cap_json_response(serialized, max_tokens)
    except Exception as e:
        logger.error("memory_context failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_update(
    id: str,
    content: str | None = None,
    type: str | None = None,
    project: str | None = None,
    topic_key: str | None = None,
    metadata: dict | None = None,
    title: str | None = None,
    max_tokens: int | None = None,
) -> str:
    """Update an existing observation.

    Args:
        id: The UUID of the observation to update (required).
        content: New content text (optional).
        type: New observation type (optional).
        project: New project name (optional).
        topic_key: New stable key for grouping (optional).
        metadata: Optional dict with updated metadata fields.
        title: Optional short searchable title for the observation.
        max_tokens: Optional max tokens in response (default: 8000, ~32KB). Truncates large content.

    Returns:
        JSON with the updated observation details.
    """
    try:
        service = _get_memory_service()
        observation = service.update(
            observation_id=id,
            content=content,
            type=type,
            project=project,
            topic_key=topic_key,
            metadata=metadata,
            title=title,
        )
        serialized = _serialize_observation(observation)
        return _cap_json_response(serialized, max_tokens)
    except Exception as e:
        logger.error("memory_update failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_stats() -> str:
    """Get database statistics.

    Returns:
        JSON with observation_count, fts_count, db_size_bytes, db_size_human.
    """
    try:
        service = _get_health_service()
        stats = service.get_stats()
        return json.dumps(stats)
    except Exception as e:
        logger.error("memory_stats failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_timeline(
    start: int, end: int, max_tokens: int | None = None, project: str | None = None
) -> str:
    """Get observations within a time range.

    Args:
        start: Start timestamp in Unix milliseconds (required).
        end: End timestamp in Unix milliseconds (required).
        max_tokens: Optional max tokens in response (default: 8000, ~32KB). Truncates large content.

    Returns:
        JSON array of observations in the time range.
    """
    try:
        service = _get_memory_service()
        effective_project = _resolve_project(project)
        results = service.get_by_time_range(start, end, project=effective_project)
        serialized = _serialize_observations(results)
        return _cap_json_response(serialized, max_tokens)
    except Exception as e:
        logger.error("memory_timeline failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_session_start(
    project: str,
    directory: str,
    goal: str | None = None,
    instructions: str | None = None,
) -> str:
    """Start a new session. Auto-ends any previous active session for the project.

    Args:
        project: Project name for the session (required).
        directory: Working directory path (required).
        goal: Optional goal description.
        instructions: Optional instructions or constraints.

    Returns:
        JSON with the new session details.
    """
    try:
        service = _get_session_service()
        session = service.start_session(
            project=project,
            directory=directory,
            goal=goal,
            instructions=instructions,
        )
        return json.dumps(_serialize_session(session))
    except Exception as e:
        logger.error("memory_session_start failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_session_end(
    session_id: str,
    summary: str | None = None,
) -> str:
    """End an active session.

    Args:
        session_id: The ID of the session to end (required).
        summary: Optional summary of what was accomplished.

    Returns:
        JSON with the updated session details.
    """
    try:
        service = _get_session_service()
        session = service.end_session(session_id, summary=summary)
        return json.dumps(_serialize_session(session))
    except Exception as e:
        logger.error("memory_session_end failed: %s", e, exc_info=True)
        raise _map_error(e) from e


def memory_session_summary(
    content: str,
    project: str | None = None,
    session_id: str | None = None,
) -> str:
    """Save a structured session summary as a session-summary type observation.

    Args:
        content: The summary text (required).
        project: Optional project name for scoping.
        session_id: Optional session ID to link the summary to.

    Returns:
        JSON with observation id and status.
    """
    if not content or not content.strip():
        raise _map_error(ValueError("Content must not be empty"))

    effective_project = _resolve_project(project)
    try:
        meta: dict[str, Any] = {}
        if session_id:
            meta["session_id"] = session_id

        service = _get_memory_service()
        observation = service.save(
            content=content,
            metadata=meta if meta else None,
            project=effective_project,
            type="session-summary",
        )
        return json.dumps({"id": observation.id, "status": "saved", "type": "session-summary"})
    except Exception as e:
        logger.error("memory_session_summary failed: %s", e, exc_info=True)
        raise _map_error(e) from e


# ---------------------------------------------------------------------------
# Topic key suggestion
# ---------------------------------------------------------------------------


_TOPIC_FAMILY_MAP: dict[str, str] = {
    "architecture": "architecture",
    "design": "architecture",
    "adr": "architecture",
    "refactor": "architecture",
    "bug": "bug",
    "bugfix": "bug",
    "fix": "bug",
    "incident": "bug",
    "hotfix": "bug",
    "decision": "decision",
    "pattern": "pattern",
    "convention": "pattern",
    "guideline": "pattern",
    "config": "config",
    "setup": "config",
    "infra": "config",
    "infrastructure": "config",
    "ci": "config",
    "discovery": "discovery",
    "investigation": "discovery",
    "root_cause": "discovery",
    "root-cause": "discovery",
    "learning": "learning",
    "learn": "learning",
    "session-summary": "session",
}

_TOPIC_KEYWORDS = ("bug", "architecture", "decision", "pattern", "config", "discovery", "learning")


def _infer_topic_family(obs_type: str | None, title: str, content: str) -> str:
    if obs_type:
        lower_type = obs_type.lower().strip()
        if lower_type in _TOPIC_FAMILY_MAP:
            return _TOPIC_FAMILY_MAP[lower_type]

    combined = f"{title} {content}".lower()
    for keyword in _TOPIC_KEYWORDS:
        if keyword in combined:
            return _TOPIC_FAMILY_MAP.get(keyword, "topic")

    if obs_type:
        normalized = _normalize_topic_segment(obs_type)
        return normalized if normalized else "topic"

    return "topic"


def _normalize_topic_segment(text: str) -> str:
    value = text.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = "-".join(value.split())
    if len(value) > 100:
        value = value[:100]
    return value


def _suggest_topic_key(obs_type: str | None, title: str, content: str) -> str:
    family = _infer_topic_family(obs_type, title, content)

    segment = _normalize_topic_segment(title)

    if not segment:
        words = content.lower().split()[:8]
        segment = _normalize_topic_segment(" ".join(words))

    if not segment:
        segment = "general"

    if segment.startswith(f"{family}-"):
        segment = segment[len(family) + 1 :]

    if not segment or segment == family:
        segment = "general"

    return f"{family}/{segment}"


def memory_suggest_topic_key(
    title: str | None = None,
    type: str | None = None,
    content: str | None = None,
) -> str:
    """Suggest a stable topic_key for an observation.

    Generates a topic_key in family/segment format based on the observation
    type, title, and content. Use this before saving to get a consistent,
    normalized key for upserts.

    Args:
        title: Observation title (preferred input for stable keys).
        type: Observation type (e.g., 'architecture', 'decision', 'bugfix').
        content: Observation content (fallback if title is empty).

    Returns:
        JSON with the suggested topic_key and the family/segment breakdown.
    """
    title_text = title or ""
    content_text = content or ""

    if not title_text.strip() and not content_text.strip():
        raise _map_error(ValueError("Provide at least a title or content to suggest a topic_key"))

    suggested = _suggest_topic_key(type, title_text, content_text)
    family, _, segment = suggested.partition("/")

    return json.dumps(
        {
            "topic_key": suggested,
            "family": family,
            "segment": segment,
        }
    )


# ---------------------------------------------------------------------------
# Prompt saving
# ---------------------------------------------------------------------------


def memory_save_prompt(
    content: str,
    project: str | None = None,
    session_id: str | None = None,
    role: str | None = None,
    model: str | None = None,
    provider: str | None = None,
) -> str:
    """Save a user prompt to the dedicated prompts table."""
    if not content or not content.strip():
        raise _map_error(ValueError("Content must not be empty"))

    try:
        service = _get_memory_service()
        prompt_id = service.save_prompt(
            content=content,
            project=project,
            session_id=session_id,
            role=role,
            model=model,
            provider=provider,
        )
        preview = content[:80] + ("..." if len(content) > 80 else "")
        return json.dumps({"id": prompt_id, "status": "saved", "preview": preview})
    except Exception as e:
        logger.error("memory_save_prompt failed: %s", e, exc_info=True)
        raise _map_error(e) from e


# ---------------------------------------------------------------------------
# Passive learning capture
# ---------------------------------------------------------------------------


_LEARNING_HEADER_RE = re.compile(
    r"(?im)^#{2,3}\s+(?:Aprendizajes(?:\s+Clave)?|Key\s+Learnings?|Learnings?):?\s*$"
)
_NUMBERED_ITEM_RE = re.compile(r"^\s*\d+[.)]\s+(.+)", re.MULTILINE)
_BULLET_ITEM_RE = re.compile(r"^\s*[-*]\s+(.+)", re.MULTILINE)
_MIN_LEARNING_LENGTH = 20
_MIN_LEARNING_WORDS = 4


def _extract_learnings(text: str) -> list[str]:
    """Extract learning items from text containing a Key Learnings section."""
    lines = text.split("\n")
    in_section = False
    section_lines: list[str] = []

    for line in lines:
        if _LEARNING_HEADER_RE.match(line):
            in_section = True
            section_lines = []
            continue

        if in_section:
            if re.match(r"^#{1,3}\s+", line) and not _LEARNING_HEADER_RE.match(line):
                break
            section_lines.append(line)

    raw_text = "\n".join(section_lines)
    if not raw_text.strip():
        return []

    items: list[str] = []
    numbered = _NUMBERED_ITEM_RE.findall(raw_text)
    items = numbered or _BULLET_ITEM_RE.findall(raw_text)

    cleaned: list[str] = []
    for item in items:
        text_clean = re.sub(r"\*\*(.+?)\*\*", r"\1", item)
        text_clean = re.sub(r"`(.+?)`", r"\1", text_clean)
        text_clean = re.sub(r"\*(.+?)\*", r"\1", text_clean)
        text_clean = re.sub(r"\s+", " ", text_clean).strip()

        if (
            len(text_clean) >= _MIN_LEARNING_LENGTH
            and len(text_clean.split()) >= _MIN_LEARNING_WORDS
        ):
            cleaned.append(text_clean)

    return cleaned


def memory_capture_passive(
    content: str,
    project: str | None = None,
    session_id: str | None = None,
    source: str | None = None,
) -> str:
    """Extract and save learnings from text output.

    Scans content for a '## Key Learnings:' or '## Aprendizajes Clave:' section,
    extracts numbered or bulleted items, and saves each as a separate observation.
    Duplicates within the same project are skipped.

    Args:
        content: Text output containing a learnings section (required).
        project: Optional project name for scoping.
        session_id: Optional session ID to associate.
        source: Optional source identifier (default: 'mcp-passive').

    Returns:
        JSON with extracted, saved, and duplicate counts.
    """
    if not content or not content.strip():
        raise _map_error(ValueError("Content must not be empty"))

    effective_project = _resolve_project(project)
    try:
        learnings = _extract_learnings(content)

        if not learnings:
            return json.dumps({"extracted": 0, "saved": 0, "duplicates": 0})

        service = _get_memory_service()
        effective_source = source or "mcp-passive"
        meta: dict[str, Any] = {"source": effective_source}
        if session_id:
            meta["session_id"] = session_id

        saved = 0
        duplicates = 0

        for learning in learnings:
            existing = service.search(query=learning[:60], limit=1)
            if existing and any(e.content == learning for e in existing):
                duplicates += 1
                continue

            service.save(
                content=learning,
                metadata=meta if meta else None,
                project=effective_project,
                type="learning-batch",
            )
            saved += 1

        return json.dumps(
            {
                "extracted": len(learnings),
                "saved": saved,
                "duplicates": duplicates,
            }
        )
    except Exception as e:
        logger.error("memory_capture_passive failed: %s", e, exc_info=True)
        raise _map_error(e) from e


# ---------------------------------------------------------------------------
# Project merge
# ---------------------------------------------------------------------------


def memory_merge_projects(
    from_projects: str,
    to_project: str,
) -> str:
    """Merge observations and sessions from source projects into a target project."""
    if not from_projects or not from_projects.strip():
        raise McpError(ErrorData(code=INVALID_PARAMS, message="from_projects must not be empty"))
    if not to_project or not to_project.strip():
        raise McpError(ErrorData(code=INVALID_PARAMS, message="to_project must not be empty"))

    try:
        service = _get_memory_service()
        result = service.merge_projects(from_projects=from_projects, to_project=to_project)
        return json.dumps(result)
    except Exception as e:
        logger.error("memory_merge_projects failed: %s", e, exc_info=True)
        raise _map_error(e) from e
