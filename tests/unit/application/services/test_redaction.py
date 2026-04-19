"""Tests for privacy redaction module."""
from __future__ import annotations

from src.application.services.redaction import (
    redact_content,
    redact_metadata,
    redact_observation_data,
)


class TestRedactContent:
    """Tests for redact_content function."""

    def test_private_tags_stripped(self) -> None:
        content, was = redact_content("before <private>secret</private> after")
        assert content == "before [REDACTED] after"
        assert was is True

    def test_private_tags_multiline(self) -> None:
        raw = "start\n<private>line1\nline2\nline3</private>\nend"
        content, was = redact_content(raw)
        assert content == "start\n[REDACTED]\nend"
        assert was is True

    def test_private_tags_case_insensitive(self) -> None:
        content, was = redact_content("text <PRIVATE>hidden</PRIVATE> text")
        assert content == "text [REDACTED] text"
        assert was is True

    def test_api_key_redacted(self) -> None:
        content, was = redact_content('api_key="sk_live_abc123defghijklmnop"')
        assert "[REDACTED]" in content
        assert "sk_live" not in content
        assert was is True

    def test_bearer_token_redacted(self) -> None:
        content, was = redact_content("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig")
        assert content == "Authorization: Bearer [REDACTED]"
        assert was is True

    def test_password_redacted(self) -> None:
        content, was = redact_content('password="supersecret123"')
        assert content == 'password="[REDACTED]"'
        assert was is True

    def test_aws_key_redacted(self) -> None:
        content, was = redact_content("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE")
        assert content == "AWS_ACCESS_KEY_ID=[REDACTED_AWS_KEY]"
        assert "AKIAIOSFODNN7EXAMPLE" not in content
        assert was is True

    def test_pem_key_redacted(self) -> None:
        pem = "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBg...\n-----END PRIVATE KEY-----"
        content, was = redact_content(f"Key follows:\n{pem}\ndone")
        assert "[REDACTED_PRIVATE_KEY]" in content
        assert "MIIEvgIBADANBg" not in content
        assert was is True

    def test_clean_content_unchanged(self) -> None:
        raw = "This is a normal log message with no secrets at all."
        content, was = redact_content(raw)
        assert content == raw
        assert was is False

    def test_was_redacted_flag_true(self) -> None:
        _, was = redact_content("password=longenoughvalue")
        assert was is True

    def test_was_redacted_flag_false(self) -> None:
        _, was = redact_content("Just a regular message")
        assert was is False

    def test_multiple_patterns_in_one_string(self) -> None:
        raw = 'api_key="abcdefghijklmnopqrst" and password="longpassword1"'
        content, was = redact_content(raw)
        assert "abcdefghijklmnopqrst" not in content
        assert "longpassword1" not in content
        assert content.count("[REDACTED]") == 2
        assert was is True

    def test_token_redacted(self) -> None:
        content, was = redact_content('token="ghp_abcdefghijklmnopqrstuvwxyz"')
        assert "[REDACTED]" in content
        assert "ghp_" not in content
        assert was is True


class TestRedactMetadata:
    """Tests for redact_metadata function."""

    def test_metadata_sensitive_keys(self) -> None:
        meta, was = redact_metadata({"api_key": "sk_live_12345", "name": "test"})
        assert meta["api_key"] == "[REDACTED]"
        assert meta["name"] == "test"
        assert was is True

    def test_metadata_nested(self) -> None:
        meta, was = redact_metadata({
            "config": {
                "password": "hunter2",
                "host": "localhost",
            },
            "public": "visible",
        })
        assert meta["config"]["password"] == "[REDACTED]"
        assert meta["config"]["host"] == "localhost"
        assert meta["public"] == "visible"
        assert was is True

    def test_metadata_secret_key(self) -> None:
        meta, was = redact_metadata({"client_secret": "s3cretvalue"})
        assert meta["client_secret"] == "[REDACTED]"
        assert was is True

    def test_metadata_access_token(self) -> None:
        meta, was = redact_metadata({"access_token": "tok_val_1234567890abcdef"})
        assert meta["access_token"] == "[REDACTED]"
        assert was is True

    def test_metadata_non_sensitive_untouched(self) -> None:
        meta, was = redact_metadata({"title": "hello", "count": 42, "tags": ["a", "b"]})
        assert meta["title"] == "hello"
        assert meta["count"] == 42
        assert meta["tags"] == ["a", "b"]
        assert was is False

    def test_metadata_string_value_redacted(self) -> None:
        meta, was = redact_metadata({"note": 'password="longenoughpass"'})
        assert meta["note"] == 'password="[REDACTED]"'
        assert was is True

    def test_empty_metadata_none(self) -> None:
        result, was = redact_metadata(None)
        assert result is None
        assert was is False

    def test_empty_metadata_dict(self) -> None:
        result, was = redact_metadata({})
        assert result == {}
        assert was is False

    def test_metadata_auth_key(self) -> None:
        meta, was = redact_metadata({"auth": "somevalue", "Authorization": "Bearer val"})
        assert meta["auth"] == "[REDACTED]"
        assert meta["Authorization"] == "[REDACTED]"
        assert was is True


class TestRedactObservationData:
    """Tests for redact_observation_data function."""

    def test_observation_data_both(self) -> None:
        content, meta, was = redact_observation_data(
            "My key is <private>hidden</private>",
            {"api_key": "sk_live_abc"},
        )
        assert content == "My key is [REDACTED]"
        assert meta["api_key"] == "[REDACTED]"
        assert was is True

    def test_observation_data_content_only(self) -> None:
        content, meta, was = redact_observation_data(
            "password=longenoughvalue",
            {"name": "test"},
        )
        assert "[REDACTED]" in content
        assert meta["name"] == "test"
        assert was is True

    def test_observation_data_metadata_only(self) -> None:
        content, meta, was = redact_observation_data(
            "clean text",
            {"secret": "hiddenvalue"},
        )
        assert content == "clean text"
        assert meta["secret"] == "[REDACTED]"
        assert was is True

    def test_observation_data_clean(self) -> None:
        content, meta, was = redact_observation_data("clean text", {"key": "value"})
        assert content == "clean text"
        assert meta["key"] == "value"
        assert was is False

    def test_observation_data_none_metadata(self) -> None:
        content, meta, was = redact_observation_data("clean text", None)
        assert content == "clean text"
        assert meta is None
        assert was is False

    def test_observation_data_content_secret_sets_flag(self) -> None:
        _, _, was = redact_observation_data("AKIAIOSFODNN7EXAMPLE", {"name": "test"})
        assert was is True
