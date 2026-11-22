import json
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from sources import raiitalia

FIXTURE = Path(__file__).parent / "fixtures" / "raiitalia-day.json"
DAY = date(2026, 11, 23)


class ParseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.rows = raiitalia.parse_day(cls.payload)

    def test_every_event_parsed(self):
        self.assertEqual(len(self.rows), 54)

    def test_utc_start_is_converted_to_rome(self):
        # the payload says 2026-11-23T00:30:00+0000
        first = self.rows[0]
        self.assertEqual(
            first[0].strftime("%Y-%m-%d %H:%M %z"), "2026-11-23 01:30 +0100"
        )
        self.assertEqual(first[2], "Speciale TG1")

    def test_duration_is_exact(self):
        first = self.rows[0]
        self.assertEqual(first[1] - first[0], timedelta(hours=1))

    def test_description_is_kept_when_present(self):
        described = [row for row in self.rows if row[3]]
        self.assertTrue(described, "no event carried a description")
        self.assertTrue(all(isinstance(row[3], str) for row in described))

    def test_falls_back_to_duration_in_minutes(self):
        payload = {
            "events": [
                {
                    "id": "1",
                    "name": "X",
                    "date": "2026-11-23T10:00:00+0000",
                    "duration": "",
                    "duration_in_minutes": "45 min",
                }
            ]
        }
        start, stop, _, _, _ = raiitalia.parse_day(payload)[0]
        self.assertEqual(stop - start, timedelta(minutes=45))

    def test_unknown_duration_defaults_to_thirty_minutes(self):
        payload = {
            "events": [{"id": "1", "name": "X", "date": "2026-11-23T10:00:00+0000"}]
        }
        start, stop, _, _, _ = raiitalia.parse_day(payload)[0]
        self.assertEqual(stop - start, timedelta(minutes=30))

    def test_rows_without_date_or_name_are_skipped(self):
        payload = {
            "events": [
                {"id": "1", "name": "No date"},
                {"id": "2", "name": "", "date": "2026-11-23T10:00:00+0000"},
            ]
        }
        self.assertEqual(raiitalia.parse_day(payload), [])


class MergeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_same_day_twice_is_deduped(self):
        merged = raiitalia.merge([self.payload, self.payload], DAY)
        self.assertEqual(len(merged), len(raiitalia.merge([self.payload], DAY)))

    def test_overlaps_are_dropped_so_the_day_is_linear(self):
        merged = raiitalia.merge([self.payload], DAY)
        self.assertLess(len(merged), 54)  # the file's two grids overlap heavily
        for (start, stop, title, _), (next_start, _, _, _) in zip(merged, merged[1:]):
            self.assertLessEqual(
                stop, next_start, f"{title} overlaps the next programme"
            )

    def test_window_clips_days_outside_it(self):
        merged = raiitalia.merge([self.payload], date(2026, 11, 24), 1)
        self.assertTrue(all(start.date() == date(2026, 11, 24) for start, *_ in merged))

    def test_sorted_and_non_zero(self):
        merged = raiitalia.merge([self.payload], DAY)
        starts = [row[0] for row in merged]
        self.assertEqual(starts, sorted(starts))
        self.assertTrue(all(stop > start for start, stop, *_ in merged))


if __name__ == "__main__":
    unittest.main()
