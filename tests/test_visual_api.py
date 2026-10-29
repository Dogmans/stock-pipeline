import unittest
from unittest.mock import patch

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


class FakeStockService:
    def get(self, symbol):
        return {'symbol': symbol, 'overview': {'Price': 123.45},
                'news': [{'title': 'Example', 'url': 'https://example.com'}]}


class ApiTests(unittest.TestCase):
    def test_configured_lan_origin(self):
        with patch.dict('os.environ', {'STOCK_PIPELINE_ALLOWED_ORIGINS':
                                      ' http://stock-server:8765/, http://192.168.1.50:8765 '}):
            with TestClient(create_app(FakeManager(), FakeStockService())) as client:
                for origin in ('http://stock-server:8765', 'http://192.168.1.50:8765'):
                    response = client.post('/api/runs', json={'workflow': {'version': 1}},
                                           headers={'Origin': origin})
                    self.assertEqual(response.status_code, 202)
                    self.assertEqual(response.headers['access-control-allow-origin'], origin)
                preflight = client.options('/api/runs', headers={
                    'Origin': 'http://stock-server:8765',
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'Content-Type'})
                self.assertEqual(preflight.status_code, 200)
                self.assertEqual(client.post('/api/runs', json={'workflow': {'version': 1}},
                    headers={'Origin': 'http://untrusted:8765'}).status_code, 403)

    def test_catalog_run_validation_origin_and_shutdown(self):
        manager = FakeManager()
        with TestClient(create_app(manager, FakeStockService())) as client:
            catalog = client.get('/api/screeners')
            self.assertEqual(catalog.status_code, 200)
            self.assertGreaterEqual(len(catalog.json()), 10)
            started = client.post('/api/runs', json={'workflow': {'version': 1}})
            self.assertEqual(started.status_code, 202)
            self.assertEqual(client.get('/api/runs/run-1').json()['status'], 'completed')
            self.assertEqual(client.post('/api/runs/run-1/cancel').json()['status'], 'cancelling')
            self.assertEqual(client.post('/api/runs', json={'workflow': {}}).status_code, 422)
            self.assertEqual(client.get('/api/screeners', headers={'Origin': 'https://example.com'}).status_code, 403)
            detail = client.get('/api/stocks/aapl')
            self.assertEqual(detail.json()['symbol'], 'AAPL')
            self.assertEqual(detail.json()['overview']['Price'], 123.45)
            self.assertEqual(client.get('/api/stocks/bad!symbol').status_code, 422)
        self.assertTrue(manager.closed)
