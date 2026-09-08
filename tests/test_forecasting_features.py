"""
Tests for Feature Engineering & Anti-Target Leakage Guarantees.
"""

import datetime
from django.test import TestCase
import pandas as pd
import numpy as np

from apps.forecasting.features import build_features, get_feature_column_names


class ForecastingFeaturesTestCase(TestCase):
    def setUp(self):
        # 30-day sequence of deterministic values: 10, 20, 30, ...
        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        values = [(i + 1) * 10.0 for i in range(30)]
        self.df = pd.DataFrame({"target": values}, index=dates)

    def test_lag_features_correctness(self):
        """Verifies lag_1, lag_7, lag_14 match past target values exactly."""
        feat_df = build_features(self.df, drop_na=False)

        # On Jan 15 (index 14):
        # target is 150.0
        # lag_1 is Jan 14 value (140.0)
        # lag_7 is Jan 8 value (80.0)
        # lag_14 is Jan 1 value (10.0)
        row = feat_df.loc["2026-01-15"]
        self.assertEqual(row["lag_1"], 140.0)
        self.assertEqual(row["lag_7"], 80.0)
        self.assertEqual(row["lag_14"], 10.0)

    def test_shifted_rolling_features_zero_leakage(self):
        """
        CRITICAL TEST: Asserts that rolling_mean_7 at time t is computed
        exclusively over values up to t-1, completely unaffected by target at t.
        """
        feat_df_original = build_features(self.df, drop_na=False)
        orig_rolling_mean_at_jan15 = feat_df_original.loc["2026-01-15", "rolling_mean_7"]

        # Modify the target value at Jan 15 from 150.0 to an extreme outlier: 999999.0
        leaked_df = self.df.copy()
        leaked_df.loc["2026-01-15", "target"] = 999999.0

        feat_df_modified = build_features(leaked_df, drop_na=False)
        mod_rolling_mean_at_jan15 = feat_df_modified.loc["2026-01-15", "rolling_mean_7"]

        # If shifted properly, mod_rolling_mean_at_jan15 MUST BE IDENTICAL to orig_rolling_mean_at_jan15!
        self.assertEqual(orig_rolling_mean_at_jan15, mod_rolling_mean_at_jan15)

        # And target at Jan 15 must only influence t >= Jan 16
        self.assertNotEqual(
            feat_df_original.loc["2026-01-16", "rolling_mean_7"],
            feat_df_modified.loc["2026-01-16", "rolling_mean_7"],
        )

    def test_calendar_features(self):
        """Verifies correct extraction of day_of_week, month, and is_weekend."""
        feat_df = build_features(self.df, drop_na=True)

        # 2026-01-17 was Saturday (day_of_week = 5, is_weekend = 1)
        sat_row = feat_df.loc["2026-01-17"]
        self.assertEqual(sat_row["day_of_week"], 5)
        self.assertEqual(sat_row["is_weekend"], 1)
        self.assertEqual(sat_row["month"], 1)

        # 2026-01-19 was Monday (day_of_week = 0, is_weekend = 0)
        mon_row = feat_df.loc["2026-01-19"]
        self.assertEqual(mon_row["day_of_week"], 0)
        self.assertEqual(mon_row["is_weekend"], 0)

    def test_drop_na_removes_initial_lag_rows(self):
        """Verifies drop_na=True properly trims initial unpopulated lag rows."""
        feat_df = build_features(self.df, drop_na=True)
        # Max lag is 14, so initial 14 rows are removed: 30 - 14 = 16 rows remain
        self.assertEqual(len(feat_df), 16)
        self.assertFalse(feat_df.isna().any().any())
