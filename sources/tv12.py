"""TV12 Medianordest: one hand-edited WordPress table, refreshed daily.

`https://tv12.medianordest.it/programmazione/` renders a single HTML table under
`<h2 align='center'>26/11/2026</h2>`, one `<tr>` per programme: time, title, description.
No parameter opens another day and no multi-day feed exists, so this source contributes
today's schedule only; descriptions come with it.

The table is a *broadcast* day starting at 05:00 that wraps at `23:49 -> 00:12`, so rows are
kept in source order and a backwards jump moves to the next calendar day. Sorting by clock
time would put the night tail at the start of the day.
"""

import re
import sys
from datetime import date, datetime, time as dtime, timedelta

from epg import ROME, fetch, resolve_dates, text

CHANNEL = {
    "id": "TV12.it",
    "name": "TV12 Medianordest",
    "icon": "https://tv12.medianordest.it/wp-content/uploads/2024/02/logo_sito_tv12.png",
}

URL = "https://tv12.medianordest.it/programmazione/"

DATE_RE = re.compile(
    r"<h2[^>]*align=['\"]center['\"][^>]*>\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*</h2>", re.I
)
ROW_RE = re.compile(
    r"<tr[^>]*>\s*<td[^>]*>\s*(\d{1,2}):(\d{2})\s*</td>\s*"
    r"<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>",
    re.S,
)


def parse_page(html):
    """-> (date, [(hour, minute, title, description)]) in the order the table lists them."""
    heading = DATE_RE.search(html)
    if not heading:
        return None, []
    day, month, year = (int(part) for part in heading.groups())
    try:
        when = date(year, month, day)
    except ValueError:
        return None, []

    events = []
    for hour, minute, title, description in ROW_RE.findall(html):
        hour, minute = int(hour), int(minute)
        label = text(title)
        if hour > 23 or minute > 59 or not label:
            continue
        events.append((hour, minute, label, text(description) or None))
    return when, events


def build(when, events, last_duration=60, min_duration=5):
    """Source order + midnight wrap -> [(start, stop, title, description)]."""
    starts, previous, extra_days = [], None, 0
    for hour, minute, title, description in events:
        if previous and (hour, minute) < previous:
            extra_days += 1
        previous = (hour, minute)
        start = datetime.combine(when, dtime(hour, minute), tzinfo=ROME) + timedelta(
            days=extra_days
        )
        starts.append((start, title, description))

    programmes = []
    for index, (start, title, description) in enumerate(starts):
        stop = (
            starts[index + 1][0]
            if index + 1 < len(starts)
            else start + timedelta(minutes=last_duration)
        )
        stop = max(stop, start + timedelta(minutes=min_duration))
        programmes.append((start, stop, title, description))
    return programmes


def collect(today, days=7):
    """-> [(start, stop, title, description)] for today's published schedule."""
    when, events = parse_page(fetch(URL))
    if not events:
        raise RuntimeError("no programme parsed — has the page structure changed?")
    if when != today:
        print(
            f"warning: TV12 publishes {when}, projecting onto the current week",
            file=sys.stderr,
        )
    window = [
        day
        for day in resolve_dates(
            [{"weekday": when.weekday(), "date": when, "entries": events}], today, days
        )
        if (day["date"] - today).days < days
    ]
    return [row for day in window for row in build(day["date"], day["entries"])]
