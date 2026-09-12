"""Local HTTP adapter for the shared workflow engine. Run: python visual_api.py."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from copy import deepcopy
import logging
from pathlib import Path
import re
from threading import Event, Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import main as pipeline  # Keep initialization consistent with the existing CLI.
from workflow import WorkflowEngine, WorkflowError, Cancelled, screener_catalog, validate_workflow
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
from research import RunArchive, financial_history, forward_performance


class RunRequest(BaseModel):
    workflow: dict
    snapshot_id: str | None = None


class RunManager:
    def __init__(self, engine=None, archive=None):
        self.engine = engine or WorkflowEngine()
        self.archive = archive or RunArchive(Path(__file__).parent / 'output' / 'workflow_history')
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='workflow')
        self.lock = Lock()
        self.runs = {}

    def start(self, document, snapshot_id=None):
        validate_workflow(document)
        with self.lock:
            if any(r['status'] in ('queued', 'running', 'cancelling') for r in self.runs.values()):
                raise HTTPException(409, 'A workflow is already running. Finish or cancel it first.')
            while len(self.runs) >= 10:
                del self.runs[next(iter(self.runs))]
            run_id = uuid4().hex
            self.runs[run_id] = {'id': run_id, 'status': 'queued',
                                 'progress': {'message': 'Queued', 'overall_percent': 0},
                                 'result': None, 'error': None, 'cancel': Event()}
        self.executor.submit(self._execute, run_id, deepcopy(document), snapshot_id)
        return run_id

    def _execute(self, run_id, document, snapshot_id):
        with self.lock:
            run = self.runs[run_id]
            if run['cancel'].is_set():
                run['status'] = 'cancelled'
                return
            run['status'] = 'running'

        def update(value):
            with self.lock:
                run['progress'] = value
        try:
            result = self.engine.execute(document, snapshot_id=snapshot_id,
                                         cancel=run['cancel'], progress=update)
            if not run['cancel'].is_set():
                try:
                    self.archive.save(run_id, document, result)
                except (OSError, ValueError):
                    logging.getLogger(__name__).exception('Could not save workflow history')
                    result['history_warning'] = 'Run completed, but its history could not be saved.'
            with self.lock:
                run['result'] = result
                run['status'] = 'cancelled' if run['cancel'].is_set() else 'completed'
        except Cancelled:
            with self.lock:
                run['status'] = 'cancelled'
        except Exception as exc:
            logging.getLogger(__name__).exception('Workflow run failed')
            with self.lock:
                run['status'] = 'failed'
                run['error'] = str(exc) if isinstance(exc, WorkflowError) else 'Run failed. See the Python log for details.'

    def get(self, run_id):
        with self.lock:
            if run_id not in self.runs:
                raise HTTPException(404, 'Run not found; it may have expired or the server restarted.')
            return deepcopy({k: v for k, v in self.runs[run_id].items() if k != 'cancel'})

    def cancel(self, run_id):
        with self.lock:
            if run_id not in self.runs:
                raise HTTPException(404, 'Run not found.')
            run = self.runs[run_id]
            if run['status'] in ('queued', 'running', 'cancelling'):
                run['cancel'].set()
                run['status'] = 'cancelling'
        return self.get(run_id)

    def close(self):
        with self.lock:
            for run in self.runs.values():
                run['cancel'].set()
        self.executor.shutdown(wait=True, cancel_futures=True)


class StockDetailService:
    def __init__(self, provider=None):
        self.provider = provider or FinancialModelingPrepProvider()

    def get(self, symbol):
        overview = self.provider.get_company_overview(symbol) or {}
        news = self.provider.get_stock_news(symbol, limit=8)
        articles = []
        for item in news:
            url = item.get('url') or item.get('link')
            articles.append({
                'title': item.get('title') or 'Untitled article',
                'publisher': item.get('publisher') or item.get('site') or '',
                'published_at': item.get('publishedDate') or item.get('published_at') or '',
                'summary': item.get('text') or item.get('summary') or '',
                'url': url if isinstance(url, str) and url.startswith(('https://', 'http://')) else None,
                'image': item.get('image') if isinstance(item.get('image'), str) and item['image'].startswith(('https://', 'http://')) else None,
            })
        return {'symbol': symbol, 'overview': overview, 'news': articles}


def create_app(manager=None, stock_service=None):
    manager = manager or RunManager()
    stock_service = stock_service or StockDetailService()

    @asynccontextmanager
    async def lifespan(app):
        yield
        manager.close()

    app = FastAPI(title='Stock Pipeline Visual Editor', lifespan=lifespan)
    origins = ['http://127.0.0.1:8765', 'http://localhost:8765',
               'http://127.0.0.1:5173', 'http://localhost:5173']
    app.add_middleware(CORSMiddleware, allow_origins=origins,
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

    @app.middleware('http')
    async def local_browser_only(request: Request, call_next):
        if request.headers.get('origin') and request.headers['origin'] not in origins:
            return JSONResponse({'detail': 'This API accepts the local editor origin only.'}, status_code=403)
        return await call_next(request)

    @app.get('/api/screeners')
    def screeners():
        return screener_catalog()

    @app.get('/api/stocks/{symbol}')
    def stock_detail(symbol: str):
        symbol = symbol.upper()
        if not re.fullmatch(r'[A-Z0-9.^=-]{1,30}', symbol):
            raise HTTPException(422, 'Invalid stock symbol.')
        return stock_service.get(symbol)

    @app.get('/api/stocks/{symbol}/financial-history')
    def stock_history(symbol: str):
        symbol = symbol.upper()
        if not re.fullmatch(r'[A-Z0-9.^=-]{1,30}', symbol):
            raise HTTPException(422, 'Invalid stock symbol.')
        return financial_history(stock_service.provider, symbol)

    @app.get('/api/history')
    def history():
        return manager.archive.list()

    @app.get('/api/history/{run_id}')
    def history_detail(run_id: str):
        try:
            return manager.archive.get(run_id)
        except KeyError as exc:
            raise HTTPException(404, 'Saved run not found.') from exc

    @app.get('/api/history/{run_id}/performance')
    def performance(run_id: str, output_id: str, benchmark: str = 'SPY'):
        if not re.fullmatch(r'[A-Z0-9.^=-]{1,30}', benchmark):
            raise HTTPException(422, 'Invalid benchmark symbol.')
        try:
            record = manager.archive.get(run_id)
            return forward_performance(stock_service.provider, record, output_id, benchmark)
        except KeyError as exc:
            raise HTTPException(404, 'Saved run not found.') from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post('/api/workflows/validate')
    def validate(body: RunRequest):
        try:
            validate_workflow(body.workflow)
        except WorkflowError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {'valid': True}

    @app.post('/api/runs', status_code=202)
    def start(body: RunRequest):
        try:
            return {'id': manager.start(body.workflow, body.snapshot_id)}
        except WorkflowError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get('/api/runs/{run_id}')
    def status(run_id: str):
        return manager.get(run_id)

    @app.post('/api/runs/{run_id}/cancel')
    def cancel(run_id: str):
        return manager.cancel(run_id)

    build = Path(__file__).parent / 'web' / 'dist'
    if build.exists():
        app.mount('/', StaticFiles(directory=build, html=True), name='editor')
    else:
        @app.get('/')
        def not_built():
            return {'message': 'Build the editor first: cd web; npm install; npm run build. Then restart this server.'}
    return app


app = create_app()

if __name__ == '__main__':
    import uvicorn
    # Keep a single worker: the FMP session, rate limiter, and snapshots are process-local.
    uvicorn.run(app, host='127.0.0.1', port=8765)
