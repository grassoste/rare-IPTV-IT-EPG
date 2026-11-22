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
TITLE_RE = re.compile(r'<div class="titolo">\s*<a href="([^"]*)"[^>]*>(.*?)</a>', re.S)
DESCRIPTION_RE = re.compile(r'id="descrizione"[^>]*>(.*?)(?:<script|$)', re.S)
# Assembly sessions show download/embed boilerplate in the same tab instead of a description
BOILERPLATE = (
    "CODICE DA INCORPORARE",
    "LINK DIRETTO AL VIDEO",
    "Download video della Seduta",
)


def parse_description(html):
    """The prose in an event page's 'Descrizione' tab, or None when there is none."""
    match = DESCRIPTION_RE.search(html)
    if not match:
        return None
    prose = text(match.group(1))
    if len(prose) < 40 or any(marker in prose for marker in BOILERPLATE):
        return None
    return prose


def parse_day(html):
    """-> (date, [(hour, minute, title, event_url)]) or (None, []) when not scheduled."""
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
        label = text(title.group(2))
        if hour < 24 and minute < 60 and label:
            events.append((hour, minute, label, title.group(1)))
    return datetime(int(year), month, int(day)).date(), sorted(events)


def build(days, last_duration=60, min_duration=5):
    """days: [(date, [(hour, minute, title, description)])] -> [(start, stop, title, description)]."""
    programmes = []
    for day, events in days:
        starts = [
            (
                datetime.combine(day, datetime.min.time(), tzinfo=ROME).replace(
                    hour=hour, minute=minute
                ),
                title,
                description,
            )
            for hour, minute, title, description in events
        ]
        for index, (start, title, description) in enumerate(starts):
            stop = (
                starts[index + 1][0]
                if index + 1 < len(starts)
                else start + timedelta(minutes=last_duration)
            )
            # two events can share a start time; a zero-length programme is useless in a guide
            stop = max(stop, start + timedelta(minutes=min_duration))
            programmes.append((start, stop, title, description))
    return programmes


def descriptions(events):
    """Fetch each event page once and attach its prose; a failure means no description."""
    cache = {}
    described = []
    for hour, minute, title, url in events:
        if url and url not in cache:
            try:
                cache[url] = parse_description(fetch(url))
            except Exception as err:  # noqa: BLE001 - a missing description is cosmetic
                print(f"warning: Camera description {url}: {err}", file=sys.stderr)
                cache[url] = None
        described.append((hour, minute, title, cache.get(url)))
    return described


def collect(today, days=7):
    """-> [(start, stop, title, description)] for the coming `days` days."""
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
            schedule.append((when, descriptions(events)))
    if not schedule and failures:
        raise RuntimeError(f"no day fetched ({failures} failed)")
    return build(schedule)
