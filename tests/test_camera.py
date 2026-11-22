import unittest
from datetime import date, datetime
from pathlib import Path

from sources import camera

FIXTURE = Path(__file__).parent / "fixtures" / "camera-day.html"
EMPTY = Path(__file__).parent / "fixtures" / "camera-empty.html"


class ParseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.day, cls.events = camera.parse_day(FIXTURE.read_text(encoding="utf-8"))

    def test_day_heading(self):
        self.assertEqual(self.day, date(2026, 11, 23))

    def test_events_are_sorted_with_titles(self):
        self.assertEqual(len(self.events), 5)
        self.assertEqual(self.events[0][:2], (10, 0))
        self.assertTrue(self.events[0][2].startswith("Riconoscimento al merito"))
        self.assertTrue(self.events[-1][2].startswith("Per mano"))

    def test_time_is_not_the_hidden_label(self):
        # the .ora block also contains a hidden "Inizia alle" span
        self.assertTrue(all(0 <= hour < 24 for hour, _, _ in self.events))

    def test_empty_day_has_a_date_and_no_events(self):
        day, events = camera.parse_day(EMPTY.read_text(encoding="utf-8"))
        self.assertEqual(day, date(2026, 11, 22))
        self.assertEqual(events, [])

    def test_garbage_yields_nothing(self):
        self.assertEqual(camera.parse_day("<html>hello</html>"), (None, []))


class BuildTest(unittest.TestCase):
    def test_durations_follow_the_next_event(self):
        day = date(2026, 11, 23)
        events = [(10, 0, "A"), (10, 30, "B"), (14, 0, "C")]
        programmes = camera.build([(day, events)])
        self.assertEqual(programmes[0][1], programmes[1][0])
        self.assertEqual(programmes[1][1], programmes[2][0])

    def test_last_event_gets_the_default_hour(self):
        programmes = camera.build([(date(2026, 11, 23), [(23, 0, "Late")])])
        self.assertEqual((programmes[0][1] - programmes[0][0]).seconds // 60, 60)

    def test_shared_start_time_is_not_zero_length(self):
        events = [(10, 30, "A"), (10, 30, "B")]
        programmes = camera.build([(date(2026, 11, 23), events)])
        self.assertTrue(all(stop > start for start, stop, _ in programmes))

    def test_empty_day_contributes_nothing(self):
        self.assertEqual(camera.build([(date(2026, 11, 22), [])]), [])


if __name__ == "__main__":
    unittest.main()
