"""Shared workflow execution for the CLI and local visual editor."""
from collections import OrderedDict, deque
from copy import deepcopy
from datetime import datetime, timezone
import inspect
import json
import logging
import math
import re
from threading import Event
from uuid import uuid4

import pandas as pd
from utils import get_screener, list_screeners
from universe import get_stock_universe

logger = logging.getLogger(__name__)
OUTCOMES = ('passed', 'failed', 'unavailable', 'error')


class WorkflowError(ValueError):
    pass


class Cancelled(Exception):
    pass


def screener_catalog():
    catalog = []
    for name, description in list_screeners().items():
        instance = get_screener(name)
        if instance is None:
            continue
        parameters = []
        for key, parameter in inspect.signature(type(instance).__init__).parameters.items():
            if key == 'self' or parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
                continue
            default = parameter.default
            if default is None:
                default = getattr(instance, key, None)
            parameters.append({'name': key, 'default': default,
                               'type': 'text' if isinstance(default, str) else 'number'})
        catalog.append({'id': name, 'label': instance.get_strategy_name(),
                        'description': description, 'parameters': parameters})
    return catalog


def validate_workflow(document, catalog=None):
    """Validate a rooted graph with source fan-out and disjoint outcome branches."""
    if not isinstance(document, dict) or document.get('version') != 1:
        raise WorkflowError('Expected a workflow with version 1.')
    nodes, edges = document.get('nodes'), document.get('edges')
    if not isinstance(nodes, list) or not 2 <= len(nodes) <= 50 or not isinstance(edges, list):
        raise WorkflowError('A workflow needs 2–50 nodes and an edges list.')
    by_id = {}
    catalog = {item['id']: item for item in (catalog if catalog is not None else screener_catalog())}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not re.fullmatch(r'[\w-]{1,80}', node['id']):
            raise WorkflowError('Each node needs a short, unique identifier.')
        if node['id'] in by_id or node.get('type') not in ('universe', 'screener', 'output'):
            raise WorkflowError('Duplicate identifier or unsupported node type.')
        by_id[node['id']] = node
        if node['type'] == 'screener':
            entry = catalog.get(node.get('screener'))
            if entry is None:
                raise WorkflowError(f"Unknown screener on node {node['id']}.")
            params = node.get('params', {})
            if not isinstance(params, dict):
                raise WorkflowError('Screener parameters must be an object.')
            allowed = {p['name']: p for p in entry['parameters']}
            for key, value in params.items():
                if key not in allowed:
                    raise WorkflowError(f'Unsupported parameter: {key}.')
                if allowed[key]['type'] == 'number':
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                        raise WorkflowError(f'{key} must be a finite number.')
                elif not isinstance(value, str) or len(value) > 40:
                    raise WorkflowError(f'{key} must be short text.')
            criterion = node.get('criterion', {'operator': 'default'})
            if not isinstance(criterion, dict) or criterion.get('operator') not in ('default', 'gte', 'lte'):
                raise WorkflowError('Choose the default rule, score ≥, or score ≤.')
            if criterion['operator'] != 'default':
                value = criterion.get('value')
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise WorkflowError('Score threshold must be a finite number.')
    roots = [n['id'] for n in nodes if n['type'] == 'universe']
    if len(roots) != 1 or not any(n['type'] == 'output' for n in nodes):
        raise WorkflowError('Use one universe and at least one shortlist node.')
    incoming, outgoing, used_ports, edge_ids = {}, {}, set(), set()
    for edge in edges:
        if not isinstance(edge, dict) or not isinstance(edge.get('id'), str) or edge['id'] in edge_ids:
            raise WorkflowError('Each connection needs a unique identifier.')
        edge_ids.add(edge['id'])
        source, target = edge.get('source'), edge.get('target')
        port = edge.get('sourceHandle', 'passed')
        if source not in by_id or target not in by_id or source == target:
            raise WorkflowError('Connections must join two different existing nodes.')
        if by_id[source]['type'] == 'output' or target == roots[0] or port not in OUTCOMES:
            raise WorkflowError('Invalid connection direction or outcome.')
        if by_id[source]['type'] == 'universe' and port != 'passed':
            raise WorkflowError('Connect the universe through its stocks output.')
        if target in incoming or (by_id[source]['type'] != 'universe' and (source, port) in used_ports):
            raise WorkflowError('Use one input per node and one connection per screener outcome; overlapping merges are not supported.')
        incoming[target] = edge
        outgoing.setdefault(source, []).append(edge)
        used_ports.add((source, port))
    order, queue = [], deque(roots)
    while queue:
        current = queue.popleft()
        if current in order:
            raise WorkflowError('Cycles are not supported.')
        order.append(current)
        queue.extend(edge['target'] for edge in outgoing.get(current, []))
    if len(order) != len(nodes):
        raise WorkflowError('Connect every node to the universe; cycles are not supported.')
    universe = document.get('universe', {})
    if not isinstance(universe, dict):
        raise WorkflowError('Universe must be an object.')
    if 'symbols' in universe:
        symbols = universe['symbols']
        if not isinstance(symbols, list) or not 1 <= len(symbols) <= 10000:
            raise WorkflowError('Provide 1–10,000 symbols.')
        if any(not isinstance(s, str) or not re.fullmatch(r'[A-Za-z0-9.^=-]{1,30}', s) for s in symbols):
            raise WorkflowError('Invalid stock symbol.')
    elif not isinstance(universe.get('name'), str) or not re.fullmatch(r'[a-zA-Z0-9_:.-]{1,60}', universe['name']):
        raise WorkflowError('Choose a named universe or provide symbols.')
    return order, by_id, incoming


def json_records(frame):
    # Pandas handles numpy scalars, timestamps, and NaN without invalid JSON floats.
    return json.loads(frame.to_json(orient='records', date_format='iso'))


class WorkflowEngine:
    """Serial executor with bounded, explicit reusable score snapshots."""
    def __init__(self, factory=get_screener, resolver=get_stock_universe):
        self.factory = factory
        self.resolver = resolver
        self.snapshots = OrderedDict()

    def execute(self, document, *, snapshot_id=None, cancel=None, progress=None, catalog=None):
        order, nodes, incoming = validate_workflow(document, catalog)
        cancel = cancel or Event()
        progress = progress or (lambda update: None)
        if snapshot_id:
            if snapshot_id not in self.snapshots:
                raise WorkflowError('This score snapshot has expired. Start a new snapshot.')
            snapshot = self.snapshots[snapshot_id]
            self.snapshots.move_to_end(snapshot_id)
        else:
            snapshot_id = uuid4().hex
            snapshot = {'created_at': datetime.now(timezone.utc).isoformat(), 'scores': {}, 'universes': {}}
            self.snapshots[snapshot_id] = snapshot
            while len(self.snapshots) > 5:
                self.snapshots.popitem(last=False)
        universe_spec = document['universe']
        screener_ids = [node_id for node_id in order if nodes[node_id]['type'] == 'screener']
        screener_position = {node_id: index for index, node_id in enumerate(screener_ids)}
        overall_total = len(screener_ids)
        universe_key = json.dumps(universe_spec, sort_keys=True)
        progress({'message': 'Loading universe', 'completed': 0, 'total': 0,
                  'overall_completed': 0, 'overall_total': overall_total, 'overall_percent': 0})
        if cancel.is_set():
            raise Cancelled()
        if universe_key not in snapshot['universes']:
            if 'symbols' in universe_spec:
                frame = pd.DataFrame({'symbol': list(dict.fromkeys(s.upper() for s in universe_spec['symbols']))})
            else:
                frame = self.resolver(universe_spec['name'])
            if frame is None or frame.empty or 'symbol' not in frame:
                raise WorkflowError('The universe returned no symbols. Check the universe and FMP access.')
            frame = frame.drop_duplicates('symbol').copy()
            if len(frame) > 10000:
                raise WorkflowError('This editor supports up to 10,000 symbols per run.')
            if 'security' not in frame:
                frame['security'] = frame['symbol']
            snapshot['universes'][universe_key] = frame
        universe_frame = snapshot['universes'][universe_key]
        by_symbol = universe_frame.set_index('symbol', drop=False)
        result = {'snapshot_id': snapshot_id, 'snapshot_created_at': snapshot['created_at'],
                  'nodes': {}, 'edges': {}, 'shortlist': [], 'errors': 0}
        for node_id in order:
            if cancel.is_set():
                raise Cancelled()
            node = nodes[node_id]
            if node['type'] == 'universe':
                records = json_records(universe_frame)
            else:
                edge = incoming[node_id]
                records = deepcopy(result['nodes'][edge['source']]['outcomes'][edge.get('sourceHandle', 'passed')])
            outcomes = {key: [] for key in OUTCOMES}
            if node['type'] != 'screener':
                outcomes['passed'] = records
            else:
                screener = self.factory(node['screener'], **node.get('params', {}))
                if screener is None:
                    raise WorkflowError(f"Could not create screener {node['screener']}.")
                score_key = json.dumps([node['screener'], node.get('params', {})], sort_keys=True)
                scored = []
                for index, upstream in enumerate(records):
                    if cancel.is_set():
                        raise Cancelled()
                    symbol = upstream['symbol']
                    stage_progress = index / len(records) if records else 1
                    overall_completed = screener_position[node_id] + stage_progress
                    overall_percent = round(overall_completed / overall_total * 100, 1) if overall_total else 100
                    progress({'node_id': node_id, 'completed': index, 'total': len(records),
                              'overall_completed': overall_completed, 'overall_total': overall_total,
                              'overall_percent': overall_percent,
                              'message': f"{node['screener']} · {symbol}"})
                    key = (score_key, symbol)
                    if key in snapshot['scores']:
                        row = deepcopy(snapshot['scores'][key])
                    else:
                        try:
                            frame = screener.screen_stocks(by_symbol.loc[[symbol]])
                            if frame is None or frame.empty:
                                row = {'symbol': symbol, 'outcome': 'unavailable',
                                       'reason': 'No score returned: data may be missing or the screener could not evaluate this stock.'}
                            else:
                                row = json_records(frame)[0]
                                if row.get('score') is None or not isinstance(row.get('meets_threshold'), bool):
                                    row.update(outcome='unavailable', reason='Score or threshold outcome is unavailable.')
                                else:
                                    row['outcome'] = 'passed' if row['meets_threshold'] else 'failed'
                        except Exception:
                            logger.exception('Workflow screener %s failed for %s', node['screener'], symbol)
                            row = {'symbol': symbol, 'outcome': 'error', 'reason': 'Screening error. See the Python log for details.'}
                        if row['outcome'] != 'error' and len(snapshot['scores']) < 100000:
                            snapshot['scores'][key] = deepcopy(row)
                    criterion = node.get('criterion', {'operator': 'default'})
                    if row['outcome'] in ('passed', 'failed') and criterion['operator'] != 'default':
                        value = criterion['value']
                        passed = row['score'] >= value if criterion['operator'] == 'gte' else row['score'] <= value
                        row.update(outcome='passed' if passed else 'failed', meets_threshold=passed,
                                   reason=f"Score {row['score']:.3g} {'≥' if criterion['operator'] == 'gte' else '≤'} {value:g}: {'pass' if passed else 'fail'}")
                    scored.append(row)
                # Preserve each screener's ranking rather than sorting scores in one direction.
                valid = [row for row in scored if row['outcome'] in ('passed', 'failed')]
                if valid:
                    try:
                        ranked = json_records(screener.sort_results(pd.DataFrame(valid)))
                    except (KeyError, AttributeError):
                        ranked = valid
                    for row in ranked:
                        outcomes[row['outcome']].append(row)
                for row in scored:
                    if row['outcome'] in ('unavailable', 'error'):
                        outcomes[row['outcome']].append(row)
                overall_completed = screener_position[node_id] + 1
                overall_percent = round(overall_completed / overall_total * 100, 1) if overall_total else 100
                progress({'node_id': node_id, 'completed': len(records), 'total': len(records),
                          'overall_completed': overall_completed, 'overall_total': overall_total,
                          'overall_percent': overall_percent, 'message': f"{node['screener']} complete"})
            result['nodes'][node_id] = {'input_count': len(records), 'outcomes': outcomes,
                                        'counts': {key: len(rows) for key, rows in outcomes.items()}}
            result['errors'] += len(outcomes['error']) if node['type'] == 'screener' else 0
            if node['type'] == 'output':
                result['shortlist'].extend(records)
        for edge in document['edges']:
            rows = result['nodes'][edge['source']]['outcomes'][edge.get('sourceHandle', 'passed')]
            result['edges'][edge['id']] = {'count': len(rows), 'symbols': [r['symbol'] for r in rows]}
        result['shortlist'] = list({row['symbol']: row for row in result['shortlist']}.values())
        return result


def run_workflow_cli(path, output_dir, display_limit=20):
    from pathlib import Path
    from reporting import generate_screening_report, generate_summary_report
    document = json.loads(Path(path).read_text(encoding='utf-8'))
    result = WorkflowEngine().execute(document)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'workflow_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    # A shortlist can deliberately be connected to a fail branch: label it as selected.
    selected = pd.DataFrame(result['shortlist'])
    if not selected.empty:
        selected['meets_threshold'] = True
    frames = {'workflow_selection': selected}
    generate_screening_report(frames, destination / 'workflow_report.md', display_limit)
    generate_summary_report(frames, destination / 'workflow_summary.txt',
                            document.get('name', 'Workflow'), result['nodes'][next(n['id'] for n in document['nodes'] if n['type'] == 'universe')]['input_count'],
                            'Workflow selection; see per-node outcomes in workflow_results.json', display_limit)
    return 1 if result['errors'] else 0
