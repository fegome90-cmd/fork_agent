"""Topic mapping for event types.

Maps event class names to topic strings for the async message broker.
Central registry so publishers and subscribers agree on topic names.
"""

from __future__ import annotations

from src.application.services.orchestration.events import (
    FileWrittenEvent,
    SessionStartEvent,
    SubagentStartEvent,
    SubagentStopEvent,
    ToolPreExecutionEvent,
    TrifectaIndexEvent,
    UserCommandEvent,
    WorkflowExecuteCompleteEvent,
    WorkflowExecuteStartEvent,
    WorkflowOutlineCompleteEvent,
    WorkflowOutlineStartEvent,
    WorkflowPhaseChangeEvent,
    WorkflowShipCompleteEvent,
    WorkflowShipStartEvent,
    WorkflowVerifyCompleteEvent,
    WorkflowVerifyStartEvent,
    WorktreeCreatedEvent,
    WorktreeMergedEvent,
    WorktreeRemovedEvent,
)

# Topics
TOPIC_USER_COMMAND = "user.command"
TOPIC_FILE_WRITTEN = "file.written"
TOPIC_TOOL_PRE_EXEC = "tool.pre_exec"
TOPIC_SESSION_START = "session.start"
TOPIC_SUBAGENT_START = "subagent.start"
TOPIC_SUBAGENT_STOP = "subagent.stop"

TOPIC_WORKFLOW_PHASE = "workflow.phase"
TOPIC_WORKFLOW_OUTLINE_START = "workflow.outline.start"
TOPIC_WORKFLOW_OUTLINE_COMPLETE = "workflow.outline.complete"
TOPIC_WORKFLOW_EXECUTE_START = "workflow.execute.start"
TOPIC_WORKFLOW_EXECUTE_COMPLETE = "workflow.execute.complete"
TOPIC_WORKFLOW_VERIFY_START = "workflow.verify.start"
TOPIC_WORKFLOW_VERIFY_COMPLETE = "workflow.verify.complete"
TOPIC_WORKFLOW_SHIP_START = "workflow.ship.start"
TOPIC_WORKFLOW_SHIP_COMPLETE = "workflow.ship.complete"

TOPIC_WORKTREE_CREATED = "worktree.created"
TOPIC_WORKTREE_MERGED = "worktree.merged"
TOPIC_WORKTREE_REMOVED = "worktree.removed"
TOPIC_TRIFECTA_INDEX = "trifecta.index"

# Registry: event class -> topic string
# Used for dynamic dispatch when event type is known at runtime.
EVENT_TOPIC_MAP: dict[type, str] = {
    UserCommandEvent: TOPIC_USER_COMMAND,
    FileWrittenEvent: TOPIC_FILE_WRITTEN,
    ToolPreExecutionEvent: TOPIC_TOOL_PRE_EXEC,
    SessionStartEvent: TOPIC_SESSION_START,
    SubagentStartEvent: TOPIC_SUBAGENT_START,
    SubagentStopEvent: TOPIC_SUBAGENT_STOP,
    WorkflowPhaseChangeEvent: TOPIC_WORKFLOW_PHASE,
    WorkflowOutlineStartEvent: TOPIC_WORKFLOW_OUTLINE_START,
    WorkflowOutlineCompleteEvent: TOPIC_WORKFLOW_OUTLINE_COMPLETE,
    WorkflowExecuteStartEvent: TOPIC_WORKFLOW_EXECUTE_START,
    WorkflowExecuteCompleteEvent: TOPIC_WORKFLOW_EXECUTE_COMPLETE,
    WorkflowVerifyStartEvent: TOPIC_WORKFLOW_VERIFY_START,
    WorkflowVerifyCompleteEvent: TOPIC_WORKFLOW_VERIFY_COMPLETE,
    WorkflowShipStartEvent: TOPIC_WORKFLOW_SHIP_START,
    WorkflowShipCompleteEvent: TOPIC_WORKFLOW_SHIP_COMPLETE,
    WorktreeCreatedEvent: TOPIC_WORKTREE_CREATED,
    WorktreeMergedEvent: TOPIC_WORKTREE_MERGED,
    WorktreeRemovedEvent: TOPIC_WORKTREE_REMOVED,
    TrifectaIndexEvent: TOPIC_TRIFECTA_INDEX,
}


def topic_for_event(event: object) -> str | None:
    """Resolve the topic string for an event instance.

    Checks by exact type first, then by MRO to handle subclasses.
    Returns None if no topic is registered.
    """
    event_type = type(event)
    topic = EVENT_TOPIC_MAP.get(event_type)
    if topic is not None:
        return topic

    # Fallback: check MRO for registered parent types
    for cls in event_type.__mro__[1:]:  # skip the type itself
        topic = EVENT_TOPIC_MAP.get(cls)
        if topic is not None:
            return topic

    return None
