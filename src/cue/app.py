from __future__ import annotations

from pathlib import Path

import flet as ft

from cue.calendar_service import get_calendar_service
from cue.parser import build_event_body, parse_block

APP_TITLE = "CUE - Calendar Upload Engine"
SAMPLE_FILE = Path("sample_data/parades_2026.txt")


def main(page: ft.Page) -> None:
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.window.width = 1440
    page.window.height = 940
    page.padding = 18
    page.scroll = ft.ScrollMode.AUTO

    parsed_events = []
    line_checks: list[ft.Checkbox] = []

    year_field = ft.TextField(label="Year", value="2026", width=100)
    timezone_field = ft.TextField(label="Timezone", value="America/Chicago", width=220)
    duration_field = ft.TextField(label="Timed event duration (hours)", value="2.0", width=190)
    calendar_field = ft.TextField(label="Calendar ID", value="primary", width=180)
    status = ft.Text("Ready.", selectable=True)
    input_box = ft.TextField(
        label="Paste event text",
        multiline=True,
        min_lines=12,
        max_lines=22,
        expand=True,
        value=SAMPLE_FILE.read_text(encoding="utf-8") if SAMPLE_FILE.exists() else "",
    )
    preview_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    selector_status = ft.Text("Line selector ready.", selectable=True)
    line_selector = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=260)

    def rebuild_line_selector(update_page: bool = True):
        nonlocal line_checks
        lines = [line.strip() for line in (input_box.value or "").splitlines() if line.strip()]
        line_checks = [ft.Checkbox(label=line, value=True) for line in lines]
        line_selector.controls = line_checks.copy()
        selector_status.value = f"{len(lines)} pasted line(s). Checked lines will be parsed."
        if update_page:
            page.update()

    def selected_lines() -> list[str]:
        return [cb.label for cb in line_checks if cb.value and cb.label]

    def summarize_event(evt) -> ft.Control:
        pieces = [evt.title]
        if evt.start_date:
            pieces.append(f"Start: {evt.start_date.isoformat()}")
        if evt.time_text:
            pieces.append(f"Time: {evt.time_text}")
        else:
            pieces.append("All day")
        if evt.source_url:
            pieces.append(f"URL: {evt.source_url}")
        if evt.notes:
            pieces.append(f"Notes: {evt.notes}")
        return ft.Card(
            content=ft.Container(
                padding=12,
                content=ft.Column([
                    ft.Text(evt.title or "Untitled", weight=ft.FontWeight.BOLD),
                    ft.Text(" | ".join(pieces[1:]), size=12, selectable=True),
                    ft.Text(evt.raw_text, size=11, selectable=True, color=ft.Colors.BLUE_GREY_600),
                ])
            )
        )

    def refresh_preview():
        preview_column.controls.clear()
        for evt in parsed_events:
            preview_column.controls.append(summarize_event(evt))
        page.update()

    def load_sample(_):
        if SAMPLE_FILE.exists():
            input_box.value = SAMPLE_FILE.read_text(encoding="utf-8")
            status.value = f"Loaded sample data from {SAMPLE_FILE}."
            rebuild_line_selector(update_page=False)
        else:
            status.value = "Sample data file not found."
        page.update()

    def do_parse(_):
        nonlocal parsed_events
        try:
            if not line_checks:
                rebuild_line_selector(update_page=False)
            lines = selected_lines()
            if not lines:
                parsed_events = []
                status.value = "No checked lines to parse."
                preview_column.controls.clear()
                page.update()
                return
            parsed_events = parse_block("\n".join(lines), year=int(year_field.value or "2026"))
            status.value = f"Parsed {len(parsed_events)} checked event(s)."
            refresh_preview()
        except Exception as exc:
            status.value = f"Parse error: {exc}"
            page.update()

    def select_all_lines(_):
        for cb in line_checks:
            cb.value = True
        status.value = f"Selected {len(line_checks)} line(s)."
        page.update()

    def clear_all_lines(_):
        for cb in line_checks:
            cb.value = False
        status.value = "Cleared all line selections."
        page.update()

    def keep_checked_lines(_):
        lines = selected_lines()
        input_box.value = "\n".join(lines)
        rebuild_line_selector(update_page=False)
        parsed_events.clear()
        preview_column.controls.clear()
        status.value = f"Kept {len(lines)} checked line(s) in the paste area."
        page.update()

    def do_dry_run(_):
        try:
            if not parsed_events:
                status.value = "Nothing parsed yet."
                page.update()
                return
            bodies = [build_event_body(evt, timezone_field.value or "America/Chicago", float(duration_field.value or "2")) for evt in parsed_events]
            preview_column.controls.clear()
            for body in bodies:
                preview_column.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=12,
                            content=ft.Column([
                                ft.Text(body.get("summary", "Untitled"), weight=ft.FontWeight.BOLD),
                                ft.Text(str(body.get("start")), size=12, selectable=True),
                                ft.Text(str(body.get("end")), size=12, selectable=True),
                                ft.Text(body.get("description", ""), size=11, selectable=True),
                            ])
                        )
                    )
                )
            status.value = f"Dry run built {len(bodies)} Google Calendar event payload(s)."
            page.update()
        except Exception as exc:
            status.value = f"Dry run error: {exc}"
            page.update()

    def do_import(_):
        try:
            if not parsed_events:
                status.value = "Nothing parsed yet."
                page.update()
                return
            service = get_calendar_service()
            count = 0
            for evt in parsed_events:
                body = build_event_body(evt, timezone_field.value or "America/Chicago", float(duration_field.value or "2"))
                service.events().insert(calendarId=calendar_field.value or "primary", body=body).execute()
                count += 1
            status.value = f"Imported {count} event(s) into calendar '{calendar_field.value or 'primary'}'."
            page.update()
        except FileNotFoundError as exc:
            status.value = "Import error: credentials.json not found. Save your Google OAuth client secrets as credentials.json in the project root, then try again."
            page.update()
        except Exception as exc:
            status.value = f"Import error: {exc}"
            page.update()

    controls_bar = ft.Row(
        wrap=True,
        controls=[
            year_field,
            timezone_field,
            duration_field,
            calendar_field,
            ft.Button("Load sample", icon=ft.Icons.DOWNLOAD, on_click=load_sample),
            ft.Button("Parse", icon=ft.Icons.PLAY_ARROW, on_click=do_parse),
            ft.Button("Dry run", icon=ft.Icons.VISIBILITY, on_click=do_dry_run),
            ft.FilledButton("Import", icon=ft.Icons.CALENDAR_MONTH, on_click=do_import),
        ]
    )

    page.add(
        ft.Text(APP_TITLE, size=28, weight=ft.FontWeight.BOLD),
        ft.Text(
            "Paste loosely formatted event lines, preview parsed results, dry-run Google payloads, then import to Google Calendar.",
            size=14,
        ),
        controls_bar,
        status,
        ft.ResponsiveRow(
            controls=[
                ft.Container(
                    col={"sm": 12, "md": 6},
                    content=ft.Column([
                        input_box,
                        ft.Row(
                            wrap=True,
                            controls=[
                                ft.Button("Refresh lines", icon=ft.Icons.LIST, on_click=lambda _: rebuild_line_selector()),
                                ft.Button("Select all", icon=ft.Icons.CHECK_BOX, on_click=select_all_lines),
                                ft.Button("Clear all", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=clear_all_lines),
                                ft.Button("Keep checked", icon=ft.Icons.FILTER_LIST, on_click=keep_checked_lines),
                            ],
                        ),
                        selector_status,
                        line_selector,
                    ]),
                ),
                ft.Container(
                    col={"sm": 12, "md": 6},
                    content=ft.Column([
                        ft.Text("Preview", size=20, weight=ft.FontWeight.BOLD),
                        preview_column,
                    ], expand=True),
                ),
            ]
        )
    )

    if input_box.value:
        rebuild_line_selector(update_page=False)
        parsed_events = parse_block("\n".join(selected_lines()), year=int(year_field.value))
        status.value = f"Parsed {len(parsed_events)} checked event(s)."
        refresh_preview()


if __name__ == "__main__":
    ft.run(main)
