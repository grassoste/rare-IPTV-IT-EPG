"""Iunior TV: the weekly guide pasted at the bottom of the channel's single Blogger post.

The blog is one ever-green post; the guide starts after a `============= PALINSESTO ============`
line and runs weekday by weekday (`LUNEDI`, `MARTEDI`, ...) as `ore 07,00 - TITLE`. There are
no dates, so each block is projected onto the next occurrence of its weekday. A block runs
past midnight (`ore 00,00`, `ore 01,00` at the end), so those rows belong to the next day.
"""

import re
import sys
from datetime import datetime, timedelta

from epg import ROME, fetch, text

CHANNEL = {
    "id": "IuniorTV.it",
    "name": "Iunior TV",
    "icon": "https://i.imgur.com/FBOJnfT.png",
}

BLOG_URL = "https://iuniortv.blogspot.com/"
MIN_ROWS = 150

DAY_NAMES = {
    "LUNEDI": 0,
    "MARTEDI": 1,
    "MERCOLEDI": 2,
    "GIOVEDI": 3,
    "VENERDI": 4,
    "SABATO": 5,
    "DOMENICA": 6,
}
DAY_RE = re.compile(r"^(" + "|".join(DAY_NAMES) + r")\b", re.I)
ROW_RE = re.compile(r"^ore\s+(\d{1,2})[,.:](\d{2})\s*[-\u2013]\s*(.+)$", re.I)


def page_lines(html):
    """Blogger markup -> one line per visual line, tags and entities resolved."""
    html = re.sub(r"<br\s*/?>", "\n", html)
    html = re.sub(r"</(?:p|div|h[1-6]|li)>", "\n", html)
    lines = [text(line) for line in html.split("\n")]
    return [line for line in lines if line]


def parse_guide(html):
    """-> {weekday: [(hour, minute, title)]} in the order the blog lists them."""
    lines = page_lines(html)
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if "PALINSESTO" in line.upper() and "=" in line
        ),
        None,
    )
    if start is None:
        return {}

    guide, weekday = {}, None
    for line in lines[start + 1 :]:
        day = DAY_RE.match(line)
        if day:
            weekday = DAY_NAMES[day.group(1).upper()]
            guide.setdefault(weekday, [])
            continue
        row = ROW_RE.match(line)
        if row and weekday is not None:
            hour, minute = int(row.group(1)), int(row.group(2))
            if hour < 24 and minute < 60:
                guide[weekday].append((hour, minute, row.group(3).strip()))
    return guide


def collect(today, days=7):
    """-> [(start, stop, title)] for the coming `days` days."""
    return build(parse_guide(fetch(BLOG_URL)), today, days)


def build(guide, today, days=7):
    total = sum(len(rows) for rows in guide.values())
    if total < MIN_ROWS:
        raise RuntimeError(
            f"parsed only {total} rows — has the blog's PALINSESTO section changed?"
        )
    if len(guide) < 7:
        print(f"warning: only {len(guide)} weekday block(s) found", file=sys.stderr)

    programmes = []
    for weekday, rows in sorted(guide.items()):
        offset = (weekday - today.weekday()) % 7
        if offset >= days:
            continue
        night = today + timedelta(days=offset)
        starts, extra, previous = [], 0, None
        for hour, minute, title in rows:
            # the block lists 00,00 / 01,00 after 23,xx: same broadcast day, next calendar day
            if previous is not None and hour < 6 and hour < previous.hour:
                extra += 1
            start = datetime.combine(
                night, datetime.min.time(), tzinfo=ROME
            ) + timedelta(days=extra, hours=hour, minutes=minute)
            previous = start
            starts.append((start, title))
        for index, (start, title) in enumerate(starts):
            stop = (
                starts[index + 1][0]
                if index + 1 < len(starts)
                else start + timedelta(minutes=60)
            )
            programmes.append((start, stop, title))
    return sorted(programmes)
