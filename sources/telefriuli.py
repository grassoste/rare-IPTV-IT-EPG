"""Telefriuli: weekly page on telefriuli.it plus the live playout log.

The weekly page is a WordPress Elementor widget, one tab per weekday, one paragraph per
programme ("06.20   Title"). Its heading dates drift by weeks, so only the weekday is
trusted and every day is re-projected onto the coming week. The live page's playout log
covers today and part of tomorrow with minute-accurate, real broadcast names, so it wins
for the days it covers.
"""

import json
import re
import sys
import time
from datetime import date

from epg import MONTHS, WEEKDAYS, build_programmes, fetch, resolve_dates, text

CHANNEL = {
    "id": "Telefriuli.it",
    "name": "Telefriuli",
    "icon": "https://i.imgur.com/He3uCs6.png",
}

REST_URL = "https://www.telefriuli.it/wp-json/wp/v2/pages/494"
PAGE_URL = "https://www.telefriuli.it/palinsesto/"
STREAMING_URL = "https://www.telefriuli.it/streaming/"
MIN_PROGRAMMES = 50
MIN_STREAM_DAY = (
    10  # the live log builds forward; below this a day is not worth replacing
)

HEADING_RE = re.compile(r"^programmazione di (\w+) (\d{2})/(\d{2})/(\d{2})$", re.I)
ROW_RE = re.compile(r"^(\d{1,2})[.:](\d{2})\s+(.+)$")
GUIDE_DAY_RE = re.compile(
    r'<h3>(\w+) (\d{1,2}) (\w+) (\d{4})</h3>\s*<ul class="programme-day">(.*?)</ul>',
    re.S,
)
GUIDE_ITEM_RE = re.compile(
    r'<li class="programme[^"]*">\s*<div class="time">(\d{1,2}):(\d{2})</div>'
    r'.*?<div class="title">(.*?)</div>',
    re.S,
)


def load_html(timeout=20):
    """REST first: the rendered page sits behind a URL-keyed cache that can serve last week."""
    try:
        return json.loads(fetch(REST_URL, timeout))["content"]["rendered"]
    except Exception as err:  # noqa: BLE001 - any failure means "use the page"
        print(
            f"warning: REST fetch failed ({err}), falling back to the page",
            file=sys.stderr,
        )
    return fetch(f"{PAGE_URL}?v={int(time.time())}", timeout)


def parse_schedule(html):
    """-> [{'weekday': 0-6, 'date': date, 'entries': [(hour, minute, label)]}]"""
    days = []
    for raw in re.findall(r"<p[^>]*>(.*?)</p>", html, re.S):
        line = text(raw)
        if not line:
            continue
        heading = HEADING_RE.match(line)
        if heading:
            weekday = WEEKDAYS.get(heading.group(1).lower())
            if weekday is None:
                continue
            day, month, year = (int(part) for part in heading.groups()[1:])
            days.append(
                {
                    "weekday": weekday,
                    "date": date(2000 + year, month, day),
                    "entries": [],
                }
            )
            continue
        row = ROW_RE.match(line)
        if row and days:
            hour, minute = int(row.group(1)), int(row.group(2))
            if hour < 24 and minute < 60:
                days[-1]["entries"].append((hour, minute, row.group(3)))
    return [day for day in days if day["entries"]]


def parse_streaming(html):
    """The live page's playout log: dated, minute-accurate, but only the next day or two."""
    days = []
    for weekday_name, day, month_name, year, body in GUIDE_DAY_RE.findall(html):
        weekday = WEEKDAYS.get(weekday_name.lower())
        month = MONTHS.get(month_name.lower())
        if weekday is None or month is None:
            continue
        entries = [
            (int(hour), int(minute), text(title))
            for hour, minute, title in GUIDE_ITEM_RE.findall(body)
        ]
        entries = [
            item for item in entries if item[0] < 24 and item[1] < 60 and item[2]
        ]
        if len(entries) >= MIN_STREAM_DAY:
            days.append(
                {
                    "weekday": weekday,
                    "date": date(int(year), month, int(day)),
                    "entries": entries,
                }
            )
    return days


def merge_days(preferred, fallback):
    """The live log wins for the days it covers; the weekly page fills the rest."""
    merged = {day["weekday"]: day for day in fallback}
    merged.update({day["weekday"]: day for day in preferred})
    return [merged[weekday] for weekday in sorted(merged)]


def collect(today, days=7):
    """-> [(start, stop, title)] for the coming `days` days."""
    week = parse_schedule(load_html())
    total = sum(len(day["entries"]) for day in week)
    if total < MIN_PROGRAMMES:
        raise RuntimeError(
            f"parsed only {total} programmes — has the page structure changed?"
        )

    try:
        live = parse_streaming(fetch(f"{STREAMING_URL}?v={int(time.time())}"))
    except Exception as err:  # noqa: BLE001 - the weekly page still works without it
        print(f"warning: live guide unavailable ({err})", file=sys.stderr)
        live = []
    if live:
        print(
            "live guide overrides %d day(s): %s"
            % (len(live), ", ".join(str(day["date"]) for day in live)),
            file=sys.stderr,
        )
        week = merge_days(live, week)

    if max(day["date"] for day in week) < today:
        print(
            "warning: the schedule has no day in the future; the guide may be stale",
            file=sys.stderr,
        )

    window = [
        day for day in resolve_dates(week, today) if (day["date"] - today).days < days
    ]
    return build_programmes(window)
