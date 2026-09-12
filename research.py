"""Evidence-backed research views and durable local workflow snapshots."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from threading import Lock

import pandas as pd


def number(value):
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


class RunArchive:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.lock = Lock()

    def save(self, run_id, workflow, result):
        record = {'id': run_id, 'saved_at': datetime.now(timezone.utc).isoformat(),
                  'workflow': workflow, 'result': result}
        with self.lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            target = self.directory / f'{run_id}.json'
            temporary = target.with_suffix('.tmp')
            temporary.write_text(json.dumps(record, allow_nan=False), encoding='utf-8')
            temporary.replace(target)
        return record

    def list(self):
        records = []
        for path in self.directory.glob('*.json'):
            try:
                record = json.loads(path.read_text(encoding='utf-8'))
                records.append({'id': record['id'], 'saved_at': record['saved_at'],
                                'name': record['workflow'].get('name', 'Untitled workflow')})
            except (OSError, ValueError, KeyError):
                continue
        return sorted(records, key=lambda r: r['saved_at'], reverse=True)

    def get(self, run_id):
        # IDs originate at the server; never interpret user input as a path.
        if not run_id or any(c not in '0123456789abcdef' for c in run_id):
            raise KeyError(run_id)
        try:
            return json.loads((self.directory / f'{run_id}.json').read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise KeyError(run_id) from exc


def financial_history(provider, symbol):
    periods, missing = {}, []
    definitions = [
        ('income', provider.get_income_statement, {'revenue': ['totalRevenue'], 'net_income': ['netIncome']}),
        ('balance', provider.get_balance_sheet, {'debt': ['totalDebt'], 'equity': ['totalShareholderEquity', 'totalEquity']}),
        ('cash_flow', provider.get_cash_flow, {'free_cash_flow': ['freeCashflow', 'freeCashFlow']}),
    ]
    for name, fetch, fields in definitions:
        try:
            frame = fetch(symbol, annual=True)
            if frame is None or frame.empty:
                missing.append(name)
                continue
            for _, row in frame.iterrows():
                date = pd.to_datetime(row.get('fiscalDateEnding'), errors='coerce')
                if pd.isna(date):
                    continue
                period = periods.setdefault(date.date().isoformat(), {})
                for field, keys in fields.items():
                    period[field] = next((number(row.get(k)) for k in keys if number(row.get(k)) is not None), None)
                currency = row.get('reportedCurrency')
                if isinstance(currency, str) and currency:
                    period['currency'] = currency
        except Exception:
            missing.append(name)
    rows = []
    for date, row in sorted(periods.items(), reverse=True)[:5]:
        revenue = row.get('revenue')
        row['margin'] = row['net_income'] / revenue if revenue and row.get('net_income') is not None else None
        rows.append({'date': date, **row})
    return {'symbol': symbol, 'periods': rows, 'missing': missing, 'source': 'FMP annual financial statements'}


def forward_performance(provider, record, output_id, benchmark='SPY'):
    node = next((n for n in record['workflow']['nodes'] if n['id'] == output_id and n['type'] == 'output'), None)
    if node is None:
        raise ValueError('Choose an output node in the saved run.')
    symbols = sorted({r['symbol'] for r in record['result']['nodes'][output_id]['outcomes']['passed']})
    if len(symbols) > 100:
        raise ValueError('Performance tracking supports shortlists of up to 100 stocks.')
    frames = provider.get_historical_prices(list(dict.fromkeys(symbols + [benchmark])), period='5y')
    # Start at the first close strictly AFTER the saved decision date. Avoid claiming
    # returns achievable before the shortlist existed, even when cached scores were reused.
    decision_date = record['saved_at'][:10]
    clean = {}
    for symbol, frame in frames.items():
        if frame is None or frame.empty or 'Close' not in frame:
            continue
        series = pd.to_numeric(frame['Close'], errors='coerce').dropna()
        series.index = pd.to_datetime(series.index).strftime('%Y-%m-%d')
        series = series[~series.index.duplicated()].sort_index()
        clean[symbol] = series[series > 0]
    baseline = clean.get(benchmark)
    dates = [] if baseline is None else [d for d in baseline.index if d > decision_date]
    if len(dates) < 2:
        return {'rows': [], 'pending': True, 'benchmark': benchmark,
                'message': 'At least two benchmark trading closes after the saved run are needed.'}
    start, end = dates[0], dates[-1]
    rows = []
    for symbol in symbols:
        series = clean.get(symbol)
        value = float((series[end] / series[start] - 1) * 100) if series is not None and start in series and end in series else None
        rows.append({'symbol': symbol, 'return_percent': value})
    complete = rows and all(row['return_percent'] is not None for row in rows)
    return {'rows': rows, 'pending': False, 'start': start, 'end': end, 'benchmark': benchmark,
            'benchmark_return': float((baseline[end] / baseline[start] - 1) * 100),
            'portfolio_return': sum(r['return_percent'] for r in rows) / len(rows) if complete else None,
            'message': 'Equal-weight price returns from the first close after the saved run. Excludes dividends and trading costs; corporate actions may affect raw close prices. Missing stocks prevent a portfolio return.'}
