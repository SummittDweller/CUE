from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional

DEFAULT_YEAR = 2026
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

HEADER_RE = re.compile(
    r"^(?P<weekday>(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:[–-](?:Mon|Tue|Wed|Thu|Fri|Sat|Sun))?),\s+"
    r"(?P<month>[A-Z][a-z]{2})\s+"
    r"(?P<day>\d{1,2})(?:[–-](?P<endday>\d{1,2}))?\s+"
    r"(?P<rest>.*)$"
)
URL_MD_RE = re.compile(r'\[([^\]]+)\]\((https?://[^)]+)\)')
URL_RAW_RE = re.compile(r'https?://\S+')
TIME_RE = re.compile(r'(?P<h>\d{1,2}):(\d{2})\s*(?P<ampm>[ap]m)', re.I)
PAREN_RE = re.compile(r'\(([^()]*)\)')
LOCATION_TAIL_RE = re.compile(r'(?:,\s*IA|\(Beaverdale\),\s*IA|IA)\s+~?\d+\s+mi(?:\s*\([^)]*\))?\s*$')
TITLE_LOCATION_SEP_RE = re.compile(r'^(?P<title>.+?)\.\s+(?P<tail>.+)$')
FACEBOOK_TRAIL_RE = re.compile(r'\s+Facebook:\s*[^\n]+$', re.I)
EXPLICIT_DATE_IN_PAREN_RE = re.compile(r'\b(?P<weekday>Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(?:(?P<month>[A-Z][a-z]{2})\s+)?(?P<day>\d{1,2})\b')
ONLY_WEEKDAY_IN_PAREN_RE = re.compile(r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b')


@dataclass
class ParsedEvent:
    raw_text: str
    title: str
    start_date: Optional[date] = None
    end_date_exclusive: Optional[date] = None
    time_text: Optional[str] = None
    source_url: Optional[str] = None
    all_day: bool = True
    notes: Optional[str] = None


def strip_markdown_and_extract_url(text: str) -> tuple[str, Optional[str]]:
    url = None
    md_match = URL_MD_RE.search(text)
    if md_match:
        url = md_match.group(2)
        text = URL_MD_RE.sub("", text)
    else:
        raw_match = URL_RAW_RE.search(text)
        if raw_match:
            url = raw_match.group(0)
            text = URL_RAW_RE.sub("", text)
    text = FACEBOOK_TRAIL_RE.sub("", text).strip()
    return re.sub(r'\s+', ' ', text).strip(), url


def parse_time(value: str) -> str:
    m = TIME_RE.search(value)
    if not m:
        raise ValueError(f"No time found in: {value}")
    hh = int(m.group('h'))
    mm = int(m.group(2))
    ampm = m.group('ampm').lower()
    if ampm == 'pm' and hh != 12:
        hh += 12
    if ampm == 'am' and hh == 12:
        hh = 0
    return f"{hh:02d}:{mm:02d}"


def infer_specific_date(paren_text: str, header_month: str, start_day: int, end_day: Optional[int], year: int) -> Optional[date]:
    explicit = EXPLICIT_DATE_IN_PAREN_RE.search(paren_text)
    if explicit:
        month = explicit.group('month') or header_month
        day = int(explicit.group('day'))
        return date(year, MONTHS[month], day)

    if end_day is not None:
        wd = ONLY_WEEKDAY_IN_PAREN_RE.search(paren_text)
        if wd:
            target = wd.group(1)
            start = date(year, MONTHS[header_month], start_day)
            end = date(year, MONTHS[header_month], end_day)
            current = start
            while current <= end:
                if WEEKDAYS[current.weekday()] == target:
                    return current
                current += timedelta(days=1)
    return None


def clean_summary(rest: str) -> str:
    s = rest.strip(" -—")
    separated = TITLE_LOCATION_SEP_RE.match(s)
    if separated and LOCATION_TAIL_RE.search(separated.group('tail')):
        return re.sub(r'\s+', ' ', separated.group('title')).strip(' -—')
    s = re.sub(r'\s+', ' ', s).strip(' -—')
    return s


def parse_event_line(line: str, year: int = DEFAULT_YEAR) -> ParsedEvent:
    original = line.strip()
    if not original:
        raise ValueError("Empty line")

    normalized, url = strip_markdown_and_extract_url(original)
    m = HEADER_RE.match(normalized)
    if not m:
        return ParsedEvent(raw_text=original, title=normalized, source_url=url, notes="Unparsed")

    month = m.group('month')
    day = int(m.group('day'))
    endday = int(m.group('endday')) if m.group('endday') else None
    rest = m.group('rest').strip()

    parens = PAREN_RE.findall(rest)
    event_date = infer_specific_date(" | ".join(parens), month, day, endday, year) or date(year, MONTHS[month], day)

    time_text = None
    for p in parens:
        if TIME_RE.search(p):
            time_text = parse_time(p)
            break
    if time_text is None and TIME_RE.search(rest):
        time_text = parse_time(rest)

    summary = clean_summary(rest)
    if parens:
        summary = re.sub(r'\s*\([^)]*\)', '', summary).strip()
    summary = re.sub(r'\s+[—-]\s+.*$', '', summary).strip()

    if time_text:
        return ParsedEvent(
            raw_text=original,
            title=summary,
            start_date=event_date,
            end_date_exclusive=event_date + timedelta(days=1),
            time_text=time_text,
            source_url=url,
            all_day=False,
        )

    if endday is not None and event_date == date(year, MONTHS[month], day):
        end_exclusive = date(year, MONTHS[month], endday) + timedelta(days=1)
    else:
        end_exclusive = event_date + timedelta(days=1)

    return ParsedEvent(
        raw_text=original,
        title=summary,
        start_date=event_date,
        end_date_exclusive=end_exclusive,
        time_text=None,
        source_url=url,
        all_day=True,
    )


def parse_block(text: str, year: int = DEFAULT_YEAR) -> list[ParsedEvent]:
    return [parse_event_line(line, year=year) for line in text.splitlines() if line.strip()]


def build_event_body(item: ParsedEvent, timezone: str = "America/Chicago", duration_hours: float = 2.0) -> dict:
    event = {
        "summary": item.title,
        "description": f"Source: {item.source_url or 'None'}\n\nImported from text: {item.raw_text}",
    }
    if item.source_url:
        event["source"] = {"title": "Event source", "url": item.source_url}

    if item.all_day or not item.time_text:
        start = item.start_date or date(DEFAULT_YEAR, 1, 1)
        end = item.end_date_exclusive or (start + timedelta(days=1))
        event["start"] = {"date": start.isoformat()}
        event["end"] = {"date": end.isoformat()}
    else:
        hh, mm = map(int, item.time_text.split(":"))
        start_dt = datetime.combine(item.start_date, time(hh, mm))
        end_dt = start_dt + timedelta(hours=duration_hours)
        event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": timezone}
        event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": timezone}
    return event
