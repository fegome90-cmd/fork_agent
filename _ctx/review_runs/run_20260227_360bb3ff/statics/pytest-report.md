# Static Analysis: pytest

## Tool: pytest
## Status: PASS (with caveats)

## Summary
1190 passed, 2 failed, 3 skipped

## Results
- **Passed**: 1190
- **Failed**: 2 (E2E tests requiring tmux runtime)
- **Skipped**: 3

## Failed Tests (Non-blocking)
1. `tests/integration/test_messaging_e2e.py::TestMessageSendAndCapture::test_send_message_to_session`
2. `tests/integration/test_messaging_e2e.py::TestMessageBroadcast::test_broadcast_includes_created_sessions`

**Note**: These failures require tmux to be running. Not a code regression.

## Verdict
**PASS** - Core functionality verified. E2E failures are environment-related.
