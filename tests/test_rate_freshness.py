import unittest

import pandas as pd

import ndx5s_daily as engine


class RateFreshnessTests(unittest.TestCase):
    def test_newer_backup_and_no_future_observations(self):
        target = pd.Timestamp("2026-11-18")
        fred = pd.Series([1.0], index=[target - pd.Timedelta(days=2)])
        treasury = pd.Series([2.0, 3.0], index=[
            target - pd.Timedelta(days=1), target + pd.Timedelta(days=1)
        ])
        engine.SOURCES.pop("test rate", None)
        self.addCleanup(engine.SOURCES.pop, "test rate", None)
        sources = [("FRED", lambda: fred), ("Treasury", lambda: treasury)]
        chosen = engine.first_ok("test rate", sources, required_date=target, allow_previous=True)
        pd.testing.assert_series_equal(chosen, treasury.iloc[:1])
        self.assertEqual(engine.SOURCES["test rate"], ["Treasury", "2026-11-17"])

    def test_current_primary_skips_backup(self):
        target = pd.Timestamp("2026-11-18")
        fred = pd.Series([1.0], index=[target])
        self.addCleanup(engine.SOURCES.pop, "test rate", None)

        def backup():
            self.fail("同日主源有效，备用源不应被调用")

        chosen = engine.first_ok("test rate", [("FRED", lambda: fred), ("Treasury", backup)],
                                 required_date=target, allow_previous=True)
        pd.testing.assert_series_equal(chosen, fred)
