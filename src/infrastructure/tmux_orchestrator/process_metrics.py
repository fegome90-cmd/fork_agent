"""Process metrics collection for tmux agent sessions.

Tries psutil first, falls back to /proc on Linux.
Returns zeroed metrics on any failure.

REQ-12: Process metrics for agent session monitoring.
"""

from __future__ import annotations

import logging
import platform

logger = logging.getLogger(__name__)

# Check psutil availability at import time
try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    _PSUTIL_AVAILABLE = False


def collect_metrics(pid: int) -> dict[str, float]:
    """Collect CPU and memory metrics for a process.

    Args:
        pid: Process ID to collect metrics for.

    Returns:
        Dict with ``cpu_percent`` and ``memory_mb``. Zeroed on any failure.
    """
    if _PSUTIL_AVAILABLE and psutil is not None:
        try:
            proc = psutil.Process(pid)
            cpu = proc.cpu_percent(interval=0.1)
            mem = proc.memory_info()
            return {
                "cpu_percent": cpu,
                "memory_mb": mem.rss / (1024 * 1024),
            }
        except Exception:
            logger.debug("psutil metrics collection failed for PID %s", pid, exc_info=True)
            return {"cpu_percent": 0.0, "memory_mb": 0.0}

    # Fallback: /proc on Linux
    if platform.system() == "Linux":
        try:
            return _collect_via_proc(pid)
        except Exception:
            logger.debug("/proc metrics collection failed for PID %s", pid, exc_info=True)

    return {"cpu_percent": 0.0, "memory_mb": 0.0}


def _collect_via_proc(pid: int) -> dict[str, float]:
    """Collect metrics from /proc filesystem (Linux only).

    Reads /proc/{pid}/stat for CPU ticks and /proc/{pid}/status for memory.
    Returns raw CPU ticks (not percentage) and memory in MB.
    """
    # Read /proc/{pid}/stat for CPU
    with open(f"/proc/{pid}/stat") as f:
        stat_parts = f.read().split()
        # utime is field 14 (index 13), stime is field 15 (index 14)
        utime = int(stat_parts[13])
        stime = int(stat_parts[14])

    # Read /proc/{pid}/status for memory
    mem_kb = 0
    with open(f"/proc/{pid}/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                mem_kb = int(line.split()[1])
                break

    return {
        "cpu_percent": float(utime + stime),
        "memory_mb": mem_kb / 1024,
    }
