import unittest
from datetime import date
from pathlib import Path

from sources import iuniortv as itv

FIXTURE = Path(__file__).parent / "fixtures" / "iuniortv.html"
TODAY = date(2026, 11, 22)  # a Sunday, the day the fixture was saved


class GuideTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guide = itv.parse_guide(FIXTURE.read_text(encoding="utf-8"))

    def test_seven_weekday_blocks(self):
        self.assertEqual(sorted(self.guide), list(range(7)))

    def test_every_row_parsed(self):
        # If the fixture is refreshed, update the expected count.
        self.assertEqual(sum(len(rows) for rows in self.guide.values()), 262)

    def test_first_row_of_monday(self):
        self.assertEqual(self.guide[0][0], (7, 0, "CARTOONS STORY"))

    def test_comma_times_and_dash_separator(self):
        titles = {title for rows in self.guide.values() for _, _, title in rows}
        self.assertIn("LA NOTTE DI IUNIOR TV", titles)

    def test_garbage_input_yields_nothing(self):
        self.assertEqual(itv.parse_guide("<html><p>hello</p></html>"), {})


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guide = itv.parse_guide(FIXTURE.read_text(encoding="utf-8"))
        cls.programmes = itv.build(cls.guide, TODAY, 7)

    def test_every_broadcast_day_starts_at_seven(self):
        first_rows = {
            start.date(): title
            for start, _, title in self.programmes
            if start.hour == 7 and start.minute == 0
        }
        self.assertEqual(
            sorted(first_rows), [date(2026, 11, 22 + offset) for offset in range(7)]
        )
        self.assertEqual(first_rows[date(2026, 11, 23)], "CARTOONS STORY")

    def test_tails_spill_into_the_following_morning(self):
        # Each block ends at 01,00 of the next calendar day; Saturday's tail stops at 07,00.
        self.assertEqual(
            max(start.date() for start, _, _ in self.programmes), date(2026, 11, 29)
        )

    def test_after_midnight_rows_land_on_the_next_day(self):
        night = [p for p in self.programmes if p[2] == "LA NOTTE DI IUNIOR TV"]
        self.assertEqual(len(night), 7)
        self.assertTrue(all(start.hour == 1 for start, _, _ in night))
        self.assertEqual(night[0][0].date(), date(2026, 11, 23))  # Monday's tail

    def test_durations_positive_and_ordered(self):
        self.assertTrue(all(stop > start for start, stop, _ in self.programmes))
        starts = [start for start, _, _ in self.programmes]
        self.assertEqual(starts, sorted(starts))

    def test_day_window_limits_the_output(self):
        guide = itv.parse_guide(FIXTURE.read_text(encoding="utf-8"))
        today_only = itv.build(guide, TODAY, 1)
        self.assertEqual(len(today_only), len(self.guide[6]))
        self.assertEqual(
            {start.date() for start, _, _ in today_only},
            {date(2026, 11, 22), date(2026, 11, 23)},
        )

    def test_thin_guide_is_rejected(self):
        with self.assertRaises(RuntimeError):
            itv.build({0: [(7, 0, "ONLY ONE")]}, TODAY)


if __name__ == "__main__":
    unittest.main()
