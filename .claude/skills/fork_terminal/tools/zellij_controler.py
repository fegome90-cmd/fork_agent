#!/usr/bin/env python3

"""

Zellij Controler

- Generate a layout.kdl (KDL = KDL) with M panes running commands (bash -lc "...")
- Launches zellij in a *version-tolerant* way( handles CLI differences).
- Optionally fork a new MacOs Terminal window via osascript.

Docs references:
- Layouts + applying layouts: https://zellij.dev/documentation/layouts.html
- Layout syntax (KDL), command/args/cwd/stacked: https://zellij.dev/documentation/creating-a-layout.html
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional



# ----------------------------
# Helpers: escaping
# ----------------------------

def _kdl_escape(s: str) -> str:
    """Escape a string for KDL quoted string."""
    return (
        s.replace("\\", "\\\\")
        .replace("\"", "\\\"")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )

def _sh_quote(s: str) -> str:
    """Single-quote for bash safely."""
    return "'" + s.replace("'", "'\''") + "'"

def _escape_applescript_string(s: str) -> str:
    """Escape for AppleScript string literal inside osascript."""
    return (
        s.replace("\\", "\\\\")
        .replace("\"", "\\\"")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def validate_output_dir(provided_path: str, base_allowlist: list[Path] = None) -> Path:
    """
    Valida y sanitiza una ruta de directorio de salida para prevenir Path Traversal.
    
    Args:
        provided_path: La ruta proporcionada por el usuario o configuración.
        base_allowlist: Lista de rutas base permitidas. 
                        Si es None, por defecto solo permite dentro de Path.home().
    
    Returns:
        Path: Objeto Path resuelto y validado.
    """
    if not provided_path:
        raise ValueError("Provided path is empty")

    # 1. Normalización y Resolución Absoluta
    # expanduser() maneja ~, resolve() elimina .. y symlinks
    path = Path(provided_path).expanduser().resolve()

    # 2. Definir allowlist (Default: Home del usuario)
    if base_allowlist is None:
        base_allowlist = [Path.home().resolve()]
    else:
        base_allowlist = [p.expanduser().resolve() for p in base_allowlist]

    # 3. Verificación de Prefijo (Chroot Simulado)
    is_allowed = False
    for base in base_allowlist:
        try:
            path.relative_to(base)
            is_allowed = True
            break
        except ValueError:
            continue

    if not is_allowed:
        raise ValueError(f"Path Traversal detectado o ruta fuera de rangos permitidos: {path}")

    # 4. Verificación de Caracteres y Seguridad
    if '\0' in str(path):
        raise ValueError("Null byte injection detected")

    # 5. Verificación de Permisos y Tipo
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"La ruta existe y no es un directorio: {path}")
        if not os.access(path, os.W_OK):
            raise PermissionError(f"Sin permisos de escritura en el directorio: {path}")
    else:
        # Verificar que el padre sea escribible si el directorio no existe
        parent = path.parent
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent
        if not os.access(parent, os.W_OK):
            raise PermissionError(f"Sin permisos para crear el directorio en: {parent}")

    return path


# ----------------------------
# Spec
# ----------------------------

@dataclass(frozen=True)
class PaneSpec:
    """Specification for a zellij layout."""
    command: str
    name: str
    args: List[str]
    cwd: Optional[str] = None
    stacked: bool = False
    start_suspended: bool = False
    close_on_exit: bool = False


# ----------------------------
# Layout generator (KDL)
# ----------------------------

def build_layout_kdl(
    panes: List[PaneSpec],
    *,
    root_split_direction: str = "vertical",  # "vertical" or "horizontal"
    stacked: bool = False,
    tab_name: str = "agents",
    include_compact_bar: bool = True,
) -> str:
    """
    Generates a KDL layout.
    - For many panes, consider stacked=True (keeps panes readable).
    - Uses command="bash" with args inside child braces (required by zellij). :contentReference[oaicite:1]{index=1}
    """
    if root_split_direction not in ("vertical", "horizontal"):
        raise ValueError("root_split_direction must be 'vertical' or 'horizontal'")

    def pane_node(p: PaneSpec) -> str:
        props = []
        if p.name:
            props.append(f'name="{_kdl_escape(p.name)}"')
        if p.cwd:
            props.append(f'cwd="{_kdl_escape(p.cwd)}"')
        if p.start_suspended:
            props.append("start_suspended=true")
        if p.close_on_exit:
            props.append("close_on_exit=true")

        # Run via bash -lc "<cmd>" to keep behavior consistent across shells.
        # args must be inside pane braces. :contentReference[oaicite:2]{index=2}
        inner = f'''
            command "bash"
            args "-lc" "{_kdl_escape(p.command)}"
        '''.rstrip()

        props_str = (" " + " ".join(props)) if props else ""
        return f'''
        pane{props_str} {{
{indent(inner, 12)}
        }}
        '''.rstrip()

    body_children = "\n".join(pane_node(p) for p in panes)

    if stacked:
        # Stacked panes keep 1 expanded pane + titles for others. :contentReference[oaicite:3]{index=3}
        root = f'''
    pane stacked=true {{
{indent(body_children, 8)}
    }}
        '''.rstrip()
    else:
        root = f'''
    pane split_direction="{root_split_direction}" {{
{indent(body_children, 8)}
    }}
        '''.rstrip()

    # Optional compact bar plugin
    compact_bar = ""
    if include_compact_bar:
        compact_bar = '''
    pane size=1 borderless=true {
        plugin location="zellij:compact-bar"
    }
        '''.rstrip()

    kdl = f'''
layout {{
    tab name="{_kdl_escape(tab_name)}" {{
{indent(root, 4)}
{indent(compact_bar, 4) if compact_bar else ""}
    }}
}}
    '''.strip() + "\n"
    return kdl


def indent(s: str, n: int) -> str:
    pad = " " * n
    return "\n".join(pad + line if line.strip() else line for line in s.splitlines())


# ----------------------------
# Zellij launch (version-tolerant)
# ----------------------------

def build_zellij_launch_command(session_name: str, layout_path: str) -> str:
    """
    Zellij CLI changed around how session naming + layout launching works.
    This command uses a runtime feature-detect on `zellij --help` to pick the best invocation.

    We prefer:
      - If `--new-session-with-layout` exists: use it + -s/--session.
      - Else try: zellij -s NAME --layout PATH
      - Else fallback: zellij --layout PATH (random session name) and then attach/create.

    Note: --layout is the documented way to apply a layout. :contentReference[oaicite:4]{index=4}
    """
    s = _sh_quote(session_name)
    l = _sh_quote(layout_path)

    # This is a single bash snippet so you can pass it to your fork_terminal safely.
    cmd = f"""
bash -lc '
set -e
HELP="$(zellij --help 2>/dev/null || true)"
if echo "$HELP" | grep -q -- "--new-session-with-layout"; then
  # Newer behavior (documented in issues/discussions)
  exec zellij --new-session-with-layout {l} -s {s}
elif echo "$HELP" | grep -q -- "--layout"; then
  # Try session flag + layout (varies by version)
  exec zellij -s {s} --layout {l} || exec zellij --layout {l}
else
  exec zellij
fi
'
""".strip()
    return cmd


# ----------------------------
# Forking (macOS Terminal) + direct launch
# ----------------------------

def fork_terminal_macos(command: str) -> str:
    safe_cmd = _escape_applescript_string(command)
    script = f'tell application "Terminal" to do script "{safe_cmd}"'
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if res.returncode != 0:
        return f"osascript error: {res.stderr.strip()}"
    return res.stdout.strip()


def launch_zellij_session(
    panes: List[PaneSpec],
    *,
    session_name: str,
    out_dir: str,
    stacked: Optional[bool] = None,
    root_split_direction: str = "vertical",
    fork_new_terminal: bool = True,
) -> str:
    # Validar directorio de salida para prevenir Path Traversal
    out = validate_output_dir(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Default policy: stack if too many panes
    if stacked is None:
        stacked = len(panes) > 4

    layout_kdl = build_layout_kdl(
        panes,
        root_split_direction=root_split_direction,
        stacked=stacked,
        tab_name="fork-agents",
        include_compact_bar=True,
    )

    layout_path = out / f"layout_{session_name}_{int(time.time())}.kdl"
    layout_path.write_text(layout_kdl, encoding="utf-8")

    launch_cmd = build_zellij_launch_command(session_name, str(layout_path))

    if not fork_new_terminal:
        # If you're already in a terminal (eg. IDE terminal), you can just print and run it.
        return launch_cmd

    system = platform.system()
    if system == "Darwin":
        return fork_terminal_macos(launch_cmd)
    elif system == "Windows":
        # Best effort. If user has zellij installed on Windows.
        subprocess.Popen(f'start cmd /k {launch_cmd}', shell=True)
        return "Started zellij (Windows)."
    else:
        # Linux: launch in current process if GUI terminal is unknown.
        subprocess.Popen(launch_cmd, shell=True)
        return "Started zellij (Linux)."


# ----------------------------
# CLI
# ----------------------------

def parse_pane_arg(s: str) -> PaneSpec:
    """
    Format:
      --pane "NAME::CMD"
      --pane "NAME::CMD::CWD"
    """
    parts = s.split("::")
    if len(parts) < 2:
        raise ValueError("Pane must be 'NAME::CMD' or 'NAME::CMD::CWD'")
    name = parts[0].strip()
    cmd = parts[1].strip()
    cwd = parts[2].strip() if len(parts) >= 3 and parts[2].strip() else None
    return PaneSpec(command=cmd, name=name, args=[], cwd=cwd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True, help="Session name")
    ap.add_argument("--out-dir", default="~/.cache/hemdov/zellij", help="Where to write layout files")
    ap.add_argument("--pane", action="append", default=[], help='Pane spec: "NAME::CMD" or "NAME::CMD::CWD"')
    ap.add_argument("--stacked", action="store_true", help="Force stacked panes")
    ap.add_argument("--no-fork", action="store_true", help="Do not fork a new terminal; print launch command")
    ap.add_argument("--split", default="vertical", choices=["vertical", "horizontal"], help="Root split direction")
    args = ap.parse_args()

    panes = [parse_pane_arg(p) for p in args.pane]
    if not panes:
        print("ERROR: Provide at least one --pane", file=sys.stderr)
        sys.exit(2)

    result = launch_zellij_session(
        panes,
        session_name=args.session,
        out_dir=args.out_dir,
        stacked=True if args.stacked else None,
        root_split_direction=args.split,
        fork_new_terminal=not args.no_fork,
    )
    print(result)


if __name__ == "__main__":
    main()