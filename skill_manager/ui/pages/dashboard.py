from __future__ import annotations

import customtkinter as ctk

from skill_manager.backend.models import ScanSummary, SkillRecord
from skill_manager.platform.base import PlatformAdapter


class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, adapter: PlatformAdapter, on_run_scan, on_open_settings, on_show_skills, on_show_candidates, on_cancel_shadow, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.adapter = adapter
        self.live_records: list[dict] = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.title = ctk.CTkLabel(self, text="Dashboard", font=ctk.CTkFont(size=24, weight="bold"))
        self.title.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))
        self.info = ctk.CTkLabel(self, text="", justify="left", anchor="w")
        self.info.grid(row=1, column=0, sticky="ew", padx=18, pady=8)
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=2, column=0, sticky="w", padx=18, pady=12)
        ctk.CTkButton(button_frame, text="Run Fast Scan", command=on_run_scan).grid(row=0, column=0, padx=6, pady=8)
        ctk.CTkButton(button_frame, text="Open Settings", command=on_open_settings).grid(row=0, column=1, padx=6, pady=8)
        ctk.CTkButton(button_frame, text="View Skills", command=on_show_skills).grid(row=0, column=2, padx=6, pady=8)
        ctk.CTkButton(button_frame, text="Review Candidates", command=on_show_candidates).grid(row=0, column=3, padx=6, pady=8)
        ctk.CTkButton(button_frame, text="Cancel Shadow Scan", command=on_cancel_shadow).grid(row=0, column=4, padx=6, pady=8)
        self.discovery_frame = ctk.CTkScrollableFrame(self, label_text="Potential skills and Claude items")
        self.discovery_frame.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.discovery_frame.grid_columnconfigure(0, weight=1)
        self.set_idle()

    def set_idle(self) -> None:
        self._render_records([])
        self.info.configure(
            text=(
                f"Platform: {self.adapter.name}\n"
                f"Claude config root: {self.adapter.format_path(self.adapter.claude_config_root())}\n"
                "Last scan: Not yet run"
            )
        )

    def set_scanning(self) -> None:
        self.live_records = []
        self._render_records([])
        self.info.configure(
            text=(
                "Scanning Claude environment...\n"
                "Dashboard shows live in-memory discoveries only.\n"
                "Stable Skills/Candidates pages update after fast exit."
            )
        )

    def update_scan_progress(self, payload: dict) -> None:
        self.live_records = list(payload.get("potential_records", []))
        self.info.configure(
            text=(
                "Scanning Claude environment...\n\n"
                f"Current phase: {payload.get('current_phase', '—')}\n"
                f"Current path: {payload.get('formatted_path', '—')}\n"
                f"Files checked: {payload.get('files_checked', 0)}\n"
                f"Potential skills/items found: {payload.get('potential_found', len(self.live_records))}\n"
                f"Errors: {payload.get('errors', 0)}"
            )
        )
        self._render_records(self.live_records)

    def set_summary(self, summary: ScanSummary, records: list[SkillRecord] | None = None) -> None:
        self.info.configure(
            text=(
                "Fast scan complete.\n\n"
                f"Confirmed skills: {summary.confirmed_skills}\n"
                f"Candidate files: {summary.candidates}\n"
                f"Legacy commands: {summary.legacy_commands}\n"
                f"Claude configs: {summary.claude_configs}\n"
                f"Shadow scan: {summary.shadow_status}"
            )
        )
        self._render_records([record.to_dict() for record in records or []])

    def _render_records(self, records: list[dict]) -> None:
        for child in self.discovery_frame.winfo_children():
            child.destroy()
        if not records:
            ctk.CTkLabel(
                self.discovery_frame,
                text="No discoveries yet.",
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
            return
        for row_index, record in enumerate(records):
            name = record.get("name", "Unknown")
            record_type = record.get("record_type", "unknown")
            scope = record.get("scope", "unknown")
            path = record.get("path", "")
            metadata = record.get("metadata", {}) if isinstance(record.get("metadata", {}), dict) else {}
            description = metadata.get("description") or metadata.get("summary") or ""
            referenced_skills = metadata.get("referenced_skills") or []
            text_parts = [f"{name}  •  {record_type}  •  {scope}"]
            if description:
                text_parts.append(str(description))
            if referenced_skills:
                text_parts.append(f"References: {', '.join(str(skill) for skill in referenced_skills)}")
            text_parts.append(str(path))
            text = "\n".join(text_parts)
            ctk.CTkLabel(self.discovery_frame, text=text, justify="left", anchor="w").grid(
                row=row_index,
                column=0,
                sticky="ew",
                padx=8,
                pady=5,
            )
