import json
import unittest
from datetime import date
from pathlib import Path

from sources import senato

FIXTURE = Path(__file__).parent / "fixtures" / "senato-day.json"
DAY = date(2026, 11, 23)


class ParseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.days = senato.parse_events(cls.payload, DAY)

    def test_every_event_appears_twice_in_the_payload(self):
        self.assertEqual(len(self.payload), 16)

    def test_rows_are_deduped_by_nid(self):
        self.assertEqual(sum(len(rows) for _, rows in self.days), 8)

    def test_date_comes_from_the_event_id(self):
        self.assertEqual([when for when, _ in self.days], [DAY])

    def test_times_and_titles_are_kept(self):
        titles = [title for _, rows in self.days for _, _, title in rows]
        self.assertIn("Convegno: Il 1956 nello specchio della Storia", titles)
        hours = {hour for _, rows in self.days for hour, _, _ in rows}
        self.assertEqual(hours, {10, 11, 12, 14, 16, 18})

    def test_missing_event_id_falls_back_to_the_requested_day(self):
        payload = [{"nid": "1", "title": "No id", "field_date": "09:15"}]
        days = senato.parse_events(payload, DAY)
        self.assertEqual(days, [(DAY, [(9, 15, "No id")])])

    def test_rows_without_time_or_title_are_skipped(self):
        payload = [
            {"nid": "1", "title": "", "field_date": "09:00"},
            {"nid": "2", "title": "No time", "field_date": ""},
        ]
        self.assertEqual(senato.parse_events(payload, DAY), [])

    def test_empty_payload_is_an_empty_schedule(self):
        self.assertEqual(senato.parse_events([], DAY), [])


class BuildTest(unittest.TestCase):
    def test_durations_follow_the_next_event(self):
        days = [(DAY, [(10, 0, "A"), (11, 0, "B")])]
        programmes = senato.build(days)
        self.assertEqual(programmes[0][1], programmes[1][0])

    def test_shared_start_time_is_not_zero_length(self):
        programmes = senato.build([(DAY, [(10, 0, "A"), (10, 0, "B")])])
        self.assertTrue(all(stop > start for start, stop, _ in programmes))

    def test_last_event_gets_the_default_hour(self):
        programmes = senato.build([(DAY, [(23, 0, "Late")])])
        self.assertEqual((programmes[0][1] - programmes[0][0]).seconds // 60, 60)


if __name__ == "__main__":
    unittest.main()
