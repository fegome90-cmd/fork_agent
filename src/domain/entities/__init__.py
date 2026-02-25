"""Entidades del dominio."""

from src.domain.entities.message import AgentMessage, MessageType
from src.domain.entities.observation import Observation
from src.domain.entities.terminal import PlatformType, TerminalConfig, TerminalResult
from src.domain.entities.user_decision import DecisionStatus, UserDecision

__all__ = [
    "AgentMessage",
    "MessageType",
    "Observation",
    "PlatformType",
    "TerminalConfig",
    "TerminalResult",
    "DecisionStatus",
    "UserDecision",
]

from src.domain.entities.message import AgentMessage, MessageType
from src.domain.entities.observation import Observation
from src.domain.entities.terminal import PlatformType, TerminalConfig, TerminalResult

__all__ = [
    "AgentMessage",
    "MessageType",
    "Observation",
    "PlatformType",
    "TerminalConfig",
    "TerminalResult",
]
