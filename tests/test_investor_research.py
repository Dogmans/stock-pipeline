import json
import unittest
from unittest.mock import Mock, patch

import pandas as pd
from fastapi.testclient import TestClient

from investor_research import evidence, financials, prices
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
from cache_config import cache
from tests.test_visual_api import FakeManager, FakeStockService
from visual_api import create_app


class InvestorResearchTests(unittest.TestCase):
    def provider(self, data):
        provider = Mock()
        provider.get_research_statements.side_effect = lambda symbol, statement, annual=True: pd.DataFrame(data.get(statement, []))
        return provider

    def test_statement_alignment_growth_margins_capex_and_fcf_fallback(self):
        provider = self.provider({
            'income': [
                {'date':'2025-12-31','revenue':120,'operatingIncome':24,'netIncome':12,'epsDiluted':3,'weightedAverageShsOutDil':4,'reportedCurrency':'USD','period':'FY','filingDate':'2026-02-01','finalLink':'https://sec.gov/example'},
                {'date':'2024-12-31','totalRevenue':100,'netIncome':10,'reportedCurrency':'USD','period':'FY'},
            ],
            'cash_flow': [{'date':'2025-12-31','netCashProvidedByOperatingActivities':30,'capitalExpenditure':-8,'reportedCurrency':'USD'}],
            'balance': [{'date':'2025-12-31','cashAndCashEquivalents':5,'totalDebt':20,'reportedCurrency':'USD'}],
        })
        data = financials(provider,'ABC')
        row = data['periods'][-1]
        self.assertEqual(row['capex'],8)
        self.assertEqual(row['free_cash_flow'],22)
        self.assertEqual(row['net_debt'],15)
        self.assertEqual(row['fcf_per_share'],5.5)
        self.assertAlmostEqual(row['yoy']['revenue'],.2)
        self.assertEqual(row['operating_income_margin'],.2)
        self.assertIsNone(data['periods'][0]['net_debt'])
        self.assertEqual(row['sources']['income']['filed_at'],'2026-02-01')
        json.dumps(data,allow_nan=False)

    def test_quarterly_growth_uses_same_quarter_not_adjacent_quarter(self):
        provider = self.provider({'income':[
            {'date':'2025-03-31','period':'Q1','revenue':100,'netIncome':-2,'reportedCurrency':'USD'},
            {'date':'2025-12-31','period':'Q4','revenue':1000,'reportedCurrency':'USD'},
            {'date':'2026-03-31','period':'Q1','revenue':120,'netIncome':4,'reportedCurrency':'USD'},
        ]})
        data = financials(provider,'ABC',annual=False)
        self.assertEqual(data['period'],'quarter')
        self.assertAlmostEqual(data['periods'][-1]['yoy']['revenue'],.2)
        self.assertIsNone(data['periods'][-1]['yoy']['net_income'])
        self.assertEqual(data['missing'],['balance','cash_flow'])

    def test_missing_nonfinite_and_currency_mismatch_do_not_become_zeroes(self):
        provider = self.provider({
            'income':[{'date':'2025-12-31','revenue':0,'netIncome':float('nan'),'reportedCurrency':'USD','link':'javascript:alert(1)'},
                      {'date':'not-a-date','revenue':10}],
            'balance':[{'date':'2025-12-31','totalDebt':10,'reportedCurrency':'CAD'}],
        })
        data = financials(provider,'ABC')
        self.assertEqual(len(data['periods']),1)
        row = data['periods'][0]
        self.assertIsNone(row['net_income'])
        self.assertIsNone(row['net_income_margin'])
        self.assertIsNone(row['sources']['income']['url'])
        self.assertNotIn('debt',row)
        self.assertTrue(data['warnings'])
        json.dumps(data,allow_nan=False)

    def test_statement_failure_keeps_other_observations(self):
        provider = Mock()
        def fetch(symbol,statement,annual=True):
            if statement=='balance': raise RuntimeError('offline')
            return pd.DataFrame([{'date':'2025-12-31','revenue':100,'reportedCurrency':'USD'}])
        provider.get_research_statements.side_effect = fetch
        with self.assertLogs('investor_research',level='ERROR'):
            data=financials(provider,'ABC')
        self.assertEqual(data['missing'],['balance'])
        self.assertEqual(data['periods'][0]['revenue'],100)

    def test_margin_changes_are_percentage_points_and_unknown_currency_is_not_inferred(self):
        provider=self.provider({'income':[
            {'date':'2025-12-31','revenue':100,'operatingIncome':20,'reportedCurrency':'USD'},
            {'date':'2024-12-31','revenue':80,'operatingIncome':8,'reportedCurrency':'USD'}]})
        row=financials(provider,'ABC')['periods'][-1]
        self.assertAlmostEqual(row['yoy_pp']['operating_income_margin'],.1)
        self.assertAlmostEqual(row['yoy']['operating_income'],1.5)
        provider=self.provider({'income':[{'date':'2025-12-31','revenue':100,'operatingIncome':20}],
            'balance':[{'date':'2025-12-31','cash':5,'totalDebt':10,'reportedCurrency':'USD'}],
            'cash_flow':[{'date':'2025-12-31','freeCashFlow':20,'reportedCurrency':'USD'}]})
        row=financials(provider,'ABC')['periods'][-1]
        self.assertNotIn('currency',row)
        self.assertIsNone(row['free_cash_flow_margin'])

    def test_earnings_zero_and_negative_estimate_surprises(self):
        provider=Mock()
        provider.get_earnings_reports.return_value=[{'date':'2026-01-31','epsActual':-.1,'epsEstimated':-.2,
                                                   'revenueActual':100,'revenueEstimated':0}]
        row=evidence(provider,'ABC','earnings')['rows'][0]
        self.assertAlmostEqual(row['eps_surprise'],.5)
        self.assertIsNone(row['revenue_surprise'])
        provider.get_earnings_reports.side_effect=RuntimeError('offline')
        with self.assertLogs('investor_research',level='ERROR'):
            self.assertTrue(evidence(provider,'ABC','earnings')['missing'])

    def test_estimate_aliases_and_safe_filings(self):
        provider=Mock()
        provider.get_analyst_estimates.return_value=pd.DataFrame([{'date':'2027-12-31','revenueAvg':100,'estimatedEpsAvg':2,'numAnalystsRevenue':5}])
        row=evidence(provider,'ABC','estimates')['rows'][0]
        self.assertEqual(row['revenue_avg'],100)
        self.assertEqual(row['eps_avg'],2)
        self.assertEqual(row['analysts'],5)
        provider.get_research_filings.return_value=[{'filingDate':'2026-02-01','formType':'10-K','finalLink':'file:///secret'},
                                                   {'filingDate':'2026-02-02','formType':'10-Q','link':'https://sec.gov/report'}]
        rows=evidence(provider,'ABC','filings')['rows']
        self.assertEqual(rows[0]['url'],'https://sec.gov/report')
        self.assertIsNone(rows[1]['url'])

    def test_prices_sort_deduplicate_and_discard_invalid_closes(self):
        provider=Mock()
        provider.get_price_change_history.return_value=pd.DataFrame([
            {'Date':'2025-01-03','Close':20},{'Date':'2025-01-02','Close':10},
            {'Date':'2025-01-03','Close':21},{'Date':'2025-01-04','Close':0},
            {'Date':'2025-01-05','Close':float('inf')}])
        data=prices(provider,'ABC')
        self.assertEqual([r['close'] for r in data['prices']],[10,21])
        json.dumps(data,allow_nan=False)

    def test_api_research_routes_validation_and_period(self):
        service=FakeStockService()
        service.provider=self.provider({})
        service.provider.get_earnings_reports.return_value=[]
        service.provider.get_price_change_history.return_value=pd.DataFrame()
        with TestClient(create_app(FakeManager(),service)) as client:
            self.assertEqual(client.get('/api/stocks/aapl/research').json()['symbol'],'AAPL')
            self.assertEqual(client.get('/api/stocks/AAPL/research?period=quarter').json()['period'],'quarter')
            for path in ['/api/stocks/bad!/research','/api/stocks/bad!/prices','/api/stocks/bad!/evidence/earnings',
                         '/api/stocks/AAPL/research?period=monthly','/api/stocks/AAPL/evidence/unknown']:
                self.assertEqual(client.get(path).status_code,422,path)
            self.assertTrue(client.get('/api/stocks/AAPL/evidence/earnings').json()['missing'])
            self.assertTrue(client.get('/api/stocks/AAPL/prices').json()['missing'])

    def test_stable_transport_routes_research_without_changing_screener_history(self):
        provider=FinancialModelingPrepProvider(api_key='offline-test')
        response=Mock(status_code=200)
        response.json.return_value=[{'date':'2025-12-31','revenue':100}]
        with patch('data_providers.financial_modeling_prep.fmp_http_session.get',return_value=response) as get, \
             patch('data_providers.financial_modeling_prep.fmp_rate_limiter.wait_if_needed'):
            self.assertTrue(provider._make_api_request('income-statement','ABC',{'limit':10},stable=True)[0])
            self.assertEqual(get.call_args.args[0],'https://financialmodelingprep.com/stable/income-statement')
            self.assertEqual(get.call_args.kwargs['params']['symbol'],'ABC')
            provider._make_api_request('income-statement','ABC')
            self.assertEqual(get.call_args.args[0],'https://financialmodelingprep.com/api/v3/income-statement/ABC')

    def test_bad_vendor_date_does_not_discard_the_entire_statement_history(self):
        provider = FinancialModelingPrepProvider(api_key='offline-research-dates')
        key = provider.get_research_statements.__cache_key__(provider, 'DATE_TEST', 'income', annual=True)
        cache.delete(key)
        raw = [{'date':'2025-12-31','revenue':120,'reportedCurrency':'USD'},
               {'date':'2024-12-31','revenue':100,'reportedCurrency':'USD'},
               {'date':'invalid-date','revenue':999,'reportedCurrency':'USD'}]
        try:
            with patch.object(FinancialModelingPrepProvider, '_make_api_request', return_value=(True, raw, None)):
                frame = provider.get_research_statements('DATE_TEST', 'income', annual=True)
            data = financials(self.provider({'income':frame}), 'DATE_TEST')
            self.assertEqual([r['date'] for r in data['periods']], ['2024-12-31','2025-12-31'])
            self.assertEqual(data['periods'][-1]['revenue'], 120)
            self.assertAlmostEqual(data['periods'][-1]['yoy']['revenue'], .2)
        finally:
            cache.delete(key)

    def test_aliases_fall_back_when_the_preferred_date_column_is_null(self):
        provider = self.provider({'income':[
            {'fiscalDateEnding':'2025-12-31','revenue':120,'reportedCurrency':'USD'},
            {'date':'2024-12-31','revenue':100,'reportedCurrency':'USD',
             'filingDate':None,'fillingDate':'2025-02-01'}]})
        rows = financials(provider, 'ABC')['periods']
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['sources']['income']['filed_at'], '2025-02-01')
        self.assertEqual(rows[-1]['revenue'], 120)
        provider.get_price_change_history.return_value = pd.DataFrame([
            {'Date':'2025-01-02','Close':10}, {'date':'2025-01-03','close':11}])
        self.assertEqual([r['date'] for r in prices(provider,'ABC')['prices']], ['2025-01-02','2025-01-03'])

    def test_unknown_fiscal_quarters_do_not_claim_same_quarter_growth(self):
        provider = self.provider({'income':[
            {'date':'2025-03-31','revenue':120,'reportedCurrency':'USD'},
            {'date':'2024-03-31','revenue':100,'reportedCurrency':'USD'}]})
        rows = financials(provider, 'ABC', annual=False)['periods']
        self.assertEqual(rows[-1]['fiscal_period'], 'Quarter')
        self.assertEqual(rows[-1]['yoy'], {})

    def test_benchmark_uses_the_same_case_normalization_as_stock_routes(self):
        service = FakeStockService()
        service.provider = self.provider({})
        manager = FakeManager()
        manager.archive = Mock()
        with patch('visual_api.forward_performance', return_value={'benchmark':'SPY'}) as performance, \
             TestClient(create_app(manager, service)) as client:
            self.assertEqual(client.get('/api/history/abc/performance?output_id=o&benchmark=spy').json()['benchmark'], 'SPY')
        self.assertEqual(performance.call_args.args[-1], 'SPY')
