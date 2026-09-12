import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
from fastapi.testclient import TestClient

from research import RunArchive, financial_history, forward_performance
from tests.test_workflow import document, CATALOG, FakeScreener
from tests.test_visual_api import FakeManager, FakeStockService
from visual_api import create_app
from workflow import WorkflowEngine, WorkflowError, validate_workflow


class ResearchTests(unittest.TestCase):
    def test_archive_survives_new_instance_and_rejects_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = RunArchive(directory)
            saved = archive.save('abc123', document(), {'nodes': {}})
            restored = RunArchive(directory)
            self.assertEqual(restored.get('abc123'), saved)
            self.assertEqual(restored.list()[0]['id'], 'abc123')
            with self.assertRaises(KeyError): restored.get('../secret')
            Path(directory, 'broken.json').write_text('invalid', encoding='utf-8')
            self.assertEqual(len(restored.list()), 1)

    def test_financial_history_aligns_periods_and_keeps_missing_fields(self):
        provider = Mock()
        provider.get_income_statement.return_value = pd.DataFrame([
            {'fiscalDateEnding': '2025-12-31', 'totalRevenue': 100, 'netIncome': 20, 'reportedCurrency': 'USD'},
            {'fiscalDateEnding': '2024-12-31', 'totalRevenue': 0, 'netIncome': 5, 'reportedCurrency': 'USD'}])
        provider.get_balance_sheet.return_value = pd.DataFrame([{'fiscalDateEnding': '2024-12-31', 'totalDebt': 10}])
        provider.get_cash_flow.side_effect = RuntimeError('Provider unavailable')
        result = financial_history(provider, 'ABC')
        self.assertEqual(result['periods'][0]['margin'], .2)
        self.assertNotIn('debt', result['periods'][0])
        self.assertEqual(result['periods'][1]['debt'], 10)
        self.assertIsNone(result['periods'][1]['margin'])
        self.assertEqual(result['missing'], ['cash_flow'])

    def test_performance_uses_only_post_decision_common_endpoints(self):
        record = {'saved_at':'2026-01-02T20:00:00+00:00', 'workflow':{'nodes':[{'id':'o','type':'output'}]},
                  'result':{'nodes':{'o':{'outcomes':{'passed':[{'symbol':'A'},{'symbol':'B'}]}}}}}
        dates = pd.to_datetime(['2026-01-02','2026-01-05','2026-01-06'])
        provider = Mock()
        provider.get_historical_prices.return_value = {
            'A':pd.DataFrame({'Close':[1,100,110]},index=dates),
            'B':pd.DataFrame({'Close':[1,200,180]},index=dates),
            'SPY':pd.DataFrame({'Close':[1,100,105]},index=dates)}
        result = forward_performance(provider,record,'o')
        self.assertEqual(result['start'],'2026-01-05')
        self.assertAlmostEqual(result['portfolio_return'],0)
        self.assertAlmostEqual(result['benchmark_return'],5)
        del provider.get_historical_prices.return_value['B']
        self.assertIsNone(forward_performance(provider,record,'o')['portfolio_return'])
        record['saved_at'] = '2026-01-06T12:00:00+00:00'
        self.assertTrue(forward_performance(provider,record,'o')['pending'])

    def test_universe_filters_preserve_exclusion_evidence_and_cache(self):
        provider = Mock()
        provider.get_company_overview.side_effect = [
            {'ExchangeShortName':'NASDAQ','MarketCapitalization':1000,'AverageVolume':500},
            {'ExchangeShortName':'NYSE','MarketCapitalization':1000,'AverageVolume':500},
            {'ExchangeShortName':'NASDAQ'}]
        doc = document()
        doc['universe']['filters'] = {'exchange':'NASDAQ','min_market_cap':100,'min_average_volume':100}
        engine = WorkflowEngine(factory=lambda *args,**kwargs:FakeScreener(),overview_provider=provider)
        result = engine.execute(doc,catalog=CATALOG)
        self.assertEqual(result['nodes']['u']['counts'],{'passed':1,'failed':1,'unavailable':1,'error':0})
        self.assertEqual(result['nodes']['u']['input_count'],3)
        self.assertEqual(result['nodes']['s']['input_count'],1)
        self.assertEqual(result['nodes']['s']['rule'], {'operator':'gte','value':10,'metric':'Score','field':'score'})
        engine.execute(doc,catalog=CATALOG,snapshot_id=result['snapshot_id'])
        self.assertEqual(provider.get_company_overview.call_count,3)
        doc['universe']['filters']['min_market_cap'] = float('nan')
        with self.assertRaises(WorkflowError): validate_workflow(doc,catalog=CATALOG)

    def test_history_api_restores_saved_document_and_validates_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = FakeManager()
            manager.archive = RunArchive(directory)
            manager.archive.save('abc',document(),{'nodes':{}})
            with TestClient(create_app(manager,FakeStockService())) as client:
                self.assertEqual(client.get('/api/history').json()[0]['id'],'abc')
                self.assertEqual(client.get('/api/history/abc').json()['workflow'],document())
                self.assertEqual(client.get('/api/history/not-valid').status_code,404)
                self.assertEqual(client.get('/api/stocks/bad!/financial-history').status_code,422)
                self.assertEqual(client.get('/api/history/abc/performance?output_id=x&benchmark=bad!').status_code,422)
