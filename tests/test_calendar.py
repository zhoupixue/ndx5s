import datetime as dt
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from update_daily import catch_up_day, eligible

class CalendarTests(unittest.TestCase):
    def at(self,s):return eligible(dt.datetime.fromisoformat(s))
    def test_weekend_and_holiday(self):
        self.assertIsNone(self.at('2026-10-11T22:17:00+00:00'))
        self.assertIsNone(self.at('2026-12-25T22:17:00+00:00'))
    def test_summer_and_winter(self):
        self.assertEqual(str(self.at('2026-10-09T22:17:00+00:00')),'2026-10-09')
        self.assertEqual(str(self.at('2026-12-24T22:17:00+00:00')),'2026-12-24')
        self.assertIsNone(self.at('2026-12-23T21:14:59+00:00'))
        self.assertEqual(str(self.at('2026-12-23T21:15:00+00:00')),'2026-12-23')
        self.assertIsNone(self.at('2026-12-23T20:17:00+00:00'))
        self.assertEqual(str(self.at('2026-12-23T21:17:00+00:00')),'2026-12-23')
        self.assertIsNone(self.at('2026-10-09T20:14:59+00:00'))
        self.assertEqual(str(self.at('2026-10-09T20:17:00+00:00')),'2026-10-09')
    def test_early_close(self):
        self.assertEqual(str(self.at('2026-11-27T19:17:00+00:00')),'2026-11-27')
        self.assertIsNone(self.at('2026-11-27T18:14:59+00:00'))
        self.assertEqual(str(self.at('2026-11-27T18:15:00+00:00')),'2026-11-27')

    def test_catch_up_previous_session_after_midnight(self):
        now = dt.datetime.fromisoformat('2026-11-21T06:00:00+00:00')
        self.assertEqual(catch_up_day(now, dt.date(2026, 11, 19)), dt.date(2026, 11, 20))
        self.assertIsNone(catch_up_day(now, dt.date(2026, 11, 20)))

    def test_catch_up_respects_early_close_and_wait_window(self):
        now = dt.datetime.fromisoformat('2026-11-27T18:14:59+00:00')
        previous = dt.date(2026, 11, 25)
        self.assertIsNone(catch_up_day(now, previous))
        self.assertEqual(catch_up_day(now + dt.timedelta(seconds=1), previous), dt.date(2026, 11, 27))
