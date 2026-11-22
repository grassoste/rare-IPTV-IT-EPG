"""Camera dei Deputati webtv: a dated event list, not a 24/7 grid.

`https://comunicazione.camera.it/palinsesto-webtv?data=YYYY-MM-DD` is server-rendered Drupal
HTML and accepts any date from 2001 to ~90 days ahead. A day with nothing scheduled says
"Nessun evento in questa data" (weekends and non-sitting days are common), so gaps in the
guide are expected and correct.

Only start times are published: an event runs until the next one that day, and the last of
the day gets a default hour. The satellite PDF on /palinsesto-satellitare is a **different**
schedule (2-day rolling, weekend publication), so it is deliberately not used here.
"""

import re
import sys
from datetime import datetime, timedelta

from epg import MONTHS, ROME, fetch, text

CHANNEL = {
    "id": "CameradeiDeputati.it",
    "name": "Camera dei Deputati",
    "icon": "https://i.imgur.com/hv4zi9N.png",
}

URL = "https://comunicazione.camera.it/palinsesto-webtv?data={}"
EMPTY_MARKERS = ("Nessun evento in questa data", "Data non disponibile sul sistema")

DAY_RE = re.compile(r'<h2 class="date">\s*(\d{1,2})\s+(\w+)\s+(\d{4})\s*</h2>')
BLOCK_RE = re.compile(
    r'<div class="caption[^"]*">(.*?)(?=<div class="caption|</section>|$)', re.S
)
TIME_RE = re.compile(r'<span class="ora">.*?(\d{1,2}):(\d{2})', re.S)
TITLE_RE = re.compile(r'<div class="titolo">\s*<a[^>]*>(.*?)</a>', re.S)


def parse_day(html):
    """-> (date, [(hour, minute, title)]) or (None, []) when the page has no schedule."""
    heading = DAY_RE.search(html)
    if not heading:
        return None, []
    day, month_name, year = heading.groups()
    month = MONTHS.get(month_name.lower())
    if month is None:
        return None, []

    events = []
    for block in BLOCK_RE.findall(html):
        time = TIME_RE.search(block)
        title = TITLE_RE.search(block)
        if not time or not title:
            continue
        hour, minute = int(time.group(1)), int(time.group(2))
        label = text(title.group(1))
        if hour < 24 and minute < 60 and label:
            events.append((hour, minute, label))
    return datetime(int(year), month, int(day)).date(), sorted(events)


def build(days, last_duration=60, min_duration=5):
    """days: [(date, [(hour, minute, title)])] -> [(start, stop, title)]."""
    programmes = []
    for day, events in days:
        starts = [
            (
                datetime.combine(day, datetime.min.time(), tzinfo=ROME).replace(
                    hour=hour, minute=minute
                ),
                title,
            )
            for hour, minute, title in events
        ]
        for index, (start, title) in enumerate(starts):
            stop = (
                starts[index + 1][0]
                if index + 1 < len(starts)
                else start + timedelta(minutes=last_duration)
            )
            # two events can share a start time; a zero-length programme is useless in a guide
            stop = max(stop, start + timedelta(minutes=min_duration))
            programmes.append((start, stop, title))
    return programmes


def collect(today, days=7):
    """-> [(start, stop, title)] for the coming `days` days."""
    schedule, failures = [], 0
    for offset in range(days):
        day = today + timedelta(days=offset)
        try:
            html = fetch(URL.format(day.isoformat()))
        except Exception as err:  # noqa: BLE001 - one missing day must not kill the channel
            failures += 1
            print(f"warning: Camera {day}: {err}", file=sys.stderr)
            continue
        if any(marker in html for marker in EMPTY_MARKERS):
            continue
        when, events = parse_day(html)
        if when:
            schedule.append((when, events))
    if not schedule and failures:
        raise RuntimeError(f"no day fetched ({failures} failed)")
    return build(schedule)
