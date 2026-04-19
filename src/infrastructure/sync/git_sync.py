"""Git-based sync backend for pushing and pulling sync chunks."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitSyncBackend:
    """Git-based sync backend using data/sync/ as working directory.

    Provides push/pull operations for sync chunks via a git repository.
    The sync directory is initialized as a git repo and chunks are
    committed and pushed to a remote.
    """

    def __init__(self, sync_dir: Path, remote_url: str | None = None) -> None:
        self._sync_dir = sync_dir
        self._remote_url = remote_url

    def init_repo(self) -> None:
        """Initialize git repo in sync dir if not already."""
        self._sync_dir.mkdir(parents=True, exist_ok=True)

        if not (self._sync_dir / ".git").exists():
            self._run_git("init")
            logger.info("Initialized git repo in %s", self._sync_dir)

        # Configure remote if provided
        if self._remote_url:
            result = self._run_git("remote")
            if "origin" not in result.stdout:
                self._run_git("remote", "add", "origin", self._remote_url)
            else:
                self._run_git("remote", "set-url", "origin", self._remote_url)

        # Ensure .gitignore exists (ignore nothing — we want chunks tracked)
        gitignore = self._sync_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("# Sync chunks are tracked\n")

    def push(self, chunk_paths: list[Path], message: str | None = None) -> bool:
        """Stage chunks, commit, and push to remote.

        Args:
            chunk_paths: List of chunk files to stage.
            message: Optional commit message. Auto-generated if not provided.

        Returns:
            True if push succeeded, False otherwise.
        """
        if not chunk_paths:
            return True

        # Stage chunk files (relative to sync_dir for cleaner git paths)
        for path in chunk_paths:
            rel = path.relative_to(self._sync_dir) if path.is_relative_to(self._sync_dir) else path.name
            self._run_git("add", str(rel))

        if message is None:
            message = f"sync: push {len(chunk_paths)} chunk(s)"

        # Commit
        result = self._run_git("commit", "-m", message)
        if result.returncode != 0 and "nothing to commit" in result.stdout:
            logger.debug("Nothing to commit")
            return True

        # Push
        result = self._run_git("push", "origin", "main")
        if result.returncode != 0:
            logger.warning(
                "Push failed (rc=%d): %s %s",
                result.returncode,
                result.stdout.strip(),
                result.stderr.strip(),
            )
            return False
        logger.info("Pushed %d chunks", len(chunk_paths))
        return True

    def pull(self) -> list[Path]:
        """Pull from remote and return new chunk paths.

        Returns:
            List of new/updated .jsonl.gz file paths in sync_dir.
        """
        # Get list of chunks before pull
        before = set(self._sync_dir.glob("*.jsonl.gz"))

        try:
            # Fetch and rebase
            try:
                self._run_git("pull", "--rebase", "origin", "main")
            except subprocess.CalledProcessError:
                # Maybe no remote yet — just return empty
                logger.debug("Pull failed (no remote or no commits)")
                return []
        except Exception as e:
            logger.warning("Pull error: %s", e)
            return []

        # Find new chunks
        after = set(self._sync_dir.glob("*.jsonl.gz"))
        new_chunks = sorted(after - before)
        if new_chunks:
            logger.info("Pulled %d new chunks", len(new_chunks))
        return new_chunks

    def status(self) -> dict[str, str | int]:
        """Get git sync status.

        Returns:
            Dictionary with branch, remote, ahead/behind counts.
        """
        info: dict[str, str | int] = {}

        try:
            result = self._run_git("branch", "--show-current")
            info["branch"] = result.stdout.strip() or "main"
        except Exception:
            info["branch"] = "unknown"

        try:
            result = self._run_git("remote", "get-url", "origin")
            info["remote"] = result.stdout.strip()
        except Exception:
            info["remote"] = "none"

        try:
            result = self._run_git("rev-list", "--count", "--right-only", "@{upstream}...HEAD")
            info["behind"] = int(result.stdout.strip())
        except Exception:
            info["behind"] = 0

        try:
            result = self._run_git("rev-list", "--count", "--left-only", "@{upstream}...HEAD")
            info["ahead"] = int(result.stdout.strip())
        except Exception:
            info["ahead"] = 0

        return info

    def _run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run a git command in the sync directory."""
        return subprocess.run(
            ["git", *args],
            cwd=str(self._sync_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
