import json
import tempfile
import time
import unittest
from pathlib import Path

import pandas as pd

from workflow import WorkflowEngine, WorkflowError, run_workflow_cli, validate_workflow


def document(threshold=10):
    return {'version': 1, 'name': 'Test', 'universe': {'symbols': ['A', 'B', 'C']},
            'nodes': [
                {'id':'u','type':'universe'},
                {'id':'s','type':'screener','screener':'fake','params':{},'criterion':{'operator':'gte','value':threshold}},
                {'id':'pass','type':'output'}, {'id':'fail','type':'output'}],
            'edges': [
                {'id':'a','source':'u','sourceHandle':'passed','target':'s'},
                {'id':'b','source':'s','sourceHandle':'passed','target':'pass'},
                {'id':'c','source':'s','sourceHandle':'failed','target':'fail'}]}


CATALOG = [{'id':'fake','label':'Fake','description':'Offline fake', 'parameters':[]}]


class FakeScreener:
    calls = 0
    def screen_stocks(self, frame):
        type(self).calls += 1
        symbol = frame.iloc[0]['symbol']
        return pd.DataFrame([{'symbol':symbol, 'score':{'A':20,'B':5}[symbol],
                              'meets_threshold':symbol == 'A', 'reason':'fake'}]) if symbol != 'C' else pd.DataFrame()
    def sort_results(self, frame):
        return frame.sort_values('score', ascending=False)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        FakeScreener.calls = 0
        self.engine = WorkflowEngine(factory=lambda name, **kwargs: FakeScreener())

    def test_branches_partition_input_and_explain_unavailable(self):
        result = self.engine.execute(document(), catalog=CATALOG)
        self.assertEqual(result['nodes']['s']['counts'], {'passed':1,'failed':1,'unavailable':1,'error':0})
        self.assertEqual(result['edges']['b']['symbols'], ['A'])
        self.assertEqual(result['edges']['c']['symbols'], ['B'])
        self.assertEqual({row['symbol'] for row in result['nodes']['s']['outcomes']['unavailable']}, {'C'})
        self.assertEqual({row['symbol'] for row in result['shortlist']}, {'A','B'})

    def test_new_threshold_reuses_snapshot_scores(self):
        first = self.engine.execute(document(10), catalog=CATALOG)
        self.assertEqual(FakeScreener.calls, 3)
        second = self.engine.execute(document(25), snapshot_id=first['snapshot_id'], catalog=CATALOG)
        self.assertEqual(FakeScreener.calls, 3)
        self.assertEqual(second['nodes']['s']['counts']['passed'], 0)
        self.assertEqual(second['nodes']['s']['counts']['failed'], 2)

    def test_validation_rejects_merges_cycles_and_bad_parameters(self):
        invalid = document()
        invalid['edges'].append({'id':'merge','source':'u','sourceHandle':'failed','target':'pass'})
        with self.assertRaisesRegex(WorkflowError, 'universe|input'):
            validate_workflow(invalid, CATALOG)
        invalid = document(); invalid['nodes'][1]['params'] = {'unknown':1}
        with self.assertRaisesRegex(WorkflowError, 'Unsupported parameter'):
            validate_workflow(invalid, CATALOG)

    def test_json_records_have_no_nan(self):
        from workflow import json_records
        self.assertEqual(json_records(pd.DataFrame([{'symbol':'A','score':float('nan')}])), [{'symbol':'A','score':None}])

    def test_saved_workflow_runs_through_cli_writer_without_market_calls(self):
        direct = {'version':1, 'name':'Direct selection', 'universe':{'symbols':['AAPL','MSFT']},
                  'nodes':[{'id':'u','type':'universe'},{'id':'o','type':'output'}],
                  'edges':[{'id':'e','source':'u','sourceHandle':'passed','target':'o'}]}
        with tempfile.TemporaryDirectory() as temporary:
            workflow_path = Path(temporary) / 'workflow.json'
            workflow_path.write_text(json.dumps(direct), encoding='utf-8')
            self.assertEqual(run_workflow_cli(workflow_path, temporary), 0)
            result = json.loads((Path(temporary) / 'workflow_results.json').read_text(encoding='utf-8'))
            self.assertEqual([row['symbol'] for row in result['shortlist']], ['AAPL', 'MSFT'])
            self.assertTrue((Path(temporary) / 'workflow_report.md').exists())
