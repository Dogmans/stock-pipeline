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
        <option value="default">Screener’s default rule</option><option value="gte">Score ≥</option><option value="lte">Score ≤</option>
      </select>
      {data.criterion.operator !== 'default' && <input type="number" step="any" aria-label="Score threshold" value={data.criterion.value ?? ''} disabled={data.busy}
        onChange={event => data.onUpdate(id, { criterion: { ...data.criterion, value: event.target.value === '' ? null : Number(event.target.value) } })}/>}
    </div>}
    {isScreener && data.criterion.operator === 'default' && <p className="default-rule">Pass when {defaultRuleText(data.catalog, data.params)}
      {data.catalog?.default_rule?.note && <span className="default-rule-note">{data.catalog.default_rule.note}</span>}
    </p>}
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
  useEffect(() => {
    if (!run?.id || !['queued', 'running', 'cancelling'].includes(run.status)) return;
    let stopped = false;
    const timer = setTimeout(async () => {
      try {
        const value = await api(`/runs/${run.id}`);
        if (stopped) return;
        setRun(value);
        if (value.result) savedSnapshot.current = value.result.snapshot_id;
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
      setRunKey(currentKey); setRun({ ...value, status: 'queued', progress: { message: 'Starting workflow', overall_percent: 0 } });
    } catch (err) { setError(err.message); } finally { setStarting(false); }
  }
  async function load(event) {
    try {
      const doc = JSON.parse(await event.target.files[0].text());
      await api('/workflows/validate', { method: 'POST', body: JSON.stringify({ workflow: doc }) });
      const graph = fromDocument(doc); setNodes(graph.nodes); setEdges(graph.edges);
      setName(doc.name || 'Untitled workflow'); setUniverse(doc.universe); setRun(null); setError('');
      savedSnapshot.current = null; setTimeout(() => fitView({ padding: .2 }), 100);
    } catch (err) { setError(err.message); }
    event.target.value = '';
  }
  async function openStock(symbol) {
    setStockDetail(null); setStockError(''); setStockLoading(symbol);
    try { setStockDetail(await api(`/stocks/${encodeURIComponent(symbol)}`)); }
    catch (err) { setStockError(err.message); }
    finally { setStockLoading(''); }
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
      <section className="results"><div className="results-heading"><div><span className="eyebrow">STOCK INSPECTOR</span><h2>{selected?.data.label || byScreener[selected?.data.screener]?.label || 'Select a node'} <span className="count-pill">{allRows.length}</span></h2></div>
        <div className="results-actions"><label className="search"><Search size={14}/><input aria-label="Filter stocks" placeholder="Filter stocks…" value={searchStocks} onChange={e => setSearchStocks(e.target.value)}/></label><button disabled={!rows.length} onClick={() => download('stocks.csv', csv(rows), 'text/csv')}><Download size={14}/> CSV</button></div></div>
        <div className="outcome-tabs">{Object.keys(colors).map(port => <button key={port} className={selection.port === port ? 'chosen' : ''} onClick={() => inspect(selection.id, port)}>{outcomeLabels[port]} <span>{selectedResult?.counts[port] ?? '—'}</span></button>)}</div>
        {rows.length ? <div className="table-scroll"><table><thead><tr><th>Symbol</th><th>Company</th><th>Score</th><th>Decision / reason</th></tr></thead><tbody>{rows.slice(0, 500).map(row => <tr key={row.symbol}><td><button className="stock-link" onClick={() => openStock(row.symbol)} disabled={stockLoading === row.symbol}>{stockLoading === row.symbol ? 'Loading…' : row.symbol}</button></td><td>{row.company_name || row.security || '—'}</td><td>{typeof row.score === 'number' ? row.score.toFixed(2) : '—'}</td><td>{row.reason || 'Included in universe'}</td></tr>)}</tbody></table>{rows.length > 500 && <p>Showing 500 rows. CSV includes all {rows.length} matching stocks.</p>}</div> : <div className="empty-state"><ListFilter size={23}/><div><strong>{stale ? 'Results need an update' : result ? 'No stocks in this outcome' : 'Your results will appear here'}</strong><p>{stale ? 'Run this workflow to see results for its current settings.' : result ? 'Select another outcome or connection to explore the run.' : 'Run the workflow, then click a node or connection to explore its stocks.'}</p></div></div>}
      </section></main>
      <aside className="inspector"><div className="section-heading">Workflow settings <SlidersHorizontal size={16}/></div><label className="field">Universe<select disabled={busy} value={universe.symbols ? 'custom' : universe.name} onChange={e => setUniverse(e.target.value === 'custom' ? {symbols: example.universe.symbols} : {name: e.target.value})}><option value="custom">Custom symbols</option><option value="sp500">S&P 500</option><option value="russell2000">Russell 2000</option><option value="nasdaq100">Nasdaq 100</option></select></label>
        {universe.symbols && <label className="field">Symbols<textarea disabled={busy} aria-label="Symbols" value={universe.symbols.join(', ')} onChange={e => setUniverse({symbols: e.target.value.toUpperCase().split(/[\s,]+/).filter(Boolean)})}/><small>Comma-separated stock symbols</small></label>}
        <div className="setting-divider"/><label className="reuse-option"><input type="checkbox" checked={reuse} disabled={busy} onChange={e => setReuse(e.target.checked)}/><span>Reuse calculated scores<small>Fast comparisons with your last run.</small></span></label>
        <p className="snapshot-note">{result?.snapshot_created_at ? `Snapshot started ${new Date(result.snapshot_created_at).toLocaleString()}.` : 'New scores use the existing FMP data cache.'} Changing a threshold reuses scores. Changing screener parameters may need more data.</p>
        {selected && <><div className="setting-divider"/><span className="eyebrow">SELECTED NODE</span><h3>{selected.data.label || byScreener[selected.data.screener]?.label}</h3><p className="description">{byScreener[selected.data.screener]?.description || 'Connect this node to build your screening path.'}</p>
          {selected.data.kind === 'screener' && <p className="default-rule">Default pass condition: {defaultRuleText(byScreener[selected.data.screener], selected.data.params)}
            {byScreener[selected.data.screener]?.default_rule?.note && <span className="default-rule-note">{byScreener[selected.data.screener].default_rule.note}</span>}
          </p>}
          {(byScreener[selected.data.screener]?.parameters || []).map(param => <label className="field" key={param.name}>{param.name.replaceAll('_', ' ')}<input disabled={busy} type={param.type === 'number' ? 'number' : 'text'} step="any" placeholder={param.default == null ? 'Default' : String(param.default)} value={selected.data.params?.[param.name] ?? ''}
            onChange={e => { const params = {...selected.data.params}; if (e.target.value === '') delete params[param.name]; else params[param.name] = param.type === 'number' ? Number(e.target.value) : e.target.value; update(selected.id, {params}); }}/></label>)}
          {selected.data.kind !== 'universe' && <button className="delete-node" disabled={busy} onClick={() => {setNodes(current => current.filter(n => n.id !== selected.id)); setEdges(current => current.filter(e => e.source !== selected.id && e.target !== selected.id));}}><Trash2 size={14}/> Remove node</button>}
        </>}
        <div className="cli-note"><span className="eyebrow">SAME WORKFLOW. YOUR TERMINAL.</span><p>Save this workflow and run it from the CLI.</p><code>python main.py<br/>--workflow workflow.json</code><ArrowUpRight size={16}/></div>
      </aside>
    </div>
    {(stockDetail || stockError || stockLoading) && <div className="stock-backdrop" onMouseDown={() => {setStockDetail(null); setStockError(''); setStockLoading('');}}><aside className="stock-drawer" aria-label="Stock details" onMouseDown={e => e.stopPropagation()}>
      <button className="drawer-close" aria-label="Close stock details" onClick={() => {setStockDetail(null); setStockError(''); setStockLoading('');}}><X size={18}/></button>
      {stockLoading && <div className="drawer-loading"><RefreshCw className="spin" size={22}/><strong>Loading {stockLoading} from FMP…</strong></div>}
      {stockError && <div className="drawer-loading"><strong>Details unavailable</strong><p>{stockError}</p></div>}
      {stockDetail && <><span className="eyebrow">FMP STOCK SNAPSHOT</span><h2>{stockDetail.overview.Name || stockDetail.symbol}</h2><p className="stock-identity">{stockDetail.symbol} · {[stockDetail.overview.Exchange, stockDetail.overview.Sector, stockDetail.overview.Industry].filter(Boolean).join(' · ')}</p>
        <div className="metric-grid">{metricDefinitions.filter(([key]) => stockDetail.overview[key] != null && stockDetail.overview[key] !== '').map(([key,label,kind]) => <div key={key}><span>{label}</span><strong>{formatMetric(stockDetail.overview[key], kind)}</strong></div>)}</div>
        {stockDetail.overview.Description && <p className="company-description">{stockDetail.overview.Description}</p>}
        <div className="news-heading"><Newspaper size={16}/><h3>Recent news</h3><span>{stockDetail.news.length}</span></div>
        {stockDetail.news.length ? <div className="news-list">{stockDetail.news.map((article,index) => <article key={`${article.url}-${index}`}>{article.image && <img src={article.image} alt=""/>}<div><span>{[article.publisher, article.published_at ? new Date(article.published_at).toLocaleDateString() : ''].filter(Boolean).join(' · ')}</span><h4>{article.title}</h4>{article.summary && <p>{article.summary}</p>}{article.url && <a href={article.url} target="_blank" rel="noreferrer">Read article <ExternalLink size={12}/></a>}</div></article>)}</div> : <p className="no-news">No recent FMP news is available for this stock.</p>}
      </>}
    </aside></div>}
    <footer><span><i/> FMP data · local execution</span><span>{busy && run?.progress?.total ? `${run.progress.completed} / ${run.progress.total} stocks` : `${nodes.length} nodes · ${edges.length} connections`}<span className="footer-separator">|</span>Workflow v1</span></footer>
  </div>;
}

createRoot(document.getElementById('root')).render(<ReactFlowProvider><Studio/></ReactFlowProvider>);
