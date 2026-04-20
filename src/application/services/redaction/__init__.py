"""Privacy redaction service for memory content."""

from __future__ import annotations

import re
from typing import Any

# Patterns to redact from content before storage
_PRIVATE_TAG_RE = re.compile(
    r"<private>(.*?)</private>",
    re.DOTALL | re.IGNORECASE,
)

# Common secret patterns (API keys, tokens, passwords)
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Generic API key patterns
    (
        re.compile(r'(api[_-]?key\s*[:=]\s*["\']?)([A-Za-z0-9_\-]{20,})(["\']?)', re.IGNORECASE),
        r"\1[REDACTED]\3",
    ),
    # Bearer tokens
    (re.compile(r"(Bearer\s+)([A-Za-z0-9_\-\.]{20,})", re.IGNORECASE), r"\1[REDACTED]"),
    # Generic tokens/secrets
    (
        re.compile(r'(token\s*[:=]\s*["\']?)([A-Za-z0-9_\-\.]{20,})(["\']?)', re.IGNORECASE),
        r"\1[REDACTED]\3",
    ),
    (
        re.compile(r'(secret\s*[:=]\s*["\']?)([A-Za-z0-9_\-\.]{20,})(["\']?)', re.IGNORECASE),
        r"\1[REDACTED]\3",
    ),
    (
        re.compile(r'(password\s*[:=]\s*["\']?)([^\s"\']{8,})(["\']?)', re.IGNORECASE),
        r"\1[REDACTED]\3",
    ),
    # AWS keys
    (re.compile(r"(AKIA[A-Z0-9]{16})"), r"[REDACTED_AWS_KEY]"),
    # Private keys (PEM)
    (
        re.compile(
            r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |DSA )?PRIVATE KEY-----"
        ),
        r"[REDACTED_PRIVATE_KEY]",
    ),
]


def redact_content(content: str) -> tuple[str, bool]:
    """Redact private/secret content from text.

    Strips <private>...</private> tags (replaces with [REDACTED]).
    Redacts common secret patterns (API keys, tokens, passwords).

    Args:
        content: Raw text to redact.

    Returns:
        Tuple of (redacted_content, was_redacted).
    """
    redacted = content
    was_redacted = False

    # 1. Strip <private>...</private> blocks
    new_content, count = _PRIVATE_TAG_RE.subn("[REDACTED]", redacted)
    if count > 0:
        redacted = new_content
        was_redacted = True

    # 2. Apply secret patterns
    for pattern, replacement in _SECRET_PATTERNS:
        new_content, count = pattern.subn(replacement, redacted)
        if count > 0:
            redacted = new_content
            was_redacted = True

    return redacted, was_redacted


def redact_metadata(metadata: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Redact sensitive values in metadata dict.

    Recursively scans metadata for sensitive keys and redacts values.

    Args:
        metadata: Metadata dictionary to redact.

    Returns:
        Tuple of (redacted_metadata, was_redacted).
    """
    if not metadata:
        return metadata, False

    was_redacted = False
    result: dict[str, Any] = {}

    _SENSITIVE_KEYS = frozenset(
        {
            "password",
            "secret",
            "token",
            "api_key",
            "apikey",
            "auth",
            "credential",
            "private_key",
            "access_token",
            "refresh_token",
            "session_token",
            "Authorization",
        }
    )

    for key, value in metadata.items():
        key_lower = key.lower()
        if any(s in key_lower for s in _SENSITIVE_KEYS):
            result[key] = "[REDACTED]"
            was_redacted = True
        elif isinstance(value, str):
            redacted_str, was_r = redact_content(value)
            result[key] = redacted_str
            if was_r:
                was_redacted = True
        elif isinstance(value, dict):
            redacted_dict, was_r = redact_metadata(value)
            result[key] = redacted_dict
            if was_r:
                was_redacted = True
        else:
            result[key] = value

    return result, was_redacted


def redact_observation_data(
    content: str,
    metadata: dict[str, Any] | None,
) -> tuple[str, dict[str, Any] | None, bool]:
    """Redact both content and metadata for an observation.

    Args:
        content: Observation content.
        metadata: Observation metadata (can be None).

    Returns:
        Tuple of (redacted_content, redacted_metadata, was_any_redacted).
    """
    redacted_content, content_redacted = redact_content(content)
    redacted_metadata = metadata
    meta_redacted = False
    if metadata:
        redacted_metadata, meta_redacted = redact_metadata(metadata)

    return redacted_content, redacted_metadata, content_redacted or meta_redacted
