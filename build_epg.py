#!/usr/bin/env python3
"""Build one epg.xml from every channel source in sources/.

Each source module owns one channel: it scrapes its own broadcaster and returns
[(start, stop, title)]. This script only merges them and writes the XMLTV file.

A source that fails is a warning, not a lost channel: its programmes are carried over from
the guide already on disk. Shared CI IPs get rate-limited (Blogspot answers 429), and losing
a channel from the published guide is worse than serving the last known schedule for a day.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

import epg
from sources import SOURCES

STAMP = "%Y%m%d%H%M%S %z"


def read_previous(path, since=None):
    """-> {channel_id: [(start, stop, title)]} from the already published XMLTV file."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return {}
    previous = {}
    for programme in root.findall("programme"):
        title = programme.find("title")
        try:
            start = datetime.strptime(programme.get("start"), STAMP)
            stop = datetime.strptime(programme.get("stop"), STAMP)
        except (TypeError, ValueError):
            continue
        if title is None or not title.text or (since and stop <= since):
            continue
        previous.setdefault(programme.get("channel"), []).append(
            (start, stop, title.text)
        )
    return {channel: sorted(rows) for channel, rows in previous.items()}


def collect_all(sources, today, days, previous=None, only=None):
    """-> [(channel, programmes)]; a failing source falls back to its published programmes."""
    previous = previous or {}
    entries = []
    for source in sources:
        channel = source.CHANNEL
        if only and channel["id"] not in only:
            continue
        try:
            programmes = source.collect(today, days)
        except Exception as err:  # noqa: BLE001 - one broken source must not empty the guide
            carried = previous.get(channel["id"])
            if not carried:
                print(f"warning: {channel['name']}: {err}", file=sys.stderr)
                continue
            print(
                f"warning: {channel['name']}: {err} — carrying over {len(carried)} "
                "programmes from the published guide",
                file=sys.stderr,
            )
            programmes = carried
        else:
            print(f"{channel['name']}: {len(programmes)} programmes", file=sys.stderr)
        entries.append((channel, programmes))
    return entries


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build epg.xml from every channel source."
    )
    parser.add_argument(
        "-o", "--output", default="epg.xml", help="output file (default: epg.xml)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        choices=range(1, 8),
        metavar="1-7",
        help="days to emit per channel, starting today (default: 7)",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="ID",
        help="only these channel ids (default: every source)",
    )
    args = parser.parse_args(argv)

    now = datetime.now(epg.ROME)
    previous = read_previous(args.output, since=now)
    entries = collect_all(SOURCES, now.date(), args.days, previous, args.only)
    if not entries:
        raise SystemExit("error: no source produced programmes")

    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(epg.build_xmltv(entries))
    total = sum(len(programmes) for _, programmes in entries)
    print(
        f"{total} programmes for {len(entries)} channel(s) -> {args.output}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
