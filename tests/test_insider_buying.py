import unittest
from datetime import datetime
from unittest.mock import Mock

import pandas as pd

from screeners.insider_buying import InsiderBuyingScreener


class InsiderTechnicalTests(unittest.TestCase):
    def setUp(self):
        self.screener = InsiderBuyingScreener()
        self.frame = pd.DataFrame({'Close': [100.0] * 40,
                                   'Volume': [100.0] * 30 + [300.0] * 10},
                                  index=pd.date_range('2026-01-01', periods=40))
        self.provider = Mock()
        self.provider.get_historical_prices.return_value = {'ABC': self.frame.iloc[::-1]}
        self.provider.get_company_overview.return_value = {}
        self.trade = dict(symbol='ABC', reportingName='Buyer', typeOfOwner='officer',
                          acquisitionOrDisposition='A', transactionType='Purchase',
                          price=100, securitiesTransacted=100000,
                          transactionDate=datetime.now().strftime('%Y-%m-%d'))

    def test_provider_contract_formulas_and_breakdown(self):
        self.provider.get_insider_trading.return_value = [self.trade]
        row = self.screener.screen_stocks(
            pd.DataFrame({'symbol': ['ABC'], 'security': ['Example']}), self.provider).iloc[0]
        self.provider.get_historical_prices.assert_called_once_with('ABC', period='3mo', interval='1d')
        self.assertEqual(row['consolidation_score'], 20)
        self.assertEqual(row['volume_score'], 10)
        self.assertEqual(row['relative_volume'], 2)
        self.assertTrue(row['consolidation_detected'])
        self.assertEqual(row['technical_status'], 'Available')
        self.assertEqual(row['score'], 65)
        self.assertTrue(row['meets_threshold'])
        self.assertEqual(row['score'], sum(row[k] for k in (
            'insider_activity_score', 'acceleration_score', 'consolidation_score', 'volume_score')))
        self.assertIn('consolidation 20.0/20', row['reason'])
        self.assertEqual(list(self.frame.columns), ['Close', 'Volume'])

    def test_no_purchases_remains_zero_without_fetch(self):
        trade = dict(self.trade, transactionType='Grant', price=0)
        metrics = self.screener.get_detailed_metrics('ABC', {}, None, [trade], self.provider)
        self.assertEqual(self.screener._total_score(metrics), 0)
        self.provider.get_historical_prices.assert_not_called()

    def test_missing_and_short_history(self):
        for history in ({}, {'ABC': self.frame.head(29)}):
            self.provider.get_historical_prices.return_value = history
            metrics = self.screener._technical_metrics('ABC', self.provider)
            self.assertEqual(metrics['technical_score'], 0)
            self.assertIsNone(metrics['consolidation_detected'])
            self.assertIn('Unavailable', metrics['technical_status'])

    def test_missing_volume_preserves_consolidation(self):
        self.provider.get_historical_prices.return_value = {'ABC': self.frame.drop(columns='Volume')}
        metrics = self.screener._technical_metrics('ABC', self.provider)
        self.assertEqual(metrics['technical_score'], 20)
        self.assertIsNone(metrics['relative_volume'])
        self.assertIn('Partial', metrics['technical_status'])

    def test_volatile_prices_and_flat_volume_get_zero(self):
        frame = self.frame.copy()
        frame['Close'] = [100, 120] * 20
        frame['Volume'] = 100
        self.provider.get_historical_prices.return_value = {'ABC': frame}
        metrics = self.screener._technical_metrics('ABC', self.provider)
        self.assertEqual(metrics['technical_score'], 0)
        self.assertFalse(metrics['consolidation_detected'])
        self.assertEqual(metrics['technical_status'], 'Available')

    def test_provider_error_is_explicit(self):
        self.provider.get_historical_prices.side_effect = RuntimeError('offline')
        metrics = self.screener._technical_metrics('ABC', self.provider)
        self.assertEqual(metrics['technical_score'], 0)
        self.assertIn('error', metrics['technical_status'])
