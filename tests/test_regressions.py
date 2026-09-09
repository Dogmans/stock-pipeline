"""Offline regressions; run with scripts/run_offline_regressions.py."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import main as pipeline
from reporting import generate_screening_report, generate_summary_report
from screeners.quality import QualityScreener


class QualityTests(unittest.TestCase):
    def test_decimal_thresholds(self):
        screener = QualityScreener()
        # Preserve the existing strict greater-than thresholds at the boundaries.
        for roe, profit, operating, expected in [
            (0.01, 0.01, 0.01, 0),
            (0.10, 0.10, 0.10, 0),
            (0.15, 0.20, 0.15, 3),
            (0.16, 0.21, 0.16, 7),
            (-0.10, -0.10, -0.10, 0),
        ]:
            with self.subTest(roe=roe, profit=profit, operating=operating):
                score = screener.calculate_score({
                    'ReturnOnEquityTTM': roe,
                    'ProfitMargin': profit,
                    'OperatingMarginTTM': operating,
                })
                self.assertEqual(score, expected)
                self.assertEqual(screener.meets_threshold(score), expected >= 6)

    def test_missing_metrics_and_display_units(self):
        screener = QualityScreener()
        self.assertIsNone(screener.calculate_score({'ReturnOnEquityTTM': 0.20}))
        self.assertEqual(screener.get_additional_data(
            'TEST', {'ReturnOnEquityTTM': 0.20}, 100)['roe'], 20)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.markdown = Path(self.temp.name) / 'report.md'
        self.summary = Path(self.temp.name) / 'summary.txt'
        self.rows = pd.DataFrame({
            'symbol': ['REJECT', 'PASS_A', 'PASS_B', 'UNKNOWN'],
            'score': [9, 8, 7, 6],
            'meets_threshold': [False, True, True, None],
        })

    def render(self, rows=None, limit=20, errors=None):
        results = {'quality': self.rows if rows is None else rows}
        generate_screening_report(results, self.markdown, limit, errors)
        generate_summary_report(results, self.summary, 'custom', 4, 'Normal', limit, errors)
        return self.markdown.read_text(encoding='utf-8'), self.summary.read_text(encoding='utf-8')

    def test_counts_and_candidates_use_only_passing_rows(self):
        markdown, summary = self.render()
        self.assertIn('at least one screener: **2**', markdown)
        self.assertIn('| quality | 4 | 2 | PASS_A |', markdown)
        for report in (markdown, summary):
            self.assertNotIn('REJECT', report)
            self.assertNotIn('UNKNOWN', report)
            self.assertIn('PASS_A', report)
            self.assertIn('PASS_B', report)
        self.assertEqual(len(self.rows), 4)

    def test_limits_apply_after_filtering(self):
        for limit in (0, 1, 20):
            with self.subTest(limit=limit):
                for report in self.render(limit=limit):
                    self.assertIn('PASS_A', report)
                    self.assertEqual('PASS_B' in report, limit != 1)
                    self.assertNotIn('REJECT', report)

    def test_no_passes_and_empty_results(self):
        for rows in (self.rows.assign(meets_threshold=False), pd.DataFrame()):
            for report in self.render(rows):
                self.assertIn('No stocks passed this screener.', report)
                self.assertNotIn('PASS_A', report)

    def test_legacy_prefiltered_results(self):
        for report in self.render(self.rows.iloc[1:3].drop(columns='meets_threshold'), limit=0):
            self.assertIn('PASS_A', report)
            self.assertIn('PASS_B', report)

    def test_failed_screener_is_not_reported_as_no_matches(self):
        for report in self.render(pd.DataFrame(), errors={'quality': 'provider failed'}):
            self.assertIn('Screening failed', report)
            self.assertNotIn('No stocks passed', report)

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            self.render(limit=-1)


class PipelineTests(unittest.TestCase):
    def test_real_quality_screener_through_pipeline_and_reports(self):
        profiles = {
            'WEAK': {'ReturnOnEquityTTM': .01, 'ProfitMargin': .01, 'OperatingMarginTTM': .01},
            'STRONG': {'ReturnOnEquityTTM': .20, 'ProfitMargin': .25, 'OperatingMarginTTM': .20},
        }
        with tempfile.TemporaryDirectory() as output:
            argv = ['main.py', '--symbols', 'WEAK,STRONG', '--strategies', 'quality',
                    '--output', output, '--limit', '0']
            # Only external data is mocked; run the actual registry, scoring and writers.
            with patch('sys.argv', argv), \
                 patch.object(pipeline, 'get_market_conditions', return_value={}), \
                 patch.object(pipeline, 'is_market_in_correction', return_value=(False, 'Normal')), \
                 patch.object(pipeline, 'get_sector_performances', return_value={}), \
                 patch('data_providers.FinancialModelingPrepProvider.get_company_overview',
                       side_effect=lambda symbol: dict(profiles[symbol])), \
                 patch('screeners.base_screener.BaseScreener._get_current_price', return_value=100):
                self.assertEqual(pipeline.main(), 0)
            markdown = Path(output, 'screening_report_sp500.md').read_text(encoding='utf-8')
            summary = Path(output, 'summary_sp500.txt').read_text(encoding='utf-8')
            self.assertIn('| quality | 2 | 1 | STRONG |', markdown)
            for report in (markdown, summary):
                self.assertIn('STRONG', report)
                self.assertNotIn('WEAK', report)

    def test_failure_keeps_other_results_and_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as output:
            argv = ['main.py', '--symbols', 'TEST', '--strategies', 'quality,pe_ratio', '--output', output]
            successful = pd.DataFrame({'symbol': ['GOOD'], 'score': [5], 'meets_threshold': [True]})
            with patch('sys.argv', argv), \
                 patch.object(pipeline, 'get_market_conditions', return_value={}), \
                 patch.object(pipeline, 'is_market_in_correction', return_value=(False, 'Normal')), \
                 patch.object(pipeline, 'get_sector_performances', return_value={}), \
                 patch.object(pipeline, 'run_screener', side_effect=[RuntimeError('offline failure'), successful]):
                self.assertEqual(pipeline.main(), 1)
            for filename in ('screening_report_sp500.md', 'summary_sp500.txt'):
                report = Path(output, filename).read_text(encoding='utf-8')
                self.assertIn('Screening failed', report)
                self.assertIn('GOOD', report)


if __name__ == '__main__':
    unittest.main()
