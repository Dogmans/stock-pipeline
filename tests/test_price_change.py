import unittest
from unittest.mock import Mock
import pandas as pd
from screeners.price_change import PriceChangeScreener
from workflow import WorkflowEngine, screener_catalog
from tests.test_workflow import document

class PriceChangeTests(unittest.TestCase):
    def test_periods_and_validation(self):
        for period, days in PriceChangeScreener.PERIODS.items():
            self.assertEqual(PriceChangeScreener(period=period).trading_days, days)
        for params in ({'period':'bad'}, {'custom_days':1.5}, {'custom_days':True}, {'custom_days':0}, {'min_change':20,'max_change':10}, {'max_change':float('inf')}, {'min_change':-101}):
            with self.assertRaises(ValueError): PriceChangeScreener(**params)

    def test_endpoints_and_inclusive_bounds(self):
        s=PriceChangeScreener(period='custom',custom_days=2,min_change=-25,max_change=25)
        frame=pd.DataFrame({'Date':['2026-01-05','2026-01-06','2026-01-07','2026-01-08'], 'Close':[100,110,125,999]})
        row=s.evaluate(frame,as_of='2026-01-08')
        self.assertEqual(row['score'],25)
        self.assertEqual(row['start_date'],'2026-01-05')
        self.assertEqual(row['end_price'],125)
        for score, expected in [(-25,True),(25,True),(-25.01,False),(25.01,False)]:
            self.assertEqual(s.meets_threshold(score),expected)
        frame.loc[2,'Close']=75
        self.assertEqual(s.evaluate(frame,as_of='2026-01-08')['score'],-25)

    def test_unavailable_history(self):
        s=PriceChangeScreener(period='custom',custom_days=1)
        for dates, prices in [(['2026-01-01'],[100]), (['2026-01-01','2026-01-01'],[100,110]), (['bad','2026-01-02'],[100,110]), (['2026-01-01','2026-01-20'],[100,110]), (['2026-01-01','2026-01-02'],[0,110]), (['2026-01-01','2026-01-02'],[100,float('nan')])]:
            self.assertIsNone(s.evaluate(pd.DataFrame({'Date':dates,'Close':prices}),as_of='2026-02-01')['score'])

    def test_workflow_records_range_and_evidence(self):
        def factory(name,**params):
            s=PriceChangeScreener(**params)
            s.provider=Mock()
            s.provider.get_company_overview.return_value={}
            s.provider.get_price_change_history.return_value=pd.DataFrame({'Date':['2026-01-05','2026-01-06'],'Close':[100,125]})
            return s
        doc=document();doc['nodes'][1].update(screener='price_change',params={'period':'custom','custom_days':1,'min_change':-10,'max_change':20},criterion={'operator':'default'})
        result=WorkflowEngine(factory=factory).execute(doc,catalog=screener_catalog())['nodes']['s']
        self.assertEqual(result['counts']['failed'],3)
        self.assertEqual(result['rule']['upper_value'],20)
        self.assertEqual(result['rule']['operator'],'between')
        self.assertEqual(result['outcomes']['failed'][0]['end_price'],125)
