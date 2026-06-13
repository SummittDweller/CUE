# CUE

**CUE** is a Flet-based utility for turning loosely formatted text into Google Calendar events.

The app is intended to help capture event information from copied text, Markdown fragments, email notes, or message threads, then preview, normalize, and import those events into Google Calendar with minimal cleanup.

## Goals

- Paste raw event text into a desktop-friendly Flet interface.
- Parse likely event title, date, time, and source URL values.
- Preview parsed results before import.
- Support dry-run validation before writing to Google Calendar.
- Reuse a local `.venv` workflow similar to other recent Python/Flet projects.

## Initial layout

- `src/cue/` - Python package for the app
- `scripts/` - convenience scripts for setup and launch
- `sample_data/` - sample event text for testing

## Quick start

```bash
cd CUE
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m cue.app
```

## Google Calendar setup

1. Create a Google Cloud OAuth desktop app.
2. Download the client credentials file.
3. Save it in the project root as `credentials.json`.
4. On first authenticated run, the app or helper script will create `token.json`.

## Status

This starter repo includes:

- a Flet UI shell,
- a parser module scaffold,
- a calendar service scaffold,
- sample input data,
- and helper scripts for local `.venv` setup.

Next steps are to connect the parser to the UI table, add dry-run/import actions, and wire in Google Calendar authentication.
