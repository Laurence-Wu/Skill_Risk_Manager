from __future__ import annotations

import customtkinter as ctk

from manager_GUI.core.state import AppState
from manager_GUI.ui.components import BaseButton, BaseView
from manager_GUI.ui.tables import BaseTable


class CandidatesView(BaseView):
    def __init__(self, master, actions: dict) -> None:
        super().__init__(master, actions)
        self.grid_rowconfigure(3, weight=1)
        self.selected_bucket = "snapshot"
        self.page_header("Candidates", "Uncertain and staged findings stay separate until reviewed.")
        self.segment_row = ctk.CTkFrame(self, fg_color="transparent")
        self.segment_row.grid(row=2, column=0, sticky="w", padx=self.theme.spacing("app_padding"), pady=(0, 12))
        self._render_segments()

        self.table = BaseTable(
            self,
            ["Path", "Reason", "Confidence", "Source", "Suggested Type"],
            empty_text="No candidates in this list.",
        )
        self.table.grid(row=3, column=0, sticky="nsew", padx=self.theme.spacing("app_padding"), pady=(0, 16))
        self._state: AppState | None = None

    def refresh(self, state: AppState) -> None:
        self._state = state
        records = {
            "snapshot": state.candidates_snapshot,
            "staged": list(reversed(state.candidates_staged)),
            "ignored": state.ignored_candidates,
        }[self.selected_bucket]
        actions = [("Open Folder", self._open_folder, "secondary")]
        if self.selected_bucket != "ignored":
            actions = [
                ("Promote", self._promote, "primary"),
                ("Ignore", self._ignore, "secondary"),
                ("Open Folder", self._open_folder, "secondary"),
            ]
        self.table.set_rows([record.to_row() for record in records], actions, page_size=80)

    def _select_bucket(self, bucket: str) -> None:
        self.selected_bucket = bucket
        self._render_segments()
        if self._state:
            self.refresh(self._state)

    def _render_segments(self) -> None:
        for child in self.segment_row.winfo_children():
            child.destroy()
        for index, candidate_bucket in enumerate(["snapshot", "staged", "ignored"]):
            BaseButton(
                self.segment_row,
                candidate_bucket.title(),
                command=lambda selected=candidate_bucket: self._select_bucket(selected),
                variant="primary" if candidate_bucket == self.selected_bucket else "secondary",
                width=96,
            ).grid(row=0, column=index, padx=(0 if index == 0 else 6, 0))

    def _promote(self, row: dict[str, object]) -> None:
        record = row.get("_record")
        if record:
            self.actions["promote_candidate"](record)

    def _ignore(self, row: dict[str, object]) -> None:
        record = row.get("_record")
        if record:
            self.actions["ignore_candidate"](record)

    def _open_folder(self, row: dict[str, object]) -> None:
        self.actions["open_folder"](str(row.get("Path", "")))
