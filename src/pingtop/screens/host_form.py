from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from pingtop.widgets.trend import render_trend_legend


class HostFormScreen(ModalScreen[str | None]):
    def __init__(self, title: str, value: str = "") -> None:
        super().__init__()
        self.dialog_title = title
        self.initial_value = value

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(self.dialog_title, classes="dialog-title")
            yield Input(value=self.initial_value, placeholder="Host or IP", id="host-target")
            yield Label("", id="dialog-error")
            with Horizontal(classes="dialog-actions"):
                yield Button("Cancel", id="cancel")
                yield Button("Save", variant="primary", id="submit")

    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#submit")
    @on(Input.Submitted, "#host-target")
    def on_submit(self) -> None:
        value = self.query_one("#host-target", Input).value.strip()
        if not value:
            self.query_one("#dialog-error", Label).update("Host cannot be empty.")
            return
        self.dismiss(value)


class ConfirmScreen(ModalScreen[bool]):
    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(self.message, classes="dialog-title")
            with Horizontal(classes="dialog-actions"):
                yield Button("Cancel", id="cancel")
                yield Button("Delete", variant="error", id="confirm")

    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#confirm")
    def on_confirm(self) -> None:
        self.dismiss(True)


class HelpScreen(ModalScreen[None]):
    BINDINGS = [
        ("escape", "dismiss_screen", "Close"),
        ("q", "dismiss_screen", "Close"),
        ("h", "dismiss_screen", "Close"),
    ]
    HELP_TEXT = "\n".join(
        [
            "a   add host",
            "e   edit selected host",
            "d   delete selected host",
            "i   show or hide details",
            "h   open or close help",
            "space   pause/resume selected host",
            "p   pause/resume all hosts",
            "r   reset selected host statistics",
            "ctrl+r   reset all host statistics",
            "H   sort by Host",
            "G   sort by IP",
            "S   sort by Seq",
            "R   sort by RTT",
            "I   sort by Min",
            "A   sort by Avg",
            "M   sort by Max",
            "T   sort by StdDev",
            "L   sort by Loss",
            "P   sort by Loss%",
            "U   sort by State",
            "W   sort by Trend",
            "press the same sort key again to reverse order",
            "q   quit",
        ]
    )

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Help", classes="dialog-title")
            yield Static(self.HELP_TEXT)
            yield Static(render_trend_legend(), id="trend-legend")
            yield Button("Close", variant="primary", id="close")

    @on(Button.Pressed, "#close")
    def on_close(self) -> None:
        self.dismiss(None)

    def action_dismiss_screen(self) -> None:
        self.dismiss(None)
