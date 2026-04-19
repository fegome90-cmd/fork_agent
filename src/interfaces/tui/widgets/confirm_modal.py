"""Yes/No confirmation modal dialog."""

from __future__ import annotations

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmModal(ModalScreen[bool]):
    """Yes/No confirmation dialog that dismisses with True/False."""

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self):
        with Vertical(classes="modal-content"):
            yield Static(self._message)
            with Horizontal(classes="modal-buttons"):
                yield Button("Yes", id="confirm-yes", variant="primary")
                yield Button("No", id="confirm-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-yes":
            self.dismiss(True)
        elif event.button.id == "confirm-no":
            self.dismiss(False)

    def key_escape(self) -> None:
        self.dismiss(False)
