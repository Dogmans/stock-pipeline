import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { createRoot } from 'react-dom/client';
import { ReactFlow, ReactFlowProvider, Background, Controls, MiniMap, Handle, Position,
  useNodesState, useEdgesState, useReactFlow, addEdge } from '@xyflow/react';
import { Play, Square, Download, Upload, Plus, Search, SlidersHorizontal, GitBranch,
  ArrowUpRight, Layers, Check, CircleHelp, RefreshCw, Trash2, ListFilter, ChevronRight,
  X, ExternalLink, Newspaper } from 'lucide-react';
import '@xyflow/react/dist/style.css';
import './style.css';
import example from '../../workflows/value_quality.json';
import { colors, outcomeLabels, fromDocument, toDocument, logicKey, canConnect, volumeWidth, csv, defaultRuleText } from './workflow.js';
import ResearchPanel, {ThresholdDistribution, FinancialHistory} from './ResearchPanel.jsx';
import {peerContext} from './insights.js';

function ScreeningPath({ context }) {
  const passed = context.steps.filter(step => step.outcome === 'passed').length;
  return <section className="screening-path" aria-label="Why this stock?">
    <span className="eyebrow">WORKFLOW EVIDENCE</span><h2>Why this stock?</h2>
    <p>{context.symbol} · {context.label}</p>
    <p>{context.steps.length ? `${passed} of ${context.steps.length} screens passed on this path.` : 'This path contains no screening steps.'}</p>
    {context.createdAt && <p className="muted">Run snapshot started {new Date(context.createdAt).toLocaleString()}. These are screening results; the stock snapshot below may be newer.</p>}
    <ol>{context.steps.map(step => <li key={step.id}>
      <div className="screening-step-heading"><strong>{step.label}</strong><span style={{color: colors[step.outcome]}}>{outcomeLabels[step.outcome]}</span></div>
      <p>Pass condition: {step.rule}</p>
      <p>Recorded score: {typeof step.row.score === 'number' ? step.row.score.toLocaleString(undefined, {maximumFractionDigits: 4}) : 'Unavailable'}</p>
      <p>{step.row.reason || 'No decision explanation was recorded.'}</p>
      {step.note && <p className="default-rule-note">{step.note}</p>}
      <p>{step.percentile == null ? 'Sector comparison unavailable: fewer than two comparable stocks.' : `${step.percentile.toFixed(0)} percentile among ${step.peerCount} evaluated ${step.sector} stocks. Higher is better.`}</p>
      <ScoreBreakdown row={step.row}/>
    </li>)}</ol>
    {context.steps.some(step => step.outcome !== 'passed') && <p className="screening-caution">This route includes a failed screen or unavailable evaluation. Inclusion here does not mean every screen passed.</p>}
  </section>;
}

function ScoreBreakdown({ row }) {
  if (row.price_basis) return <details className="score-breakdown"><summary>Price change calculation</summary>
    <p>{row.trading_days} trading sessions / {row.currency || 'Currency unavailable'}</p>
    <p>{row.start_date || 'Unavailable'}: {row.start_price ?? 'Unavailable'} to {row.end_date || 'Unavailable'}: {row.end_price ?? 'Unavailable'}</p>
    <p>{row.price_basis}. Change = (end close / start close - 1) * 100.</p>
  </details>;
  if (Array.isArray(row.roe_history)) return <details className="score-breakdown"><summary>ROE history and equity checks</summary>
    <p>Latest annual period: {row.period || 'Unavailable'} · Statement currency: {row.currency || 'Unavailable'}</p>
    <p>Three-year average ROE: {typeof row.roe_three_year_average === 'number' ? `${row.roe_three_year_average.toFixed(2)}%` : 'Unavailable (three consecutive valid years required)'}</p>
    <p>ROE = annual net income / average opening and closing shareholders’ equity. This is not TTM ROE.</p>
    <div className="table-scroll"><table><thead><tr><th>Year end</th><th>ROE</th><th>Equity / assets</th><th>Decision / data checks</th></tr></thead><tbody>{row.roe_history.map(year => <tr key={year.period}><td>{year.period}</td><td>{typeof year.roe === 'number' ? `${year.roe.toFixed(2)}%` : 'Unavailable'}</td><td>{typeof year.equity_ratio === 'number' ? `${year.equity_ratio.toFixed(2)}%` : 'Unavailable'}</td><td>{year.reason}</td></tr>)}</tbody></table></div>
    <p>ROE also contributes to Quality and Enhanced Quality; weighting them together increases its influence.</p>
  </details>;
  if (typeof row.insider_activity_score !== 'number') return null;
  return <details className="score-breakdown"><summary>Score breakdown</summary>
    <dl>{[['Insider activity', 'insider_activity_score', 40], ['Activity acceleration', 'acceleration_score', 25], ['Price consolidation', 'consolidation_score', 20], ['Volume expansion', 'volume_score', 15]].map(([label, key, max]) =>
      <div key={key}><dt>{label}</dt><dd>{row[key]?.toFixed(2) ?? '?'} / {max}</dd></div>)}</dl>
    <p>30-session annualized volatility: {row.annualized_volatility == null ? '?' : `${(row.annualized_volatility * 100).toFixed(2)}%`} (consolidation below 15%).</p>
    <p>10-session volume / period average: {row.relative_volume == null ? '?' : `${row.relative_volume.toFixed(2)}?`} (points above 1.2?).</p>
    <p>Technical data: {row.technical_status}. Missing components contribute 0 points.</p>
  </details>;
}

const initial = fromDocument(example);
async function api(path, options) {
  const response = await fetch('/api' + path, { ...options, headers: { 'Content-Type': 'application/json', ...options?.headers } });
  const body = await response.json();
  if (!response.ok) throw Error(typeof body.detail === 'string' ? body.detail : 'Request could not be processed. Check the workflow settings.');
  return body;
}
function download(name, content, type) {
  const link = document.createElement('a'), url = URL.createObjectURL(new Blob([content], { type }));
  link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const metricDefinitions = [
  ['Price', 'Price', 'currency'], ['Change', 'Change', 'number'], ['ChangesPercentage', 'Today', 'percentValue'],
  ['MarketCapitalization', 'Market cap', 'compact'], ['PERatio', 'Trailing P/E', 'number'], ['EPS', 'EPS', 'currency'],
  ['PriceToBookRatio', 'Price / book', 'number'], ['PriceToSalesRatio', 'Price / sales', 'number'],
  ['ReturnOnEquityTTM', 'Return on equity', 'percent'], ['ProfitMargin', 'Profit margin', 'percent'],
  ['52WeekLow', '52-week low', 'currency'], ['52WeekHigh', '52-week high', 'currency'],
];
function formatMetric(value, kind) {
  if (value == null || value === '') return '—';
  const number = Number(value); if (!Number.isFinite(number)) return String(value);
  if (kind === 'currency') return new Intl.NumberFormat(undefined, {style:'currency', currency:'USD', maximumFractionDigits:2}).format(number);
  if (kind === 'compact') return new Intl.NumberFormat(undefined, {notation:'compact', maximumFractionDigits:2}).format(number);
  if (kind === 'percent') return `${(number * 100).toFixed(1)}%`;
  if (kind === 'percentValue') return `${number >= 0 ? '+' : ''}${number.toFixed(2)}%`;
  return number.toLocaleString(undefined, {maximumFractionDigits:2});
}

function WorkflowNode({ id, data, selected }) {
  const result = data.result, isScreener = data.kind === 'screener';
  const ports = isScreener ? Object.keys(colors) : ['passed'];
  const Icon = data.kind === 'universe' ? Layers : data.kind === 'output' ? ListFilter : SlidersHorizontal;
  return <article className={`workflow-node ${data.kind} ${selected ? 'selected' : ''} ${data.active ? 'active' : ''}`}>
    {data.kind !== 'universe' && <Handle type="target" position={Position.Left} />}
    <div className="node-heading"><span className="node-icon"><Icon size={16}/></span><span className="eyebrow">{data.kind === 'screener' ? 'Screen' : data.kind === 'output' ? 'Collection' : 'Source'}</span><span className="node-status">{data.active ? 'Running' : result ? <Check size={14}/> : '•••'}</span></div>
    <h3>{data.label || data.catalog?.label || data.screener}</h3>
    {data.kind === 'universe' && <p>{data.universeLabel}</p>}
    {isScreener && <div className="node-rule nodrag">
      <select aria-label={`${data.catalog?.label || data.screener} rule`} value={data.criterion.operator} disabled={data.busy}
        onChange={event => data.onUpdate(id, { criterion: { operator: event.target.value, value: data.criterion.value ?? 10 } })}>
        <option value="default">{defaultRuleText(data.catalog, data.params)}</option><option value="gte">Score ≥</option><option value="lte">Score ≤</option>
      </select>
      {data.criterion.operator !== 'default' && <input type="number" step="any" aria-label="Score threshold" value={data.criterion.value ?? ''} disabled={data.busy}
        onChange={event => data.onUpdate(id, { criterion: { ...data.criterion, value: event.target.value === '' ? null : Number(event.target.value) } })}/>}
    </div>}
    {data.kind === 'output' && <p>Inspect, compare & export</p>}
    <div className="node-count"><strong>{result ? result.input_count.toLocaleString() : '—'}</strong><span>{data.kind === 'output' ? 'stocks selected' : 'stocks incoming'}</span></div>
    {data.kind !== 'output' && <div className="node-ports">
      {ports.map((port, i) => <div className="port-row" key={port}>
        <button className="nodrag" onClick={() => data.onInspect(id, port)}><i style={{ background: colors[port] }}/>{isScreener ? outcomeLabels[port] : 'Stocks'}<b>{result ? result.counts[port] : '—'}</b></button>
        <Handle type="source" position={Position.Right} id={port} style={{ top: 'auto', bottom: (ports.length - i - 1) * 27 + 22, background: colors[port] }}/>
      </div>)}
    </div>}
  </article>;
}
const nodeTypes = { workflow: WorkflowNode };

function Studio() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);
  const [name, setName] = useState(example.name), [universe, setUniverse] = useState(example.universe);
  const [catalog, setCatalog] = useState([]), [query, setQuery] = useState(''), [error, setError] = useState('');
  const [run, setRun] = useState(null), [runKey, setRunKey] = useState(''), [starting, setStarting] = useState(false);
  const [selection, setSelection] = useState({ id: 'shortlist', port: 'passed' });
  const [stockDetail, setStockDetail] = useState(null), [stockLoading, setStockLoading] = useState(''), [stockError, setStockError] = useState('');
  const [stockContext, setStockContext] = useState(null);
  const stockRequest = useRef(0);
  const [history, setHistory] = useState([]), [record, setRecord] = useState(null);
  const [expandedResults, setExpandedResults] = useState(false);
  const [weighted, setWeighted] = useState(true), [reuse, setReuse] = useState(true), [searchStocks, setSearchStocks] = useState('');
  const file = useRef(), savedSnapshot = useRef(null), { screenToFlowPosition, fitView } = useReactFlow();
  const busy = starting || ['queued', 'running', 'cancelling'].includes(run?.status);
  const document = useMemo(() => toDocument(name, universe, nodes, edges), [name, universe, nodes, edges]);
  const currentKey = logicKey(document), stale = !!run?.result && runKey !== currentKey;
  const result = !stale ? run?.result : null;
  const overallPercent = Math.max(0, Math.min(100, Math.round(run?.progress?.overall_percent || 0)));
  const byScreener = useMemo(() => Object.fromEntries(catalog.map(c => [c.id, c])), [catalog]);
  const universeLabel = universe.symbols ? `${universe.symbols.length} custom symbols` : universe.name;
  useEffect(() => { api('/screeners').then(setCatalog).catch(() => setError('The Python API is not available. Start visual_api.py and reload this page.')); }, []);
  useEffect(() => {api('/history').then(setHistory).catch(() => {});},[]);
  useEffect(() => {
    if (!run?.id || !['queued', 'running', 'cancelling'].includes(run.status)) return;
    let stopped = false;
    const timer = setTimeout(async () => {
      try {
        const value = await api(`/runs/${run.id}`);
        if (stopped) return;
        setRun(value);
        if (value.result) savedSnapshot.current = value.result.snapshot_id;
        if (value.status === 'completed' && value.result) {
          if (value.result.history_warning) setError(value.result.history_warning);
          else {
            api(`/history/${value.id}`).then(setRecord).catch(err => setError(err.message));
            api('/history').then(setHistory).catch(err => setError(err.message));
          }
        }
        if (value.error) setError(value.error);
      } catch (err) { if (!stopped) { setError(err.message); setRun(r => ({ ...r, status: 'failed' })); } }
    }, 500);
    return () => { stopped = true; clearTimeout(timer); };
  }, [run]);
  const update = useCallback((id, patch) => setNodes(current => current.map(n => n.id === id ? { ...n, data: { ...n.data, ...patch } } : n)), [setNodes]);
  const inspect = useCallback((id, port = 'passed') => { setSelection({ id, port }); setSearchStocks(''); }, []);
  const visibleNodes = nodes.map(n => ({ ...n, data: { ...n.data, result: result?.nodes[n.id],
    catalog: byScreener[n.data.screener], universeLabel, busy,
    active: busy && run?.progress?.node_id === n.id, onUpdate: update, onInspect: inspect } }));
  const root = nodes.find(n => n.data.kind === 'universe');
  const total = result?.nodes[root?.id]?.input_count || 1;
  const visibleEdges = edges.map(e => {
    const port = e.sourceHandle || 'passed', count = result?.edges[e.id]?.count;
    return { ...e, style: { stroke: colors[port], strokeWidth: count == null ? 2 : weighted ? volumeWidth(count, total) : 2,
      opacity: 0.65, ...(count === 0 ? { strokeDasharray: '4 5' } : {}) },
      label: count == null ? outcomeLabels[port] : `${count.toLocaleString()} · ${outcomeLabels[port]}`,
      labelStyle: { fontSize: 11, fontWeight: 600, fill: '#40594d' }, labelBgStyle: { fill: '#fcfcf8', fillOpacity: .95 },
      labelBgPadding: [7, 5], labelBgBorderRadius: 6 };
  });
  const selected = nodes.find(n => n.id === selection.id);
  const selectedResult = result?.nodes[selection.id];
  const allRows = selectedResult?.outcomes[selection.port] || [];
  const rows = allRows.filter(row => `${row.symbol} ${row.company_name || ''}`.toLowerCase().includes(searchStocks.toLowerCase()));

  function add(kind, screener, position) {
    if (busy) return;
    const id = `${kind}-${crypto.randomUUID().slice(0, 8)}`;
    setNodes(current => [...current, { id, type: 'workflow', position: position || screenToFlowPosition({ x: window.innerWidth / 2, y: 300 }),
      data: { kind, screener, ...(kind === 'output' ? { label: 'Shortlist' } : {}), params: {}, criterion: { operator: 'default' } } }]);
    inspect(id);
  }
  async function start() {
    setError(''); setStarting(true);
    try {
      const value = await api('/runs', { method: 'POST', body: JSON.stringify({ workflow: document, snapshot_id: reuse ? savedSnapshot.current : null }) });
      setRecord(null);
      setRunKey(currentKey); setRun({ ...value, status: 'queued', progress: { message: 'Starting workflow', overall_percent: 0 } });
    } catch (err) { setError(err.message); } finally { setStarting(false); }
  }
  async function load(event) {
    try {
      const doc = JSON.parse(await event.target.files[0].text());
      await api('/workflows/validate', { method: 'POST', body: JSON.stringify({ workflow: doc }) });
      const graph = fromDocument(doc); setNodes(graph.nodes); setEdges(graph.edges);
      setName(doc.name || 'Untitled workflow'); setUniverse(doc.universe); setRun(null); setError('');
      setRecord(null);
      savedSnapshot.current = null; setTimeout(() => fitView({ padding: .2 }), 100);
    } catch (err) { setError(err.message); }
    event.target.value = '';
  }
  async function restoreRun(id) {
    if (busy) {setError('Finish or stop the active run before opening a saved run.');return;}
    try {
      const saved = await api(`/history/${id}`), graph = fromDocument(saved.workflow);
      setNodes(graph.nodes);setEdges(graph.edges);setName(saved.workflow.name || 'Untitled workflow');setUniverse(saved.workflow.universe);
      setRun({id:saved.id,status:'completed',result:saved.result});setRunKey(logicKey(toDocument(saved.workflow.name,saved.workflow.universe,graph.nodes,graph.edges)));setRecord(saved);
      savedSnapshot.current = null;
      const output = graph.nodes.find(n => n.data.kind === 'output');
      inspect(output?.id || graph.nodes[0].id);
      setTimeout(() => fitView({padding:.2}),100);
    } catch(err) {setError(err.message);}
  }
  async function openStock(symbol, sourceSelection = selection) {
    const request = ++stockRequest.current;
    const sourceNode = nodes.find(n => n.id === sourceSelection.id);
    setStockContext({symbol, label: sourceNode?.data.label || byScreener[sourceNode?.data.screener]?.label || 'Selected path',
      createdAt: result?.snapshot_created_at,
      steps: peerContext(symbol, sourceSelection, nodes, edges, result, byScreener)});
    setStockDetail(null); setStockError(''); setStockLoading(symbol);
    try { const detail = await api(`/stocks/${encodeURIComponent(symbol)}`); if (request === stockRequest.current) setStockDetail(detail); }
    catch (err) { if (request === stockRequest.current) setStockError(err.message); }
    finally { if (request === stockRequest.current) setStockLoading(''); }
  }
  function closeStock() {
    stockRequest.current++;
    setStockContext(null); setStockDetail(null); setStockError(''); setStockLoading('');
  }
  return <div className="studio">
    <header className="header"><a className="brand" href="/"><span className="brand-mark"><GitBranch size={22}/></span><span>stock<span className="brand-light">pipeline</span></span></a>
      <span className="header-divider"/><span className="workspace-label">Workflow Studio</span><span className="local-badge"><i/> Local workspace</span>
      <a className="help-link" href="/docs" target="_blank" rel="noreferrer"><CircleHelp size={16}/> API reference</a>
    </header>
    <div className="workflow-bar"><div><div className="breadcrumb">WORKFLOWS <ChevronRight size={12}/> PERSONAL</div><input aria-label="Workflow name" className="workflow-name" value={name} onChange={e => setName(e.target.value)}/></div>
      <div className="bar-actions"><button disabled={busy} onClick={() => file.current.click()}><Upload size={15}/> Open</button><input ref={file} type="file" accept=".json" hidden onChange={load}/>
        <button onClick={() => download('workflow.json', JSON.stringify(document, null, 2), 'application/json')}><Download size={15}/> Save workflow</button>
        {busy ? <button className="run-button" disabled={starting || run?.status === 'cancelling'} onClick={() => api(`/runs/${run.id}/cancel`, { method: 'POST' }).then(setRun).catch(err => setError(err.message))}><Square size={14}/>{run?.status === 'cancelling' ? 'Stopping…' : 'Stop run'}</button> : <button className="run-button" disabled={!catalog.length} onClick={start}><Play size={15} fill="currentColor"/> Run workflow</button>}
      </div></div>
    {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')}>Dismiss</button></div>}
    <div className="workspace">
      <aside className="library"><div className="section-heading"><span>Screener library</span><span className="count-pill">{catalog.length}</span></div><p className="muted">Drag a screen onto your canvas.</p>
        <label className="search"><Search size={15}/><input placeholder="Find a screener…" aria-label="Find a screener" value={query} onChange={e => setQuery(e.target.value)}/></label>
        <div className="library-list">{catalog.filter(c => (c.label + c.description).toLowerCase().includes(query.toLowerCase())).map(c => <button key={c.id} className="library-item" draggable={!busy} disabled={busy}
          onDragStart={event => event.dataTransfer.setData('application/screener', c.id)} onClick={() => add('screener', c.id)} title={c.description}>
          <span className="library-icon"><SlidersHorizontal size={15}/></span><span>{c.label.replace(' Screener', '')}</span><Plus size={13}/>
        </button>)}</div>
        <button className="add-shortlist" disabled={busy} onClick={() => add('output')}><ListFilter size={16}/> Add shortlist <Plus size={14}/></button>
        <div className="library-note"><GitBranch size={19}/><strong>Follow the decisions.</strong><p>Connect an outcome to the next screen. Select any line to see the stocks flowing through it.</p></div>
      </aside>
      <main className="main-pane"><div className="canvas-bar"><div className="canvas-run-status"><span><i className="status-dot"/>{busy ? run?.progress?.message : stale ? 'Workflow changed · run to update' : run?.status === 'completed' ? 'Run complete' : run?.status === 'cancelled' ? 'Run cancelled' : 'Build your screening path'}</span>
        {busy && <div className="overall-progress" role="progressbar" aria-label="Overall workflow progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow={overallPercent}><span><i style={{width: `${overallPercent}%`}}/></span><b>{overallPercent}% overall</b></div>}</div>
        <label><input type="checkbox" checked={weighted} onChange={e => setWeighted(e.target.checked)}/> Volume widths</label>
      </div>
      <div className="canvas" onDragOver={e => {e.preventDefault(); e.dataTransfer.dropEffect = 'copy';}} onDrop={event => {event.preventDefault(); const id = event.dataTransfer.getData('application/screener'); if (byScreener[id]) add('screener', id, screenToFlowPosition({ x: event.clientX, y: event.clientY }));}}>
        <ReactFlow nodes={visibleNodes} edges={visibleEdges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={busy ? undefined : onEdgesChange}
          onConnect={connection => !busy && setEdges(current => addEdge(connection, current))} isValidConnection={c => canConnect(c, nodes, edges)}
          nodesConnectable={!busy} deleteKeyCode={busy ? null : ['Backspace', 'Delete']} fitView fitViewOptions={{ padding: .15 }} minZoom={.25} maxZoom={1.6}
          onNodeClick={(_, n) => inspect(n.id)} onEdgeClick={(_, e) => inspect(e.source, e.sourceHandle || 'passed')}>
          <Background color="#d6ded5" gap={22} size={1}/><Controls showInteractive={false}/><MiniMap nodeColor={n => n.data.kind === 'universe' ? '#b9cebe' : n.data.kind === 'output' ? '#258564' : '#e0e7df'} pannable zoomable/>
        </ReactFlow>
        <div className="legend">{Object.entries(colors).map(([key, color]) => <span key={key}><i style={{ background: color }}/>{outcomeLabels[key]}</span>)}</div>
      </div>
      <section className={`results ${expandedResults ? 'expanded-results' : ''}`}><div className="results-heading"><div><span className="eyebrow">STOCK INSPECTOR</span><h2>{selected?.data.label || byScreener[selected?.data.screener]?.label || 'Select a node'} <span className="count-pill">{allRows.length}</span></h2></div>
        <button className="expand-results" aria-expanded={expandedResults} onClick={() => setExpandedResults(!expandedResults)}>{expandedResults ? 'Back to canvas' : 'Expand results'}</button>
        <div className="results-actions"><label className="search"><Search size={14}/><input aria-label="Filter stocks" placeholder="Filter stocks…" value={searchStocks} onChange={e => setSearchStocks(e.target.value)}/></label><button disabled={!rows.length} onClick={() => download('stocks.csv', csv(rows), 'text/csv')}><Download size={14}/> CSV</button></div></div>
        <ResearchPanel key={`${selection.id}-${selection.port}-${run?.id || 'draft'}-${stale}`} rows={allRows} selection={selection} nodes={nodes} edges={edges} result={result} catalog={byScreener} api={api} openStock={openStock} record={stale ? null : record} history={history} onRestore={restoreRun}>
        <div className="outcome-tabs">{Object.keys(colors).map(port => <button key={port} className={selection.port === port ? 'chosen' : ''} onClick={() => inspect(selection.id, port)}>{outcomeLabels[port]} <span>{selectedResult?.counts[port] ?? '—'}</span></button>)}</div>
        {rows.length ? <div className="table-scroll"><table><thead><tr><th>Symbol</th><th>Company</th><th>Score</th><th>Decision / reason</th></tr></thead><tbody>{rows.slice(0, 500).map(row => <tr key={row.symbol}><td><button className="stock-link" onClick={() => openStock(row.symbol)} disabled={stockLoading === row.symbol}>{stockLoading === row.symbol ? 'Loading…' : row.symbol}</button></td><td>{row.company_name || row.security || '—'}</td><td>{typeof row.score === 'number' ? row.score.toFixed(2) : '—'}</td><td>{row.reason || 'Included in universe'}<ScoreBreakdown row={row}/></td></tr>)}</tbody></table>{rows.length > 500 && <p>Showing 500 rows. CSV includes all {rows.length} matching stocks.</p>}</div> : <div className="empty-state"><ListFilter size={23}/><div><strong>{stale ? 'Results need an update' : result ? 'No stocks in this outcome' : 'Your results will appear here'}</strong><p>{stale ? 'Run this workflow to see results for its current settings.' : result ? 'Select another outcome or connection to explore the run.' : 'Run the workflow, then click a node or connection to explore its stocks.'}</p></div></div>}
        </ResearchPanel>
      </section></main>
      <aside className="inspector"><div className="section-heading">Workflow settings <SlidersHorizontal size={16}/></div><label className="field">Universe<select disabled={busy} value={universe.symbols ? 'custom' : universe.name} onChange={e => setUniverse(e.target.value === 'custom' ? {symbols: example.universe.symbols, filters: universe.filters} : {name: e.target.value, filters: universe.filters})}><option value="custom">Custom symbols</option><option value="sp500">S&P 500</option><option value="russell2000">Russell 2000</option><option value="nasdaq100">Nasdaq 100</option></select></label>
        {universe.symbols && <label className="field">Symbols<textarea disabled={busy} aria-label="Symbols" value={universe.symbols.join(', ')} onChange={e => setUniverse({...universe, symbols: e.target.value.toUpperCase().split(/[\s,]+/).filter(Boolean)})}/><small>Comma-separated stock symbols</small></label>}
        <details className="universe-filters"><summary>Universe eligibility filters</summary>
          <p className="muted">Applied before screening. Missing eligibility data appears under the source node’s Unavailable outcome. Filters require company data for each candidate.</p>
          <label className="field">Exchange<input disabled={busy} placeholder="Any, e.g. NASDAQ" value={universe.filters?.exchange || ''} onChange={e => setUniverse({...universe,filters:{...universe.filters,exchange:e.target.value.toUpperCase()}})}/></label>
          {[['min_market_cap','Minimum market cap (quote currency)'],['min_average_volume','Minimum average daily volume (shares)']].map(([key,label]) => <label className="field" key={key}>{label}<input disabled={busy} type="number" min="0" step="any" value={universe.filters?.[key] ?? ''} placeholder="No minimum" onChange={e => setUniverse({...universe,filters:{...universe.filters,[key]:e.target.value === '' ? 0 : Number(e.target.value)}})}/></label>)}
          <p className="muted">Use the Universe selector above to explore an index instead of the eight example symbols.</p>
        </details>
        <div className="setting-divider"/><label className="reuse-option"><input type="checkbox" checked={reuse} disabled={busy} onChange={e => setReuse(e.target.checked)}/><span>Reuse calculated scores<small>Fast comparisons with your last run.</small></span></label>
        <p className="snapshot-note">{result?.snapshot_created_at ? `Snapshot started ${new Date(result.snapshot_created_at).toLocaleString()}.` : 'New scores use the existing FMP data cache.'} Changing a threshold reuses scores. Changing screener parameters may need more data.</p>
        {selected && <><div className="setting-divider"/><span className="eyebrow">SELECTED NODE</span><h3>{selected.data.label || byScreener[selected.data.screener]?.label}</h3><p className="description">{byScreener[selected.data.screener]?.description || 'Connect this node to build your screening path.'}</p>
          {selected.data.kind === 'screener' && <p className="default-rule">Default pass condition: {defaultRuleText(byScreener[selected.data.screener], selected.data.params)}
            {byScreener[selected.data.screener]?.default_rule?.note && <span className="default-rule-note">{byScreener[selected.data.screener].default_rule.note}</span>}
          </p>}
          {selected.data.kind === 'screener' && <ThresholdDistribution node={selected} result={selectedResult} catalog={byScreener}/>}
          {(byScreener[selected.data.screener]?.parameters || []).filter(param => selected.data.screener !== 'price_change' || param.name !== 'custom_days' || selected.data.params?.period === 'custom').map(param => {
            const change = e => { const params = {...selected.data.params}; if (e.target.value === '') delete params[param.name]; else params[param.name] = param.type === 'number' ? Number(e.target.value) : e.target.value; update(selected.id, {params}); };
            return <label className="field" key={param.name}>{param.name.replaceAll('_', ' ')}
              {param.options ? <select disabled={busy} value={selected.data.params?.[param.name] ?? param.default} onChange={change}>{param.options.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select>
                : <input disabled={busy} type={param.type === 'number' ? 'number' : 'text'} step="any" placeholder={param.default == null ? 'Default' : String(param.default)} value={selected.data.params?.[param.name] ?? ''} onChange={change}/>}
            </label>;
          })}
          {selected.data.kind !== 'universe' && <button className="delete-node" disabled={busy} onClick={() => {setNodes(current => current.filter(n => n.id !== selected.id)); setEdges(current => current.filter(e => e.source !== selected.id && e.target !== selected.id));}}><Trash2 size={14}/> Remove node</button>}
        </>}
        <div className="cli-note"><span className="eyebrow">SAME WORKFLOW. YOUR TERMINAL.</span><p>Save this workflow and run it from the CLI.</p><code>python main.py<br/>--workflow workflow.json</code><ArrowUpRight size={16}/></div>
      </aside>
    </div>
    {stockContext && <div className="stock-backdrop" onMouseDown={closeStock}><aside className="stock-drawer" aria-label="Stock details" onMouseDown={e => e.stopPropagation()}>
      <button className="drawer-close" aria-label="Close stock details" onClick={closeStock}><X size={18}/></button>
      <ScreeningPath context={stockContext}/>
      {stockLoading && <div className="drawer-loading"><RefreshCw className="spin" size={22}/><strong>Loading {stockLoading} from FMP…</strong></div>}
      {stockError && <div className="drawer-loading"><strong>Details unavailable</strong><p>{stockError}</p></div>}
      {stockDetail && <><span className="eyebrow">FMP STOCK SNAPSHOT</span><h2>{stockDetail.overview.Name || stockDetail.symbol}</h2><p className="stock-identity">{stockDetail.symbol} · {[stockDetail.overview.Exchange, stockDetail.overview.Sector, stockDetail.overview.Industry].filter(Boolean).join(' · ')}</p>
        <p className="muted">Source: FMP (may be cached). Fetched: {stockDetail.overview.OverviewFetchedAt ? new Date(stockDetail.overview.OverviewFetchedAt).toLocaleString() : 'Unavailable'}. Quote time: {stockDetail.overview.QuoteTimestamp ? new Date(stockDetail.overview.QuoteTimestamp*1000).toLocaleString() : 'Unavailable'}. Financial period: {stockDetail.overview.FinancialPeriod || 'Unavailable'}. Ratios period: {stockDetail.overview.RatiosPeriod || 'Unavailable'}.</p>
        <p className="muted">Coverage: {metricDefinitions.filter(([key]) => stockDetail.overview[key] != null && stockDetail.overview[key] !== '').length}/{metricDefinitions.length} displayed metrics. Quote currency: {stockDetail.overview.Currency || 'Unavailable'}.</p>
        <div className="metric-grid">{metricDefinitions.map(([key,label,kind]) => <div key={key}><span>{label}</span><strong>{stockDetail.overview[key] == null || stockDetail.overview[key] === '' ? 'Unavailable' : formatMetric(stockDetail.overview[key], kind === 'currency' ? 'number' : kind)}</strong></div>)}</div>
        <FinancialHistory key={stockDetail.symbol} symbol={stockDetail.symbol} api={api}/>
        {stockDetail.overview.Description && <p className="company-description">{stockDetail.overview.Description}</p>}
        <div className="news-heading"><Newspaper size={16}/><h3>Recent news</h3><span>{stockDetail.news.length}</span></div>
        {stockDetail.news.length ? <div className="news-list">{stockDetail.news.map((article,index) => <article key={`${article.url}-${index}`}>{article.image && <img src={article.image} alt=""/>}<div><span>{[article.publisher, article.published_at ? new Date(article.published_at).toLocaleDateString() : ''].filter(Boolean).join(' · ')}</span><h4>{article.title}</h4>{article.summary && <p>{article.summary}</p>}{article.url && <a href={article.url} target="_blank" rel="noreferrer">Read article <ExternalLink size={12}/></a>}</div></article>)}</div> : <p className="no-news">No recent FMP news is available for this stock.</p>}
      </>}
    </aside></div>}
    <footer><span><i/> FMP data · local execution</span><span>{busy && run?.progress?.total ? `${run.progress.completed} / ${run.progress.total} stocks` : `${nodes.length} nodes · ${edges.length} connections`}<span className="footer-separator">|</span>Workflow v1</span></footer>
  </div>;
}

createRoot(document.getElementById('root')).render(<ReactFlowProvider><Studio/></ReactFlowProvider>);
