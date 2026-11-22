"""Senato TV: a JSON palimpsest of parliamentary events, not a 24/7 grid.

The page is a shell: rows are rendered client-side from
`GET https://webtv.senato.it/api/palimpsest?field_date_value[min]=...&field_date_value[max]=...`.
Ask for an explicit one-day window (the no-parameter call returns only today, and CloudFront
serves stale copies without a cache-buster). Each `nid` comes back twice, so rows are deduped.

Only start times are published; the full date can be recovered from `field_vevent_id`
(`canale6_20261123_1000_atti_parlamentari`). Days without sittings return `[]`.
"""

import json
import re
import sys
from datetime import date, datetime, timedelta

from epg import ROME, fetch, text

CHANNEL = {
    "id": "SenatoTV.it",
    "name": "Senato TV",
    "icon": "https://i.imgur.com/h4NyN5d.png",
}

API = (
    "https://webtv.senato.it/api/palimpsest"
    "?field_date_value%5Bmin%5D={day}T00:00:00"
    "&field_date_value%5Bmax%5D={next}T00:00:00&_={stamp}"
)
EVENT_DATE_RE = re.compile(r"_(\d{4})(\d{2})(\d{2})_")
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})")


def parse_events(payload, day):
    """-> [(date, [(hour, minute, title, description)])] from one API response."""
    events, seen = {}, set()
    for row in payload:
        nid = str(row.get("nid") or "")
        if not nid or nid in seen:
            continue  # the API returns every event twice
        seen.add(nid)

        when = day
        stamp = EVENT_DATE_RE.search(row.get("field_vevent_id") or "")
        if stamp:
            try:
                when = date(*(int(part) for part in stamp.groups()))
            except ValueError:
                when = day

        time = TIME_RE.match((row.get("field_date") or "").strip())
        title = text(row.get("title") or "")
        if not time or not title:
            continue
        hour, minute = int(time.group(1)), int(time.group(2))
        description = text(row.get("body") or "") or None
        events.setdefault(when, []).append((hour, minute, title, description))
    return [(when, sorted(rows)) for when, rows in sorted(events.items())]


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
            stop = max(stop, start + timedelta(minutes=min_duration))
            programmes.append((start, stop, title, description))
    return programmes


def fetch_day(day, timeout=20):
    next_day = day + timedelta(days=1)
    url = API.format(
        day=day.isoformat(),
        next=next_day.isoformat(),
        stamp=int(datetime.now(ROME).timestamp()),
    )
    return parse_events(json.loads(fetch(url, timeout)), day)


def collect(today, days=7):
    """-> [(start, stop, title)] for the coming `days` days."""
    schedule, failures = [], 0
    for offset in range(days):
        try:
            schedule.extend(fetch_day(today + timedelta(days=offset)))
        except Exception as err:  # noqa: BLE001 - one missing day must not kill the channel
            failures += 1
            print(
                f"warning: Senato {today + timedelta(days=offset)}: {err}",
                file=sys.stderr,
            )
    if not schedule and failures:
        raise RuntimeError(f"no day fetched ({failures} failed)")
    return build(schedule)
