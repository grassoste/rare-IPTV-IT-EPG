"""Shared XMLTV plumbing for every channel source.

A source module provides a CHANNEL dict and a collect(today, days) function returning
[(start, stop, title)]; this module turns those into one XMLTV document.
"""

import re
import urllib.request
from datetime import datetime, time as dtime, timedelta
from html import unescape
from xml.sax.saxutils import escape, quoteattr
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
HORIZON = 7
GENERATOR = "rare-IPTV-IT-EPG"

WEEKDAYS = {
    "lunedì": 0,
    "martedì": 1,
    "mercoledì": 2,
    "giovedì": 3,
    "venerdì": 4,
    "sabato": 5,
    "domenica": 6,
}
MONTHS = {
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": f"{GENERATOR}/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", "replace")


def text(fragment):
    """HTML fragment -> single-line plain text."""
    return re.sub(
        r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", fragment)).replace("\xa0", " ")
    ).strip()


def resolve_dates(days, today, horizon=HORIZON):
    """Put every day inside [today, today+horizon), keeping the weekday it claims."""
    resolved = []
    for day in days:
        when = day["date"]
        if when.weekday() != day["weekday"]:
            when = today + timedelta(days=(day["weekday"] - today.weekday()) % 7)
        while when < today:
            when += timedelta(weeks=1)
        while (when - today).days >= horizon:
            when -= timedelta(weeks=1)
        resolved.append({**day, "date": when})
    return sorted(resolved, key=lambda day: day["date"])


def build_programmes(days, last_duration=60):
    """-> [(start, stop, title)], durations from the next start time in the day."""
    programmes = []
    for day in days:
        # Sources sometimes list a row out of order. A timetable is chronological, and one
        # stray row must not shift the rest of the day by 24 hours.
        starts = [
            (
                datetime.combine(day["date"], dtime(hour, minute), tzinfo=ROME),
                label.strip(),
            )
            for hour, minute, label in sorted(day["entries"])
        ]
        for index, (start, title) in enumerate(starts):
            stop = (
                starts[index + 1][0]
                if index + 1 < len(starts)
                else start + timedelta(minutes=last_duration)
            )
            programmes.append((start, stop, title))
    return programmes


def _xmltv_time(moment):
    return moment.astimezone(ROME).strftime("%Y%m%d%H%M%S %z")


def build_xmltv(entries, generated=None):
    """entries: [(channel_dict, [(start, stop, title)])] -> XMLTV string."""
    generated = generated or datetime.now(ROME)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<tv generator-info-name="{GENERATOR}" date="{generated.strftime("%Y%m%d")}">',
    ]
    for channel, _ in entries:
        lines.append(f"  <channel id={quoteattr(channel['id'])}>")
        lines.append(
            f'    <display-name lang="it">{escape(channel["name"])}</display-name>'
        )
        if channel.get("icon"):
            lines.append(f"    <icon src={quoteattr(channel['icon'])} />")
        lines.append("  </channel>")

    rows = [
        (start, stop, channel["id"], title)
        for channel, programmes in entries
        for start, stop, title in programmes
    ]
    for start, stop, channel_id, title in sorted(rows):
        lines.append(
            f'  <programme start="{_xmltv_time(start)}" stop="{_xmltv_time(stop)}" '
            f"channel={quoteattr(channel_id)}>"
        )
        lines.append(f'    <title lang="it">{escape(title)}</title>')
        lines.append("  </programme>")
    lines.append("</tv>")
    return "\n".join(lines) + "\n"
