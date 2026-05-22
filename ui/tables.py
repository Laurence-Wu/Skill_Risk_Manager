from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import customtkinter as ctk

from ui.models import LogEntry
from ui.components import BaseButton, BaseComponent


class BaseTable(BaseComponent, ctk.CTkScrollableFrame):
    def __init__(self, master, columns: list[str], *, empty_text: str = "No records to display.") -> None:
        self._init_component()
        super().__init__(
            master,
            fg_color=self.theme.color("surface"),
            border_color=self.theme.color("border"),
            border_width=1,
            corner_radius=self.theme.spacing("radius_card"),
        )
        self.columns = columns
        self.empty_text = empty_text
        self.selected_row: int | None = None
        self.row_frames: list[ctk.CTkFrame] = []
        self.row_kinds: list[str] = []
        self._rows: list[dict[str, object]] = []
        self._actions: list[TableAction] | None = None
        self._page_size = 90
        self._visible_limit = self._page_size
        self._last_signature: tuple | None = None
        self.set_rows([])

    def set_rows(
        self,
        rows: list[dict[str, object]],
        actions: list["TableAction"] | None = None,
        *,
        page_size: int = 90,
        preserve_visible_limit: bool = False,
        lazy: bool = False,
    ) -> None:
        page_size = _effective_page_size(page_size, lazy)
        signature = _rows_signature(rows, actions, page_size)
        if signature == self._last_signature and self.winfo_children():
            return
        self._update_paging(rows, actions, signature, page_size, preserve_visible_limit)
        self._clear_rows()
        total_columns = self._total_columns(actions)
        self._render_headers(actions, total_columns)
        if not rows:
            self._render_empty(total_columns)
            return
        visible_rows = rows[: self._visible_limit]
        self._render_data_rows(visible_rows, actions, total_columns)
        if len(rows) > len(visible_rows):
            self._render_footer(len(visible_rows), len(rows), total_columns)

    def _update_paging(
        self,
        rows: list[dict[str, object]],
        actions: list["TableAction"] | None,
        signature: tuple,
        page_size: int,
        preserve_visible_limit: bool,
    ) -> None:
        if preserve_visible_limit:
            self._visible_limit = max(self._visible_limit, page_size)
        elif self._last_signature and signature == self._last_signature:
            self._visible_limit = min(max(self._visible_limit, page_size), max(len(rows), page_size))
        else:
            self._visible_limit = page_size
        self._rows = rows
        self._actions = actions
        self._page_size = page_size
        self._last_signature = signature

    def _clear_rows(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self.row_frames = []
        self.row_kinds = []
        self.selected_row = None

    def _total_columns(self, actions: list["TableAction"] | None) -> int:
        total_columns = len(self.columns) + (1 if actions else 0)
        for column_index in range(total_columns):
            self.grid_columnconfigure(column_index, weight=1 if column_index == 0 else 0)
        return total_columns

    def _render_headers(self, actions: list["TableAction"] | None, total_columns: int) -> None:
        for column_index, column in enumerate(self.columns):
            ctk.CTkLabel(
                self,
                text=column,
                font=self.theme.font("caption"),
                text_color=self.theme.color("text_muted"),
                anchor="w",
            ).grid(row=0, column=column_index, sticky="ew", padx=8, pady=7)
        if actions:
            action_width = sum(_button_width(label_text) + 4 for label_text, _callback, _variant in actions)
            ctk.CTkLabel(self, text="", width=max(190, action_width)).grid(
                row=0,
                column=total_columns - 1,
                sticky="ew",
                padx=8,
                pady=7,
            )

    def _render_empty(self, total_columns: int) -> None:
        ctk.CTkLabel(
            self,
            text=self.empty_text,
            font=self.theme.font("small"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        ).grid(row=1, column=0, columnspan=total_columns, sticky="ew", padx=8, pady=12)

    def _render_data_rows(
        self,
        rows: list[dict[str, object]],
        actions: list["TableAction"] | None,
        total_columns: int,
    ) -> None:
        for row_index, row in enumerate(rows, start=1):
            row_frame = self._new_row_frame(row, row_index, total_columns)
            self._render_row_cells(row_frame, row, row_index)
            if actions:
                self._render_row_actions(row_frame, row, actions)

    def _new_row_frame(self, row: dict[str, object], row_index: int, total_columns: int) -> ctk.CTkFrame:
        row_bg = self._row_background(row, row_index)
        row_frame = ctk.CTkFrame(self, fg_color=row_bg, corner_radius=0, height=self.theme.spacing("table_row_height"))
        row_frame.grid(row=row_index, column=0, columnspan=total_columns, sticky="ew", padx=5, pady=1)
        row_frame.grid_columnconfigure(0, weight=1)
        self.row_frames.append(row_frame)
        self.row_kinds.append(str(row.get("_row_kind", "")).lower())
        row_frame.bind("<Button-1>", lambda _event, index=row_index - 1: self._select_row(index))
        return row_frame

    def _render_row_cells(self, row_frame: ctk.CTkFrame, row: dict[str, object], row_index: int) -> None:
        for column_index, column in enumerate(self.columns):
            value = _truncate(str(row.get(column, "")), 72 if column.lower() == "path" else 36)
            label = ctk.CTkLabel(
                row_frame,
                text=value,
                font=self.theme.font("small"),
                text_color=self.theme.color("text_secondary"),
                anchor="w",
                height=self.theme.spacing("table_row_height"),
            )
            label.grid(row=0, column=column_index, sticky="ew", padx=8)
            label.bind("<Button-1>", lambda _event, index=row_index - 1: self._select_row(index))

    def _render_row_actions(
        self,
        row_frame: ctk.CTkFrame,
        row: dict[str, object],
        actions: list["TableAction"],
    ) -> None:
        actions_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=len(self.columns), sticky="e", padx=4)
        for action_index, (label_text, callback, variant) in enumerate(actions):
            BaseButton(
                actions_frame,
                label_text,
                command=lambda selected=row, action=callback: action(selected),
                variant=variant,
                width=_button_width(label_text),
            ).grid(row=0, column=action_index, padx=2)

    def _render_footer(self, visible_count: int, total_count: int, total_columns: int) -> None:
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=visible_count + 1, column=0, columnspan=total_columns, sticky="ew", padx=8, pady=10)
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer,
            text=f"Showing {visible_count} of {total_count} records",
            font=self.theme.font("caption"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        BaseButton(footer, "Load More", self._load_more, width=104).grid(row=0, column=1, sticky="e")

    def _load_more(self) -> None:
        self._visible_limit += self._page_size
        self._last_signature = None
        self.set_rows(self._rows, self._actions, page_size=self._page_size, preserve_visible_limit=True)

    def _select_row(self, index: int) -> None:
        self.selected_row = index
        for row_index, frame in enumerate(self.row_frames):
            frame.configure(
                fg_color=self.theme.color("surface_selected")
                if row_index == index
                else self._row_background({"_row_kind": self.row_kinds[row_index]}, row_index + 1)
            )

    def _row_background(self, row: dict[str, object], row_index: int) -> str:
        row_kind = str(row.get("_row_kind", "")).lower()
        if row_kind == "critical":
            return "#3A1F2A"
        if row_kind == "high":
            return "#3A2C1F"
        return self.theme.color("surface_raised") if row_index % 2 else self.theme.color("surface")


class LogPanel(BaseComponent, ctk.CTkScrollableFrame):
    def __init__(self, master) -> None:
        self._init_component()
        super().__init__(
            master,
            fg_color=self.theme.color("surface"),
            border_color=self.theme.color("border"),
            border_width=1,
            corner_radius=self.theme.spacing("radius_card"),
        )
        self.grid_columnconfigure(0, weight=1)
        self._last_signature: tuple | None = None

    def set_logs(self, logs: list[LogEntry], level_filter: str = "all", *, lazy: bool = False) -> None:
        visible_limit = 50 if lazy else 120
        signature = _logs_signature(logs, level_filter, visible_limit)
        if signature == self._last_signature and self.winfo_children():
            return
        self._last_signature = signature
        for child in self.winfo_children():
            child.destroy()
        visible_logs = [log for log in logs if level_filter == "all" or log.level == level_filter]
        if not visible_logs:
            self._render_empty()
            return
        for row_index, log in enumerate(visible_logs[-visible_limit:]):
            self._render_log(row_index, log)

    def _render_empty(self) -> None:
        ctk.CTkLabel(
            self,
            text="No events yet.",
            font=self.theme.font("small"),
            text_color=self.theme.color("text_muted"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=10, pady=10)

    def _render_log(self, row_index: int, log: LogEntry) -> None:
        color = {
            "info": self.theme.color("status_info"),
            "warning": self.theme.color("status_warning"),
            "error": self.theme.color("status_danger"),
            "success": self.theme.color("status_success"),
        }.get(log.level, self.theme.color("text_secondary"))
        timestamp = datetime.fromtimestamp(log.timestamp).strftime("%H:%M:%S")
        ctk.CTkLabel(
            self,
            text=f"{timestamp}  {log.level.upper():7}  {log.message}",
            font=self.theme.font("small"),
            text_color=color,
            anchor="w",
        ).grid(row=row_index, column=0, sticky="ew", padx=10, pady=2)


TableAction = tuple[str, Callable[[dict[str, object]], None], str]


def _button_width(label: str) -> int:
    return max(76, len(label) * 7 + 26)


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


def _rows_signature(
    rows: list[dict[str, object]],
    actions: list[TableAction] | None,
    page_size: int | None = None,
) -> tuple:
    row_count = len(rows)
    sample_rows = rows[:3] + rows[-3:] if row_count > 6 else rows
    sample_keys = tuple(_row_key(row) for row in sample_rows)
    action_keys = tuple(f"{label}:{variant}" for label, _callback, variant in actions or [])
    return (page_size, row_count, sample_keys, action_keys)


def _row_key(row: dict[str, object]) -> str:
    return "|".join(
        [
            str(row.get("Path") or row.get("Name") or row.get("_record") or ""),
            str(row.get("Risk", "")),
            str(row.get("Score", "")),
            str(row.get("Status", "")),
            str(row.get("Action", "")),
            str(row.get("Top Finding", "")),
            str(row.get("Summary", "")),
        ]
    )


def _logs_signature(logs: list[LogEntry], level_filter: str, visible_limit: int = 120) -> tuple:
    visible_logs = [log for log in logs if level_filter == "all" or log.level == level_filter]
    if not visible_logs:
        return (level_filter, visible_limit, 0)
    last_log = visible_logs[-1]
    return (level_filter, visible_limit, len(visible_logs), last_log.timestamp, last_log.level, last_log.message)


def _effective_page_size(page_size: int, lazy: bool) -> int:
    if not lazy:
        return page_size
    return max(20, min(page_size, 40))
