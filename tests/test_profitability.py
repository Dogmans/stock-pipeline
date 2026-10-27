import json
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import pandas as pd
from fastapi.testclient import TestClient

from profitability import calculate_profitability, profitability
from screeners.profitability import (ProfitabilityScreener, ReturnOnAssetsScreener,
                                    ReturnOnCapitalEmployedScreener, ReturnOnEquityTrendScreener)
from utils.screener_registry import get_screener, default_screeners
from visual_api import StockDetailService, create_app
from tests.test_visual_api import FakeManager
from workflow import WorkflowEngine, screener_catalog, validate_workflow, WorkflowError


def statements(flat=False):
    income, balance = [], []
    for index, date in enumerate(pd.date_range('2022-03-31', periods=16, freq='QE')):
        income.append({'date': date.date().isoformat(), 'period': f'Q{index%4+1}',
                       'reportedCurrency': 'USD', 'netIncome': 8 if flat or index >= 12 else 4,
                       'incomeTaxExpense': 1, 'interestExpense': 1})
        balance.append({'date': date.date().isoformat(), 'reportedCurrency': 'USD',
                        'totalStockholdersEquity': 160, 'totalAssets': 250,
                        'totalCurrentLiabilities': 150})
    return pd.DataFrame(income), pd.DataFrame(balance)


class ProfitabilityTests(unittest.TestCase):
    def test_formulas_use_ttm_and_closing_balances_with_three_year_comparison(self):
        income, balance = statements()
        rows = calculate_profitability(income, balance)
        latest = rows[-1]
        self.assertEqual(latest['date'], '2025-12-31')
        self.assertEqual(latest['comparison_date'], '2022-12-31')
        self.assertEqual(latest['net_income_ttm'], 32)
        self.assertEqual(latest['ebit_ttm'], 40)
        self.assertAlmostEqual(latest['roe'], .2)
        self.assertAlmostEqual(latest['roa'], .128)
        self.assertAlmostEqual(latest['roce'], .4)
        self.assertAlmostEqual(latest['roe_3y_ago'], .1)
        self.assertAlmostEqual(latest['roe_change_3y'], .1)
        self.assertIsNone(rows[2]['roe'])
        json.dumps(rows, allow_nan=False)

    def test_reported_ebit_wins_and_missing_ebit_inputs_do_not_substitute_operating_income(self):
        income, balance = statements()
        income['ebit'] = 12
        self.assertAlmostEqual(calculate_profitability(income,balance)[-1]['roce'], .48)
        income = income.drop(columns=['ebit','interestExpense'])
        income['operatingIncome'] = 999
        row = calculate_profitability(income,balance)[-1]
        self.assertIsNone(row['roce'])
        self.assertEqual(row['roe'], .2)

    def test_missing_quarters_duplicate_periods_and_latest_balance_never_use_older_values(self):
        income, balance = statements()
        for damaged in [income.drop(index=14), income.iloc[:-1].assign(period='FY')]:
            row = calculate_profitability(damaged,balance)[-1]
            self.assertIsNone(row['roe'])
        duplicate = pd.concat([income, income.iloc[[-1]].assign(netIncome=999)])
        self.assertEqual(calculate_profitability(duplicate,balance)[-1]['roe'], .2)
        row = calculate_profitability(income,balance.iloc[:-1])[-1]
        self.assertIsNone(row['roe'])
        self.assertEqual(row['date'], '2025-12-31')

    def test_currency_unknown_mismatch_and_nonpositive_denominators(self):
        income, balance = statements()
        for field, value, metric in [('totalStockholdersEquity',0,'roe'), ('totalStockholdersEquity',-1,'roe'),
                                      ('totalAssets',0,'roa'), ('totalCurrentLiabilities',250,'roce')]:
            damaged = balance.copy();damaged.loc[15,field] = value
            self.assertIsNone(calculate_profitability(income,damaged)[-1][metric])
        for currency in ['CAD',None]:
            damaged = balance.copy();damaged.loc[15,'reportedCurrency'] = currency
            self.assertIsNone(calculate_profitability(income,damaged)[-1]['roe'])
        damaged = income.astype({'netIncome':float});damaged.loc[14,'netIncome'] = float('inf')
        row = calculate_profitability(damaged,balance)[-1]
        self.assertIsNone(row['roe'])
        json.dumps(row,allow_nan=False)

    def test_three_year_comparison_requires_the_same_fiscal_quarter_and_currency(self):
        income,balance = statements()
        for damaged in [income.iloc[4:], income.assign(reportedCurrency=['CAD']*4+['USD']*12)]:
            self.assertIsNone(calculate_profitability(damaged,balance)[-1]['roe_change_3y'])
        income,balance = statements(flat=True)
        self.assertEqual(calculate_profitability(income,balance)[-1]['roe_change_3y'],0)
        trend = ReturnOnEquityTrendScreener()
        self.assertFalse(trend.meets_threshold(0))
        self.assertTrue(trend.meets_threshold(.001))
        self.assertTrue(ReturnOnEquityTrendScreener(min_percent=-1).meets_threshold(0))

    def test_registration_units_boundaries_and_opt_in(self):
        for name, cls, threshold in [('ttm_return_on_equity',ProfitabilityScreener,15),
                                     ('return_on_assets',ReturnOnAssetsScreener,10),
                                     ('return_on_capital_employed',ReturnOnCapitalEmployedScreener,30)]:
            self.assertIsInstance(get_screener(name),cls)
            self.assertTrue(cls().meets_threshold(threshold))
            self.assertFalse(cls().meets_threshold(threshold-.01))
            self.assertNotIn(name,default_screeners())
        self.assertNotIn('roe_improvement',default_screeners())
        for value in [float('inf'),float('nan')]:
            with self.assertRaises(ValueError): ProfitabilityScreener(value)

    def test_api_and_screeners_share_the_same_values(self):
        income,balance = statements()
        provider = Mock()
        provider.get_research_statements.side_effect = lambda symbol, kind, annual: income if kind=='income' else balance
        provider.get_company_overview.return_value = {'Name':'Example'}
        provider.get_stock_news.return_value = []
        service = StockDetailService(provider)
        with TestClient(create_app(FakeManager(),service)) as client:
            api_data = client.get('/api/stocks/abc').json()['profitability']
        for cls in [ProfitabilityScreener,ReturnOnAssetsScreener,ReturnOnCapitalEmployedScreener,ReturnOnEquityTrendScreener]:
            screen = cls();screen.provider = provider
            row = screen.screen_stocks(pd.DataFrame({'symbol':['ABC']})).iloc[0]
            self.assertEqual(row['score'],api_data['latest'][screen.metric]*100)
            self.assertTrue(row['meets_threshold'])
        provider.get_research_statements.side_effect = RuntimeError('offline')
        with self.assertLogs('profitability',level='ERROR'):
            self.assertIsNone(profitability(provider,'ABC')['latest'])
        with self.assertRaises(RuntimeError): profitability(provider,'ABC',strict=True)

    def test_preset_partitions_pass_fail_unavailable_error_and_sector_exclusions(self):
        doc = json.loads((Path(__file__).resolve().parents[1]/'workflows/profitability_traits.json').read_text())
        doc['universe']['symbols'] = ['PASS','FLAT','LOWROA','LOWROCE','MISSING','ERROR','BANK','UNKNOWN']
        doc['universe'].pop('name')
        provider = Mock()
        provider.get_company_overview.side_effect = lambda s: {'Sector': 'Financial Services' if s=='BANK' else None if s=='UNKNOWN' else 'Technology'}
        def fetch(symbol,kind,annual):
            if symbol=='ERROR': raise RuntimeError('offline')
            income,balance = statements(flat=symbol=='FLAT')
            if symbol=='MISSING': income=income.iloc[-3:]
            if symbol=='LOWROA': balance['totalAssets']=400
            if symbol=='LOWROCE': balance['totalCurrentLiabilities']=0
            return income if kind=='income' else balance
        provider.get_research_statements.side_effect = fetch
        def factory(name,**kwargs):
            screen = get_screener(name,**kwargs);screen.provider=provider
            return screen
        with self.assertLogs('workflow',level='ERROR'):
            result = WorkflowEngine(factory=factory,overview_provider=provider).execute(doc)
        self.assertEqual([r['symbol'] for r in result['nodes']['shortlist']['outcomes']['passed']],['PASS'])
        for node,outcome,symbol in [('universe','failed','BANK'),('universe','unavailable','UNKNOWN'),
                                     ('roe','unavailable','MISSING'),('roe','error','ERROR'),
                                     ('roa','failed','LOWROA'),('trend','failed','FLAT'),('roce','failed','LOWROCE')]:
            self.assertIn(symbol,[r['symbol'] for r in result['nodes'][node]['outcomes'][outcome]])
        self.assertEqual(result['nodes']['trend']['rule']['operator'],'gt')
        json.dumps(result,allow_nan=False)
        invalid=deepcopy(doc);invalid['universe']['filters']['excluded_sectors'] = ['Energy']
        with self.assertRaises(WorkflowError):validate_workflow(invalid)
