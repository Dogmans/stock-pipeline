"""Offline behavioural coverage for the research universe and flow integration."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import main
import pandas as pd
from screeners.proven_technology_emerging_tam import ProvenTechnologyEmergingTAMScreener, history
from screening_audit import build_audit, write_audit
from workflow import WorkflowEngine, WorkflowError, validate_workflow
from utils.screener_registry import default_screeners
from data_providers.fmp_screening import FMPScreeningProvider


def inputs():
    return {'profile': {'sector': 'Industrials', 'industry': 'Electronic Components', 'exchange': 'NASDAQ',
                        'country': 'TW', 'isEtf': False, 'isFund': False, 'isActivelyTrading': True},
            'metrics': {'market_cap_usd': 200_000_000, 'revenue_usd': 30_000_000,
                        'gross_margin_pct': 30, 'revenue_growth_pct': 0, 'daily_dollar_volume_usd': 200_000,
                        'statement_age_days': 120, 'operating_cash_flow': -2_000_000, 'runway_months': 24,
                        'ev_sales': 3, 'debt_ebitda': 1, 'dilution_pct': 0}}


def flow():
    return {'version': 1, 'universe': {'symbols': ['HIMX', 'LTRX', 'PNG.V']},
            'nodes': [{'id': 'u', 'type': 'universe'}, {'id': 's', 'type': 'screener',
                      'screener': 'proven_technology_emerging_tam', 'params': {'min_gross_margin_pct': 25}},
                      {'id': 'o', 'type': 'output'}],
            'edges': [{'id': 'a', 'source': 'u', 'target': 's'}, {'id': 'b', 'source': 's', 'target': 'o'}]}


class TAMTests(unittest.TestCase):
    def setUp(self):
        self.screen = ProvenTechnologyEmergingTAMScreener()

    def test_industrial_foreign_company_passes_without_theme(self):
        row = self.screen.evaluate(inputs())
        self.assertTrue(row['meets_threshold'])
        self.assertEqual(row['score'], 100)
        self.assertEqual(len(row['checks']), 10)

    def test_boundaries_strict_revenue_margin_growth_inclusive_cap(self):
        for field, value, failed in [('market_cap_usd', 100_000_000, False),
                                     ('market_cap_usd', 2_500_000_000, False),
                                     ('market_cap_usd', 99_999_999, True),
                                     ('revenue_usd', 20_000_000, True),
                                     ('gross_margin_pct', 20, True), ('revenue_growth_pct', -15, True),
                                     ('daily_dollar_volume_usd', 100_000, False)]:
            data = inputs(); data['metrics'][field] = value
            with self.subTest(field=field, value=value):
                self.assertEqual(self.screen.evaluate(data)['outcome'], 'failed' if failed else 'passed')

    def test_penalties_do_not_exclude(self):
        data = inputs(); data['metrics'].update(ev_sales=20, debt_ebitda=10, dilution_pct=40)
        row = self.screen.evaluate(data)
        self.assertTrue(row['meets_threshold'])
        self.assertLess(row['score'], 100)
        self.assertFalse(row['failed_rules'])

    def test_unknown_is_retained_and_known_failure_takes_precedence(self):
        data = inputs(); data['metrics']['gross_margin_pct'] = None
        row = self.screen.evaluate(data)
        self.assertIsNone(row['meets_threshold'])
        self.assertEqual(row['outcome'], 'unavailable')
        data['metrics']['revenue_usd'] = 0
        self.assertEqual(self.screen.evaluate(data)['outcome'], 'failed')

    def test_survivability_or_condition(self):
        for ocf, runway, outcome in [(1, None, 'passed'), (-1, 12, 'passed'), (-1, 11, 'failed'), (-1, None, 'unavailable')]:
            data = inputs(); data['metrics'].update(operating_cash_flow=ocf, runway_months=runway)
            self.assertEqual(self.screen.evaluate(data)['outcome'], outcome)

    def test_structural_exclusions_and_biotech_operating_revenue(self):
        for override in [{'isEtf': True}, {'isFund': True}, {'sector': 'Financial Services'},
                         {'industry': 'REIT - Industrial'}, {'industry': 'Shell Companies'},
                         {'industry': 'Mineral Exploration'}, {'isActivelyTrading': False}]:
            data = inputs(); data['profile'].update(override)
            self.assertIn('security_type', self.screen.evaluate(data)['failed_rules'])
        data = inputs(); data['profile'].update(sector='Healthcare', industry='Biotechnology')
        self.assertTrue(self.screen.evaluate(data)['meets_threshold'])
        data['metrics']['revenue_usd'] = 0
        self.assertIn('revenue', self.screen.evaluate(data)['failed_rules'])

    def test_invalid_parameters_and_opt_in(self):
        for kwargs in [{'candidate_limit': 1.5}, {'min_revenue': float('nan')}, {'min_market_cap': 3_000_000_000}, {'min_gross_margin_pct': 101}]:
            with self.assertRaises(ValueError):
                ProvenTechnologyEmergingTAMScreener(**kwargs)
        self.assertNotIn('proven_technology_emerging_tam', default_screeners())

    def test_audit_caps_do_not_change_pass_and_benchmarks_do_not_inflate_funnel(self):
        screen = ProvenTechnologyEmergingTAMScreener(candidate_limit=1, near_miss_limit=1)
        records = []
        for symbol, revenue in [('A', 30_000_000), ('B', 30_000_000), ('C', 19_000_000), ('D', 18_000_000)]:
            data = inputs(); data['metrics']['revenue_usd'] = revenue
            records.append({'symbol': symbol, **screen.evaluate(data)})
        audit = build_audit(screen, records, evaluate_benchmarks=False)
        self.assertEqual(audit['summary']['initial_universe_count'], 4)
        self.assertEqual(audit['summary']['all_hard_filters_pass_count'], 2)
        self.assertEqual(audit['summary']['final_candidate_count'], 1)
        self.assertEqual(audit['near_misses'][0]['symbol'], 'C')
        with tempfile.TemporaryDirectory() as directory:
            write_audit(audit, directory)
            self.assertEqual(len(list(Path(directory).glob('*.json'))), 4)
            self.assertEqual(json.loads((Path(directory) / 'proven_technology_emerging_tam_summary.json').read_text())['near_miss_count'], 1)

    def test_workflow_records_effective_settings_and_prohibits_score_bypass(self):
        def factory(name, **params):
            screen = ProvenTechnologyEmergingTAMScreener(**params)
            screen.load_data = lambda symbol: {**inputs(), 'source_dates': {}}
            return screen
        result = WorkflowEngine(factory=factory).execute(flow())
        node = result['nodes']['s']
        self.assertEqual(node['rule']['settings']['min_gross_margin_pct'], 25)
        self.assertEqual(node['screening_audit']['summary']['initial_universe_count'], 3)
        self.assertEqual(node['counts']['passed'], 3)
        invalid = flow(); invalid['nodes'][1]['criterion'] = {'operator': 'gte', 'value': 0}
        with self.assertRaisesRegex(WorkflowError, 'eligibility'):
            validate_workflow(invalid)

    def test_eight_quarter_ttm_currency_runway_dilution(self):
        provider = Mock()
        provider.profile.return_value = {**inputs()['profile'], 'currency': 'CAD', 'price': 5,
                                         'marketCap': 400_000_000, 'averageVolume': 100_000}
        provider.usd_rate.side_effect = lambda c: {'rate': .75 if c == 'CAD' else 1, 'pair': c + 'USD'}
        dates = pd.date_range(end='2026-06-30', periods=8, freq='QE')[::-1]
        base = pd.DataFrame({'fiscalDateEnding': dates, 'reportedCurrency': 'USD'})
        income = base.assign(totalRevenue=[10_000_000] * 4 + [8_000_000] * 4,
                             grossProfit=3_000_000, ebitda=1_000_000, weightedAverageShsOutDil=[11] * 4 + [10] * 4)
        balance = base.head(1).assign(cash=8_000_000, totalDebt=4_000_000, totalCurrentAssets=12_000_000, totalCurrentLiabilities=6_000_000)
        cf = base.head(4).assign(operatingCashflow=-1_000_000, freeCashflow=-1_500_000)
        provider.statements.side_effect = lambda endpoint, symbol, period: {'income-statement': income, 'balance-sheet-statement': balance, 'cash-flow-statement': cf}[endpoint]
        self.screen.provider = provider
        data = self.screen.load_data('PNG.V')
        m = data['metrics']
        self.assertEqual(m['market_cap_usd'], 300_000_000)
        self.assertEqual(m['revenue_usd'], 40_000_000)
        self.assertEqual(m['revenue_growth_pct'], 25)
        self.assertEqual(m['runway_months'], 24)
        self.assertAlmostEqual(m['dilution_pct'], 10)
        self.assertEqual(m['ev_sales'], 7.4)
        bad = income.copy(); bad.loc[1, 'reportedCurrency'] = 'CAD'
        self.assertIsNone(history(bad, 8))
        self.assertIsNone(history(income.head(6), 8))

    def test_fetch_retries_and_never_caches_failure(self):
        provider = FMPScreeningProvider(api_key='offline-tam')
        fail = Mock(status_code=429, headers={'Retry-After': '0'})
        success = Mock(status_code=200); success.json.return_value = [{'symbol': 'TEST'}]
        from cache_config import cache
        key = provider.fetch.__cache_key__(provider, 'profile', 'TEST')
        cache.delete(key)
        try:
            with patch('data_providers.fmp_screening.fmp_http_session.get', side_effect=[fail, success]) as get, patch('data_providers.fmp_screening.fmp_rate_limiter.wait_if_needed'), patch('data_providers.fmp_screening.time.sleep'):
                self.assertEqual(provider.fetch('profile', 'TEST')['records'][0]['symbol'], 'TEST')
                self.assertEqual(get.call_count, 2)
            cache.delete(key)
            with patch('data_providers.fmp_screening.fmp_http_session.get', return_value=Mock(status_code=403)), patch('data_providers.fmp_screening.fmp_rate_limiter.wait_if_needed'):
                with self.assertRaisesRegex(RuntimeError, 'HTTP 403'):
                    provider.fetch('profile', 'TEST')
                self.assertNotIn(key, cache)
        finally:
            cache.delete(key)

    def test_annual_fallback_and_currency_mismatch(self):
        provider = Mock()
        provider.profile.return_value = {**inputs()['profile'], 'currency': 'USD', 'price': 5,
                                         'marketCap': 200_000_000, 'averageVolume': 100_000}
        provider.usd_rate.return_value = {'rate': 1}
        base = pd.DataFrame({'fiscalDateEnding': pd.to_datetime(['2025-12-31', '2024-12-31']), 'reportedCurrency': 'USD'})
        income = base.assign(totalRevenue=[40_000_000, 35_000_000], grossProfit=12_000_000, ebitda=4_000_000)
        balance = base.head(1).assign(reportedCurrency='CAD', cash=5_000_000, totalDebt=4_000_000)
        cf = base.head(1).assign(operatingCashflow=-2_000_000, freeCashflow=-3_000_000)
        def statements(endpoint, symbol, period):
            if period == 'quarter':
                raise RuntimeError('Quarterly history unavailable')
            return {'income-statement': income, 'balance-sheet-statement': balance, 'cash-flow-statement': cf}[endpoint]
        provider.statements.side_effect = statements
        self.screen.provider = provider
        data = self.screen.load_data('A')
        self.assertEqual(data['metrics']['revenue_basis'], 'annual')
        self.assertNotIn('runway_months', data['metrics'])
        self.assertEqual(self.screen.evaluate(data)['outcome'], 'unavailable')

    def test_stage_skips_structural_exclusions_but_keeps_boundary_misses(self):
        provider = Mock()
        provider.profile.return_value = {**inputs()['profile'], 'isFund': True, 'currency': 'USD', 'marketCap': 200_000_000}
        provider.usd_rate.return_value = {'rate': 1}
        self.screen.provider = provider
        data = self.screen.load_data('FUND')
        provider.statements.assert_not_called()
        row = self.screen.evaluate(data)
        self.assertEqual(row['outcome'], 'failed')
        self.assertTrue(any(c['status'] == 'not_evaluated' for c in row['checks']))
        provider.profile.return_value.update(isFund=False, marketCap=90_000_000)
        provider.statements.side_effect = RuntimeError('Missing statements')
        self.screen.load_data('NEAR')
        self.assertTrue(provider.statements.called)

    def test_listing_universe_preserves_suffix_and_scope(self):
        provider = FMPScreeningProvider(api_key='offline')
        provider.fetch = Mock(return_value={'records': [{'symbol':'PNG.V','exchange':'TSXV'}, {'symbol':'A','exchange':'NASDAQ'}, {'symbol':'B.L','exchange':'LSE'}]})
        self.assertEqual(provider.listing_universe().symbol.tolist(), ['PNG.V', 'A'])


if __name__ == '__main__':
    unittest.main()
