"""Configuración del workspace desde archivo YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, field_validator


class WorkspaceConfigModel(BaseModel):
    """Configuración del workspace."""

    default_layout: str = "NESTED"
    auto_cleanup: bool = False
    hooks_dir: Path | None = None

    model_config = {"frozen": True}

    @field_validator("default_layout")
    @classmethod
    def validate_layout(cls, v: str) -> str:
        valid_layouts = {"NESTED", "OUTER_NESTED", "SIBLING"}
        if v.upper() not in valid_layouts:
            raise ValueError(f"default_layout must be one of {valid_layouts}")
        return v.upper()


class TmuxConfigModel(BaseModel):
    """Configuración de tmux."""

    session_prefix: str = "fork-"
    attach_on_create: bool = True

    model_config = {"frozen": True}


class ForkAgentConfig(BaseModel):
    """Configuración principal de fork_agent."""

    workspace: WorkspaceConfigModel = WorkspaceConfigModel()
    tmux: TmuxConfigModel = TmuxConfigModel()

    model_config = {"frozen": True}

    @classmethod
    def _find_config_file(cls) -> Path | None:
        """Busca el archivo de configuración en los paths estándar.
        
        Returns:
            Ruta al archivo de configuración o None si no existe.
        """
        # Path 1: ./fork_agent.yaml (repo root)
        repo_root = Path.cwd() / ".fork_agent.yaml"
        if repo_root.exists():
            return repo_root
        
        # Path 2: ~/.config/fork_agent.yaml (user home)
        user_config = Path.home() / ".config" / "fork_agent.yaml"
        if user_config.exists():
            return user_config
        
        return None

    @classmethod
    def load(cls, path: Path | None = None) -> Self:
        """Carga configuración desde archivo o retorna valores por defecto.
        
        Args:
            path: Ruta opcional al archivo de configuración.
            
        Returns:
            Instancia de ForkAgentConfig con la configuración cargada.
        """
        config_path = path or cls._find_config_file()
        
        if config_path is None or not config_path.exists():
            return cls()
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            return cls(**data)
        except (yaml.YAMLError, ValueError) as e:
            # Si hay error al parsear, retornar defaults
            return cls()

    def save(self, path: Path) -> None:
        """Guarda la configuración a un archivo.
        
        Args:
            path: Ruta donde guardar el archivo de configuración.
        """
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "workspace": {
                "default_layout": self.workspace.default_layout,
                "auto_cleanup": self.workspace.auto_cleanup,
                "hooks_dir": str(self.workspace.hooks_dir) if self.workspace.hooks_dir else None,
            },
            "tmux": {
                "session_prefix": self.tmux.session_prefix,
                "attach_on_create": self.tmux.attach_on_create,
            },
        }
        
        # Remove None values for cleaner YAML
        if data["workspace"]["hooks_dir"] is None:
            del data["workspace"]["hooks_dir"]
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
