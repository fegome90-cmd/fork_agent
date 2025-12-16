#!/usr/bin/env python3
"""
Wrapper seguro para simular o ejecutar comandos de shell desde el repo.
- Soporta --dry-run para solo mostrar lo que haría.
- Por seguridad, evita ejecutar comandos listados en DENY_LIST.
"""
import argparse
import shlex
import subprocess
import sys

DENY_LIST = ["rm -rf /", "rm -rf --no-preserve-root /", ":(){ :|:& };:"]


def is_denied(cmd: str) -> bool:
    for bad in DENY_LIST:
        if bad in cmd:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Ejecuta comandos con modo seguro (dry-run).")
    parser.add_argument("--cmd", required=True, help="Comando a ejecutar (entre comillas).")
    parser.add_argument("--dry-run", action="store_true", help="No ejecutar, solo mostrar.")
    parser.add_argument("--shell", action="store_true", help="Ejecutar en shell (más riesgo).")
    args = parser.parse_args()

    cmd = args.cmd

    if is_denied(cmd):
        print("ERROR: comando prohibido por la política local.")
        sys.exit(2)

    print(f"COMANDO: {cmd}")
    if args.dry_run:
        print("Modo dry-run: no se ejecuta.")
        return

    if args.shell:
        res = subprocess.run(cmd, shell=True)
        sys.exit(res.returncode)

    parts = shlex.split(cmd)
    res = subprocess.run(parts)
    sys.exit(res.returncode)


if __name__ == '__main__':
    main()
