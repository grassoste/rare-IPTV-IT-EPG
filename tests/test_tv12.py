import unittest
from datetime import date, timedelta
from pathlib import Path

from sources import tv12

FIXTURE = Path(__file__).parent / "fixtures" / "tv12.html"
DAY = date(2026, 11, 26)


class ParseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.when, cls.events = tv12.parse_page(FIXTURE.read_text(encoding="utf-8"))

    def test_page_date(self):
        self.assertEqual(self.when, DAY)

    def test_every_row_parsed(self):
        self.assertEqual(len(self.events), 47)

    def test_source_order_is_kept(self):
        # the table starts at 05:00 and wraps after 23:49; it must not be sorted by clock time
        self.assertEqual(self.events[0][:3], (5, 0, "TG UDINE"))
        self.assertGreater(self.events[0][0], self.events[-1][0])

    def test_descriptions_are_read(self):
        described = [row for row in self.events if row[3]]
        self.assertTrue(described)
        self.assertTrue(described[0][3].isupper() or described[0][3][0].isupper())

    def test_garbage_yields_nothing(self):
        self.assertEqual(tv12.parse_page("<html>hello</html>"), (None, []))


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        when, events = tv12.parse_page(FIXTURE.read_text(encoding="utf-8"))
        cls.programmes = tv12.build(when, events)

    def test_durations_follow_the_next_start(self):
        self.assertEqual(self.programmes[0][1], self.programmes[1][0])

    def test_night_rows_move_to_the_next_day(self):
        # 23:49 -> 00:12 crosses midnight
        late = [p for p in self.programmes if p[0].hour < 5]
        self.assertTrue(late)
        self.assertEqual(late[0][0].date(), DAY + timedelta(days=1))

    def test_all_durations_positive_and_ordered(self):
        self.assertTrue(all(stop > start for start, stop, *_ in self.programmes))
        starts = [row[0] for row in self.programmes]
        self.assertEqual(starts, sorted(starts))

    def test_last_programme_gets_the_default_hour(self):
        tail = tv12.build(DAY, [(23, 50, "Late", None)])
        self.assertEqual((tail[0][1] - tail[0][0]).seconds // 60, 60)


if __name__ == "__main__":
    unittest.main()
