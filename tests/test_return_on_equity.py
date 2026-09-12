import unittest
from unittest.mock import Mock

import pandas as pd

from screeners.return_on_equity import ReturnOnEquityScreener
from workflow import WorkflowEngine, screener_catalog
from utils import get_screener


def statements():
    income = pd.DataFrame([{'fiscalDateEnding':f'{year}-12-31','netIncome':30,'reportedCurrency':'USD'} for year in range(2025,2020,-1)])
    balance = pd.DataFrame([{'fiscalDateEnding':f'{year}-12-31','totalShareholderEquity':200,'totalAssets':1000,'reportedCurrency':'USD'} for year in range(2025,2020,-1)])
    return income,balance


class ROETests(unittest.TestCase):
    def setUp(self):
        self.screener = ReturnOnEquityScreener()
        self.income,self.balance = statements()

    def test_annual_percentage_and_history(self):
        evidence = self.screener.evaluate(self.income,self.balance)
        self.assertEqual(evidence['roe'],15)
        self.assertEqual(evidence['equity_ratio'],20)
        self.assertEqual(evidence['roe_three_year_average'],15)
        self.assertEqual(len(evidence['roe_history']),5)
        self.assertIsNone(evidence['roe_history'][-1]['roe'])
        self.assertTrue(self.screener.meets_threshold(15))
        self.assertFalse(self.screener.meets_threshold(14.99))
        self.assertTrue(ReturnOnEquityScreener(min_roe=0).meets_threshold(0))

    def test_uses_average_equity_and_accepts_real_losses(self):
        self.balance.loc[0,'totalShareholderEquity'] = 300
        self.balance.loc[1,'totalShareholderEquity'] = 100
        self.assertEqual(self.screener.evaluate(self.income,self.balance)['roe'],15)
        self.income.loc[0,'netIncome'] = -30
        evidence = self.screener.evaluate(self.income,self.balance)
        self.assertEqual(evidence['roe'],-15)
        self.assertFalse(self.screener.meets_threshold(evidence['roe']))

    def test_invalid_equity_bases_never_receive_a_score(self):
        for start,end in [(0,200),(-100,200),(200,-100),(1,1)]:
            with self.subTest(start=start,end=end):
                balance = self.balance.copy()
                balance.loc[0,'totalShareholderEquity'] = end
                balance.loc[1,'totalShareholderEquity'] = start
                evidence = self.screener.evaluate(self.income,balance)
                self.assertIsNone(evidence['roe'])
                self.assertIn('equity',evidence['reason'])
        self.balance.loc[:1,'totalShareholderEquity'] = 50
        self.assertIsNotNone(self.screener.evaluate(self.income,self.balance)['roe'])

    def test_missing_latest_data_and_mismatched_currencies_do_not_fall_back(self):
        for field,value in [('totalAssets',None),('reportedCurrency','EUR'),('totalShareholderEquity',float('inf'))]:
            with self.subTest(field=field):
                balance = self.balance.copy()
                balance.loc[0,field] = value
                self.assertIsNone(self.screener.evaluate(self.income,balance)['roe'])
        self.assertIsNone(self.screener.evaluate(self.income,self.balance.iloc[1:])['roe'])
        self.income.loc[0,'fiscalDateEnding'] = '2026-06-30'
        self.assertIsNone(self.screener.evaluate(self.income,self.balance)['roe'])

    def test_workflow_preserves_guard_reasons_and_override_cannot_bypass_them(self):
        self.balance.loc[0,'totalShareholderEquity'] = -200
        provider = Mock()
        provider.get_income_statement.return_value = self.income
        provider.get_balance_sheet.return_value = self.balance
        provider.get_company_overview.return_value = {'Name':'Example','Sector':'Technology','ReturnOnEquityTTM':99}
        self.screener.provider = provider
        doc = {'version':1,'universe':{'symbols':['ABC']},'nodes':[
            {'id':'u','type':'universe'},
            {'id':'roe','type':'screener','screener':'return_on_equity','criterion':{'operator':'gte','value':-100}},
            {'id':'out','type':'output'}], 'edges':[
            {'id':'a','source':'u','target':'roe'}, {'id':'b','source':'roe','sourceHandle':'unavailable','target':'out'}]}
        result = WorkflowEngine(factory=lambda *args,**kwargs:self.screener).execute(doc)
        row = result['nodes']['roe']['outcomes']['unavailable'][0]
        self.assertIn('Nonpositive',row['reason'])
        self.assertIsNone(row['score'])
        self.assertEqual(len(row['roe_history']),5)
        self.assertEqual(result['nodes']['out']['input_count'],1)

    def test_registry_exposes_percentage_rule_and_constructor_parameters(self):
        self.assertIsInstance(get_screener('return_on_equity'),ReturnOnEquityScreener)
        entry = next(c for c in screener_catalog() if c['id']=='return_on_equity')
        self.assertEqual(entry['default_rule']['unit'],'%')
        self.assertEqual(entry['default_rule']['value'],15)
        self.assertEqual({p['name'] for p in entry['parameters']},{'min_roe','min_equity_ratio'})
        with self.assertRaises(ValueError): ReturnOnEquityScreener(min_equity_ratio=-1)
