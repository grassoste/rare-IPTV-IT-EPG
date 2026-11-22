#!/usr/bin/env python3
"""Build one epg.xml from every channel source in sources/.

Each source module owns one channel: it scrapes its own broadcaster and returns
[(start, stop, title)]. This script only merges them and writes the XMLTV file.
"""

import argparse
import sys
from datetime import datetime

import epg
from sources import SOURCES


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

    today = datetime.now(epg.ROME).date()
    entries = []
    for source in SOURCES:
        channel = source.CHANNEL
        if args.only and channel["id"] not in args.only:
            continue
        try:
            programmes = source.collect(today, args.days)
        except Exception as err:  # noqa: BLE001 - one broken source must not empty the guide
            print(f"warning: {channel['name']}: {err}", file=sys.stderr)
            continue
        print(f"{channel['name']}: {len(programmes)} programmes", file=sys.stderr)
        entries.append((channel, programmes))

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
