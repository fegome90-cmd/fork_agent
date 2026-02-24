"""Servicio para interactuar con PM2."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from src.interfaces.api.models import ProcessInfo


class PM2Service:
    """Servicio para gestionar procesos PM2."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path(os.environ.get("PM2_BASE_DIR", Path.cwd()))

    async def list_processes(self) -> list[ProcessInfo]:
        """Lista todos los procesos PM2."""
        try:
            result = await asyncio.create_subprocess_exec(
                "pm2",
                "jlist",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _stderr = await result.communicate()

            if result.returncode != 0:
                return []

            processes = json.loads(stdout.decode())

            return [
                ProcessInfo(
                    name=p.get("name", ""),
                    pm_id=p.get("pm_id", 0),
                    pid=p.get("pid", 0),
                    status=p.get("pm2_env", {}).get("status", "unknown"),
                    cpu=p.get("monit", {}).get("cpu", 0.0),
                    memory=self._format_memory(p.get("monit", {}).get("memory", 0)),
                    uptime=datetime.fromtimestamp(p.get("pm2_env", {}).get("created_at", 0) / 1000),
                    restarts=p.get("pm2_env", {}).get("restart_time", 0),
                    health="healthy"
                    if p.get("pm2_env", {}).get("status") == "online"
                    else "unhealthy",
                    env=p.get("pm2_env", {}).get("env", {}),
                )
                for p in processes
            ]
        except Exception:
            return []

    async def get_process(self, pm_id: int) -> ProcessInfo | None:
        """Obtiene un proceso específico por PM ID."""
        processes = await self.list_processes()
        for p in processes:
            if p.pm_id == pm_id:
                return p
        return None

    async def start_process(
        self,
        name: str,
        script: str,
        args: str | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, int | str]:
        """Inicia un nuevo proceso PM2."""
        cmd = ["pm2", "start", script, "--name", name]

        if args:
            cmd.extend(["--", *args.split()])

        # Use stored base_dir if cwd not provided
        effective_cwd = cwd if cwd else str(self._base_dir)
        cmd.extend(["--cwd", effective_cwd])

        try:
            subprocess_env = os.environ.copy()
            if env:
                subprocess_env.update(env)

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=subprocess_env,
            )
            await result.communicate()

            if result.returncode == 0:
                processes = await self.list_processes()
                for p in processes:
                    if p.name == name:
                        return {
                            "pm_id": p.pm_id,
                            "name": p.name,
                            "status": "launching",
                        }

            return {"pm_id": -1, "name": name, "status": "failed"}
        except Exception:
            return {"pm_id": -1, "name": name, "status": "error"}

    async def stop_process(self, pm_id: int) -> dict[str, int | str]:
        """Detiene un proceso PM2."""
        try:
            result = await asyncio.create_subprocess_exec(
                "pm2",
                "stop",
                str(pm_id),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()

            return {"pm_id": pm_id, "status": "stopped" if result.returncode == 0 else "error"}
        except Exception:
            return {"pm_id": pm_id, "status": "error"}

    async def restart_process(self, pm_id: int) -> dict[str, int | str]:
        """Reinicia un proceso PM2."""
        try:
            result = await asyncio.create_subprocess_exec(
                "pm2",
                "restart",
                str(pm_id),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()

            return {"pm_id": pm_id, "status": "restarting" if result.returncode == 0 else "error"}
        except Exception:
            return {"pm_id": pm_id, "status": "error"}

    async def delete_process(self, pm_id: int) -> dict[str, int | str]:
        """Elimina un proceso PM2."""
        try:
            result = await asyncio.create_subprocess_exec(
                "pm2",
                "delete",
                str(pm_id),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()

            return {"pm_id": pm_id, "status": "deleted" if result.returncode == 0 else "error"}
        except Exception:
            return {"pm_id": pm_id, "status": "error"}

    async def scale_process(self, pm_id: int, instances: int) -> dict[str, int | str]:
        """Escala un proceso PM2 (cluster)."""
        try:
            result = await asyncio.create_subprocess_exec(
                "pm2",
                "scale",
                str(pm_id),
                str(instances),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()

            return {
                "pm_id": pm_id,
                "instances": instances,
                "status": "scaled" if result.returncode == 0 else "error",
            }
        except Exception:
            return {"pm_id": pm_id, "status": "error"}

    async def get_logs(self, pm_id: int | None = None, lines: int = 100) -> str:
        """Obtiene los logs de un proceso."""
        try:
            cmd = [
                "pm2",
                "logs",
                str(pm_id) if pm_id else "all",
                "--lines",
                str(lines),
                "--nostream",
            ]
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            return (stdout + stderr).decode()
        except Exception:
            return ""

    async def get_status(self) -> dict[str, str | int]:
        """Obtiene el estado de PM2."""
        try:
            result = await asyncio.create_subprocess_exec(
                "pm2",
                "ping",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()

            processes = await self.list_processes()

            return {
                "status": "online" if result.returncode == 0 else "offline",
                "processes": len(processes),
            }
        except Exception:
            return {"status": "offline", "processes": 0}

    @staticmethod
    def _format_memory(bytes_value: int) -> str:
        """Formatea bytes a MB/GB."""
        mb = bytes_value / (1024 * 1024)
        if mb > 1024:
            return f"{mb / 1024:.1f}GB"
        return f"{mb:.0f}MB"


pm2_service = PM2Service()
