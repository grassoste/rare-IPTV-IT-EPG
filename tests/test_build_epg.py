import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import build_epg
import epg

CHANNEL = {"id": "Test.it", "name": "Test", "icon": None}
TODAY = datetime(2026, 11, 22, 12, 0, tzinfo=epg.ROME)


def _sample(rows):
    start = datetime(2026, 11, 22, 20, 0, tzinfo=epg.ROME)
    return epg.build_xmltv(
        [(CHANNEL, [(start, start.replace(hour=21), title) for title in rows])]
    )


class PreviousTest(unittest.TestCase):
    def _read(self, content):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "epg.xml"
            path.write_text(content, encoding="utf-8")
            return build_epg.read_previous(path, since=TODAY)

    def test_reads_channels_and_titles(self):
        previous = self._read(_sample(["A", "B"]))
        self.assertEqual([title for _, _, title in previous["Test.it"]], ["A", "B"])

    def test_drops_programmes_that_already_ended(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "epg.xml"
            path.write_text(_sample(["A"]), encoding="utf-8")
            later = datetime(2026, 11, 22, 22, 0, tzinfo=epg.ROME)
            self.assertEqual(build_epg.read_previous(path, since=later), {})

    def test_missing_or_broken_file_is_empty(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "epg.xml"
            self.assertEqual(build_epg.read_previous(path), {})
            path.write_text("<tv><programme", encoding="utf-8")
            self.assertEqual(build_epg.read_previous(path), {})


class CollectTest(unittest.TestCase):
    class Good:
        CHANNEL = {"id": "Good.it", "name": "Good", "icon": None}

        @staticmethod
        def collect(today, days):
            start = datetime(2026, 11, 22, 18, 0, tzinfo=epg.ROME)
            return [(start, start.replace(hour=19), "FRESH")]

    class Broken:
        CHANNEL = {"id": "Broken.it", "name": "Broken", "icon": None}

        @staticmethod
        def collect(today, days):
            raise RuntimeError("HTTP Error 429: Too Many Requests")

    def test_failing_source_keeps_its_published_programmes(self):
        carried = {"Broken.it": [(TODAY, TODAY.replace(hour=13), "LAST KNOWN")]}
        entries = build_epg.collect_all(
            [self.Good, self.Broken], TODAY.date(), 7, carried
        )
        self.assertEqual(
            [channel["id"] for channel, _ in entries], ["Good.it", "Broken.it"]
        )
        self.assertEqual(entries[1][1][0][2], "LAST KNOWN")

    def test_failing_source_without_history_is_skipped(self):
        entries = build_epg.collect_all([self.Good, self.Broken], TODAY.date(), 7, {})
        self.assertEqual([channel["id"] for channel, _ in entries], ["Good.it"])

    def test_only_filter(self):
        entries = build_epg.collect_all(
            [self.Good, self.Broken], TODAY.date(), 7, {}, only=["Good.it"]
        )
        self.assertEqual(len(entries), 1)


if __name__ == "__main__":
    unittest.main()
