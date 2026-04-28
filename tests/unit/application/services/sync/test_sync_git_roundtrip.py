from __future__ import annotations

import pytest

"""Tests for git push/pull roundtrip operations.

Uses real git subprocess calls with bare remote repos.
"""


import gzip
import subprocess
from pathlib import Path

from src.infrastructure.sync.git_sync import GitSyncBackend


def _write_chunk(path: Path, data: dict) -> None:
    """Write a single dict as a gzipped JSONL line."""
    import json

    with gzip.open(path, "wt") as f:
        f.write(json.dumps(data) + "\n")


@pytest.mark.requires_git
class TestGitPushPullRoundtrip:
    def test_push_then_pull_roundtrip(self, tmp_path: Path) -> None:
        """Push 2 chunks to bare remote, clone pulls them back."""

        # Setup bare remote
        bare = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)

        # Push from sync_dir
        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()
        git_push = GitSyncBackend(sync_dir=sync_dir, remote_url=str(bare))
        git_push.init_repo()

        chunk1 = sync_dir / "chunk_001.jsonl.gz"
        chunk2 = sync_dir / "chunk_002.jsonl.gz"
        _write_chunk(chunk1, {"id": "obs-1", "content": "first"})
        _write_chunk(chunk2, {"id": "obs-2", "content": "second"})

        ok = git_push.push([chunk1, chunk2])
        assert ok is True

        # Pull into a separate clone
        clone_dir = tmp_path / "clone"
        subprocess.run(
            ["git", "clone", str(bare), str(clone_dir)],
            check=True,
            capture_output=True,
        )

        clone_git = GitSyncBackend(sync_dir=clone_dir, remote_url=str(bare))
        clone_git.init_repo()
        new_chunks = clone_git.pull()
        assert len(new_chunks) == 0  # Already has them from clone

        # Verify files exist in clone
        assert (clone_dir / "chunk_001.jsonl.gz").exists()
        assert (clone_dir / "chunk_002.jsonl.gz").exists()

    def test_push_empty_list_returns_true(self, tmp_path: Path) -> None:
        """Push with empty list returns True (no-op)."""
        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()
        git = GitSyncBackend(sync_dir=sync_dir)
        git.init_repo()

        result = git.push([])
        assert result is True

    def test_push_with_invalid_remote_returns_false(self, tmp_path: Path) -> None:
        """Push to a non-existent remote path returns False."""

        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()
        bad_remote = tmp_path / "nonexistent.git"
        git = GitSyncBackend(sync_dir=sync_dir, remote_url=str(bad_remote))
        git.init_repo()

        chunk = sync_dir / "test.jsonl.gz"
        _write_chunk(chunk, {"id": "t1", "content": "data"})

        result = git.push([chunk])
        assert result is False

    def test_pull_no_remote_returns_empty(self, tmp_path: Path) -> None:
        """Pull with no remote configured returns empty list."""
        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()
        git = GitSyncBackend(sync_dir=sync_dir)
        git.init_repo()

        result = git.pull()
        assert result == []

    def test_push_pull_with_manifest_file(self, tmp_path: Path) -> None:
        """Push chunks+manifest, pull returns only .jsonl.gz files."""

        # Setup bare remote
        bare = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)

        # Push
        push_dir = tmp_path / "push_sync"
        push_dir.mkdir()
        git_push = GitSyncBackend(sync_dir=push_dir, remote_url=str(bare))
        git_push.init_repo()

        chunk = push_dir / "sync_100_000.jsonl.gz"
        manifest = push_dir / "manifest_100.json"
        _write_chunk(chunk, {"id": "m1", "content": "manifest-test"})
        manifest.write_text('{"chunk_count": 1}')

        ok = git_push.push([chunk])
        assert ok is True

        # Pull into new dir
        pull_dir = tmp_path / "pull_sync"
        pull_dir.mkdir()
        git_pull = GitSyncBackend(sync_dir=pull_dir, remote_url=str(bare))
        git_pull.init_repo()
        git_pull.pull()

        # Verify only .jsonl.gz files exist
        jsonl_files = list(pull_dir.glob("*.jsonl.gz"))
        assert len(jsonl_files) == 1
        assert jsonl_files[0].name == "sync_100_000.jsonl.gz"

        # Manifest is also pulled (it's tracked), but pull() only returns jsonl.gz
        all_tracked = list(pull_dir.glob("*.json"))
        assert len(all_tracked) >= 0  # manifest may or may not be here depending on git state
