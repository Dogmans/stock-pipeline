import unittest

from fastapi.testclient import TestClient

from visual_api import create_app
from workflow import WorkflowError


class FakeManager:
    def __init__(self): self.closed = False
    def start(self, document, snapshot_id=None):
        if document.get('version') != 1: raise WorkflowError('Expected version 1.')
        return 'run-1'
    def get(self, run_id): return {'id': run_id, 'status': 'completed', 'result': {'shortlist': []}}
    def cancel(self, run_id): return {'id': run_id, 'status': 'cancelling'}
    def close(self): self.closed = True


class ApiTests(unittest.TestCase):
    def test_catalog_run_validation_origin_and_shutdown(self):
        manager = FakeManager()
        with TestClient(create_app(manager)) as client:
            catalog = client.get('/api/screeners')
            self.assertEqual(catalog.status_code, 200)
            self.assertGreaterEqual(len(catalog.json()), 10)
            started = client.post('/api/runs', json={'workflow': {'version': 1}})
            self.assertEqual(started.status_code, 202)
            self.assertEqual(client.get('/api/runs/run-1').json()['status'], 'completed')
            self.assertEqual(client.post('/api/runs/run-1/cancel').json()['status'], 'cancelling')
            self.assertEqual(client.post('/api/runs', json={'workflow': {}}).status_code, 422)
            self.assertEqual(client.get('/api/screeners', headers={'Origin': 'https://example.com'}).status_code, 403)
        self.assertTrue(manager.closed)
