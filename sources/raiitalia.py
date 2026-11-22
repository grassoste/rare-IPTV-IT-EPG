"""Rai Italia: the raiplay palinsesto JSON, one file per day.

`https://www.raiplay.it/palinsesto/raiitalia/<feed>/<dd-mm-yyyy>.json` returns events with an
exact UTC start (`date`) and an exact `duration`, so no end-time guessing is needed here. The
server keeps roughly D-24..D+7 and answers HTTP 559 outside that window; day files have holes
at the edges, so a few days are fetched and deduped by event id.

The published Rai Italia guides are per feed: Africa, America, Asia, Australia. There is **no**
Europa feed (the `Rai-Italia-Europa*` files answer 302), so FEED below is the closest published
schedule to the Europe/Africa satellite leg — change it if Rai splits the feed.
"""

import json
import re
import sys
from datetime import datetime, timedelta

from epg import ROME, fetch, text

CHANNEL = {
    "id": "RaiItalia.it",
    "name": "Rai Italia",
    "icon": "https://i.imgur.com/1nN4rEP.png",
}

FEED = "Rai-Italia-Africa"
URL = "https://www.raiplay.it/palinsesto/raiitalia/{feed}/{date}.json"
STAMP = "%Y-%m-%dT%H:%M:%S%z"
DURATION_RE = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})$")


def _duration(event):
    match = DURATION_RE.match((event.get("duration") or "").strip())
    if match:
        hours, minutes, seconds = (int(part) for part in match.groups())
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    minutes = re.match(r"^(\d+)", (event.get("duration_in_minutes") or "").strip())
    return timedelta(minutes=int(minutes.group(1)) if minutes else 30)


def parse_day(payload):
    """-> [(start, stop, title, description, id)] in Europe/Rome, as published for one day."""
    programmes = []
    for event in payload.get("events") or []:
        try:
            start = datetime.strptime(event["date"], STAMP)
        except (KeyError, TypeError, ValueError):
            continue
        title = text(event.get("name") or "")
        if not title:
            continue
        stop = start + _duration(event)
        programmes.append(
            (
                start.astimezone(ROME),
                stop.astimezone(ROME),
                title,
                text(event.get("description") or "") or None,
                event.get("id") or f"{title}{start}",
            )
        )
    return programmes


def merge(payloads, today, days=7):
    """Several day files -> [(start, stop, title)], deduped, clipped and made linear.

    A day file carries two near-duplicate grids (e.g. `07:00-07:15 TG1` next to
    `07:00-08:00 TG1`, 40 overlapping pairs of 54 events), which sums to ~49h inside a 24h
    day. Keep the first event of an overlap: a player can only show one programme per channel.
    """
    seen, rows = set(), []
    for payload in payloads:
        for start, stop, title, description, event_id in parse_day(payload):
            if event_id in seen:
                continue
            seen.add(event_id)
            if not (0 <= (start.date() - today).days < days):
                continue
            rows.append((start, stop, title, description))

    programmes, busy_until = [], None
    for start, stop, title, description in sorted(rows):
        if busy_until and start < busy_until:
            continue
        programmes.append((start, stop, title, description))
        busy_until = stop
    return programmes


def collect(today, days=7):
    """-> [(start, stop, title)] for the coming `days` days."""
    payloads, failures = [], 0
    for offset in range(-1, days):
        day = today + timedelta(days=offset)
        url = URL.format(feed=FEED, date=day.strftime("%d-%m-%Y"))
        try:
            payloads.append(json.loads(fetch(url)))
        except Exception as err:  # noqa: BLE001 - 559 means "not published yet"
            failures += 1
            print(f"warning: Rai Italia {day}: {err}", file=sys.stderr)
    programmes = merge(payloads, today, days)
    if not programmes:
        raise RuntimeError(f"no programme parsed ({failures} day(s) failed)")
    return programmes
