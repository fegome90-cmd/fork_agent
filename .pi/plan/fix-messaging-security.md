# Plan: fix-messaging-security (v2 — post-audit)

## Auditoría aplicada
- patch-dedup-1 ✅ logs estructurados WARNING con campos (session, reason, msg_id)
- patch-dedup-2 ✅ quality gates = uv run ruff + uv run mypy (no bun)
- patch-dedup-3 ✅ criterios medibles por entregable
- patch-dedup-4 ✅ 1 fix = 1 commit atómico
- patch-dedup-5 ✅ cobertura mínima confirmada

## Archivos relevantes

- `src/infrastructure/tmux_orchestrator/__init__.py` — `_send_keys()`, `send_message()`, `send_command()`
- `src/application/services/messaging/agent_messenger.py` — `send()`, `broadcast()`
- `src/application/services/agent/agent_manager.py` — `TmuxAgent.send_input()`
- `src/application/services/messaging/message_protocol.py` — `encode_message()`, `decode_message()`

## Fix 1 — Sanitización en `_send_keys` y `send_input`

**Archivos:** `tmux_orchestrator/__init__.py`, `agent_manager.py`

```python
import re

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

def _sanitize_tmux_text(text: str) -> str:
    """Strip control chars and ANSI sequences. Collapse newlines to space."""
    text = _ANSI_ESCAPE.sub("", text)
    text = _CONTROL_CHARS.sub("", text)
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = text.strip()
    if not text:
        raise ValueError("sanitized text is empty")
    return text
```

Aplicar en `_send_keys()` antes de pasar a subprocess.
Aplicar en `TmuxAgent.send_input()` (misma lógica).
`send_command()` usa la misma ruta → queda cubierto.

## Fix 2 — Loop guard: `is_self_message`

**Archivo:** `message_protocol.py`

```python
def is_self_message(msg: AgentMessage, self_agent_id: str) -> bool:
    """Return True if the message was sent by this agent (loop guard)."""
    return msg.from_agent == self_agent_id
```

Uso por el consumidor del mensaje antes de procesarlo:
```python
if is_self_message(msg, my_id):
    logger.warning(
        "loop guard triggered: discarding self-message",
        extra={"msg_id": msg.id, "agent": my_id, "reason": "self_loop"},
    )
    return
```

## Fix 3 — Allowlist en `broadcast` con logs estructurados

**Archivo:** `agent_messenger.py`

```python
ALLOWED_SESSION_PREFIXES: tuple[str, ...] = ("fork-", "agent-")

def _is_allowed_target(session_name: str) -> bool:
    return any(session_name.startswith(p) for p in ALLOWED_SESSION_PREFIXES)
```

En `broadcast()`, antes de enviar a cada sesión:
```python
if not _is_allowed_target(session.name):
    logger.warning(
        "broadcast skip: session not in allowlist",
        extra={
            "session": session.name,
            "reason": "not_allowlisted",
            "allowed_prefixes": list(ALLOWED_SESSION_PREFIXES),
        },
    )
    continue
```

## Tests a agregar (commit separado)

- `test_sanitize_tmux_text_strips_newlines` — `\n` en texto → espacio
- `test_sanitize_tmux_text_strips_ansi` — `\x1b[31m` → eliminado
- `test_sanitize_tmux_text_strips_control_chars` — `\x03`, `\x1b` → eliminado
- `test_sanitize_tmux_text_empty_raises` — resultado vacío → ValueError
- `test_is_self_message_true` — from_agent == self_id → True
- `test_is_self_message_false` — from_agent != self_id → False
- `test_broadcast_skips_non_allowlisted` — sesión `personal:0` → skip
- `test_broadcast_logs_warning_on_skip` — capturar logger.warning con campos

## Commits atómicos

1. `fix(security): sanitize tmux text to prevent prompt injection`
2. `fix(security): add loop guard is_self_message to message protocol`
3. `fix(security): add session allowlist to broadcast`
4. `test(security): add tests for injection, loop guard, allowlist`

## Criterios de aceptación

- [ ] `_send_keys("session", 0, "hello\nrm -rf")` → envía `"hello rm -rf"` (sin newline)
- [ ] `_send_keys("session", 0, "\x1b[31m")` → ValueError (vacío tras sanitizar)
- [ ] `is_self_message(msg, msg.from_agent)` → True
- [ ] `broadcast()` con sesión `personal:0` → 0 enviados, 1 WARNING en logs
- [ ] `uv run mypy` PASS (strict)
- [ ] `uv run ruff check` PASS
- [ ] `pytest tests/unit/application/services/messaging/` PASS (58 + nuevos)
