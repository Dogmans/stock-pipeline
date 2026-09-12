import React, {useEffect, useMemo, useState} from 'react';
import {defaultRuleText} from './workflow.js';
import {numeric, pathNodes, rankRows, nearMisses, ruleFor, runChanges} from './insights.js';

const display = value => numeric(value) ? value.toLocaleString(undefined,{maximumFractionDigits:2}) : 'Unavailable';
const percent = value => numeric(value) ? `${display(value)}%` : 'Unavailable';
const comparisonFields = [
  ['Sector','Sector'], ['Industry','Industry'], ['Currency','Quote currency'], ['Price','Price'],
  ['MarketCapitalization','Market cap'], ['PERatio','P/E'], ['PriceToBookRatio','Price / book'],
  ['ReturnOnEquityTTM','Return on equity',100], ['ProfitMargin','Profit margin',100],
  ['DebtToEquityRatio','Debt / equity'], ['FreeCashFlowYield','Free cash flow yield',100],
  ['AverageVolume','Average daily volume'], ['FinancialPeriod','Financial period'], ['RatiosPeriod','Ratios period'],
  ['AnnualPeriod','Annual statement period'], ['AnnualCurrency','Statement currency'], ['AnnualRevenueGrowth','Annual revenue growth',100],
  ['AnnualRevenue','Annual revenue'], ['AnnualDebt','Annual debt'], ['AnnualFreeCashFlow','Annual free cash flow'],
];

export function ThresholdDistribution({node, result, catalog}) {
  const rule = ruleFor(node,catalog,result);
  if (!rule || !result) return null;
  const rows = Object.values(result.outcomes).flat(), values = rows.map(r => r[rule.field]).filter(numeric);
  if (!values.length) return <p className="muted">No numeric values available for this threshold.</p>;
  const bounds = rule.operator === 'between' ? [...new Set([rule.value, rule.upper_value])] : [rule.value];
  const min = Math.min(...values,...bounds), max = Math.max(...values,...bounds), span = max-min || 1;
  const bins = Array.from({length:12},() => 0);
  values.forEach(v => bins[Math.min(11,Math.floor((v-min)/span*12))]++);
  const peak = Math.max(...bins,1);
  return <section className="threshold-distribution"><h4>{rule.metric} distribution</h4>
    <svg viewBox="0 0 220 92" role="img" aria-label={`${values.length} values, range ${min} to ${max}, thresholds ${bounds.join(' to ')}`}>
      {bins.map((count,i) => <rect key={i} x={10+i*200/12} y={65-count/peak*50} width={14} height={count/peak*50} fill="#7faf96"><title>{count} stocks</title></rect>)}
      {bounds.map(bound => <line key={bound} x1={10+(bound-min)/span*200} x2={10+(bound-min)/span*200} y1="8" y2="68" stroke="#94652e" strokeWidth="2"/>)}
      <text x="10" y="84">{display(min)}</text><text x="210" y="84" textAnchor="end">{display(max)}</text>
    </svg><p>{defaultRuleText({default_rule:rule})} - {values.length}/{rows.length} numeric values</p>
    <p>{result.counts.passed} passed · {result.counts.failed} failed · {result.counts.unavailable + result.counts.error} unavailable or errors</p>
  </section>;
}

export function FinancialHistory({symbol, api}) {
  const [data,setData] = useState(null), [error,setError] = useState(''), [loading,setLoading] = useState(false);
  useEffect(() => {setData(null);setError('');setLoading(false);},[symbol]);
  async function load() {
    setLoading(true);setError('');
    try {setData(await api(`/stocks/${encodeURIComponent(symbol)}/financial-history`));}
    catch(e) {setError(e.message);} finally {setLoading(false);}
  }
  return <section className="financial-history"><h3>Financial history</h3>
    {!data && <button disabled={loading} onClick={load}>{loading ? 'Loading annual statements…' : 'Load five-year financial history'}</button>}
    {error && <p role="alert">{error}</p>}
    {data && <><p className="muted">{data.source}. Annual periods; amounts in each statement’s reported currency.</p>
      {data.missing.length > 0 && <p>Unavailable statements: {data.missing.join(', ')}</p>}
      {data.periods.length ? <div className="table-scroll"><table><thead><tr><th>Period</th><th>Currency</th><th>Revenue</th><th>Net income</th><th>Margin</th><th>Debt</th><th>Free cash flow</th></tr></thead><tbody>{data.periods.map(p => <tr key={p.date}><td>{p.date}</td><td>{p.currency || 'Unknown'}</td><td>{display(p.revenue)}</td><td>{display(p.net_income)}</td><td>{numeric(p.margin) ? percent(p.margin*100) : 'Unavailable'}</td><td>{display(p.debt)}</td><td>{display(p.free_cash_flow)}</td></tr>)}</tbody></table></div> : <p>No annual statements available.</p>}
    </>}
  </section>;
}

function Comparison({rows, api}) {
  const [symbols,setSymbols] = useState([]), [details,setDetails] = useState(null), [loading,setLoading] = useState(false);
  useEffect(() => {setDetails(null);},[symbols]);
  async function compare() {
    setLoading(true);
    const records = [];
    for (const symbol of symbols) {
      let detail;
      try {detail = await api(`/stocks/${encodeURIComponent(symbol)}`);}
      catch(e) {detail = {symbol,overview:{},error:e.message};}
      try {
        const history = await api(`/stocks/${encodeURIComponent(symbol)}/financial-history`);
        const [latest,previous] = history.periods.filter(p => numeric(p.revenue));
        if (latest) {
          const days = previous ? (new Date(latest.date)-new Date(previous.date))/86400000 : 0;
          Object.assign(detail.overview,{AnnualPeriod:latest.date,AnnualCurrency:latest.currency,
            AnnualRevenue:latest.revenue,AnnualDebt:latest.debt,AnnualFreeCashFlow:latest.free_cash_flow,
            AnnualRevenueGrowth:previous?.revenue > 0 && latest.currency && latest.currency === previous.currency && days >= 300 && days <= 430 ? latest.revenue/previous.revenue-1 : null});
        }
      } catch {detail.historyError = 'Annual statements unavailable';}
      records.push(detail);
    }
    setDetails(records);setLoading(false);
  }
  return <><p>Select 2–5 stocks to compare. Missing fields remain visible.</p>
    <div className="compare-picker">{rows.map(row => <label key={row.symbol}><input type="checkbox" checked={symbols.includes(row.symbol)} disabled={loading || (!symbols.includes(row.symbol) && symbols.length >= 5)} onChange={e => setSymbols(e.target.checked ? [...symbols,row.symbol] : symbols.filter(s => s !== row.symbol))}/>{row.symbol}</label>)}</div>
    <button disabled={symbols.length < 2 || loading} onClick={compare}>{loading ? 'Loading comparison…' : `Compare ${symbols.length} stocks`}</button>
    {details && <div className="table-scroll"><table className="comparison-table"><thead><tr><th>Metric</th>{details.map(d => <th key={d.symbol}>{d.symbol}</th>)}</tr></thead><tbody>
      <tr><th>Data status</th>{details.map(d => <td key={d.symbol}>{d.error || d.overview.DataCompleteness || 'Coverage unknown'}{d.historyError && <p>{d.historyError}</p>}</td>)}</tr>
      {comparisonFields.map(([key,label,multiplier]) => <tr key={key}><th>{label}</th>{details.map(d => {
        const value = d.overview[key];
        return <td key={d.symbol} className={value == null || value === '' ? 'missing-value' : ''}>{value == null || value === '' ? 'Unavailable' : multiplier ? percent(Number(value)*multiplier) : typeof value === 'number' ? display(value) : String(value)}</td>;
      })}
      </tr>)}
      <tr><th>Quote time</th>{details.map(d => <td key={d.symbol}>{d.overview.QuoteTimestamp ? new Date(d.overview.QuoteTimestamp*1000).toLocaleString() : 'Unavailable'}</td>)}</tr>
    </tbody></table><p className="muted">Source: FMP, potentially cached. Financial ratios may refer to different reporting periods; quote currencies are shown above.</p></div>}
  </>;
}

function Changes({record, history, selection, api}) {
  const [previous,setPrevious] = useState(null), [error,setError] = useState(''), [loading,setLoading] = useState(false);
  const options = history.filter(r => r.id !== record?.id && r.saved_at < record.saved_at);
  async function choose(id) {
    setPrevious(null);setError('');
    if (!id) return;
    setLoading(true);
    try {setPrevious(await api(`/history/${id}`));} catch(e) {setError(e.message);} finally {setLoading(false);}
  }
  const changes = runChanges(record,previous,selection);
  const compatible = previous?.workflow.nodes.some(n => n.id === selection.id);
  return <><label>Compare with saved run <select defaultValue="" disabled={loading} onChange={e => choose(e.target.value)}><option value="">Choose a previous run</option>{options.map(r => <option key={r.id} value={r.id}>{r.name} · {new Date(r.saved_at).toLocaleString()}</option>)}</select></label>
    {loading && <p>Loading previous run…</p>}{error && <p role="alert">{error}</p>}
    {previous && !compatible && <p>The selected node does not exist in that run. Choose a run from the same workflow.</p>}
    {previous && compatible && <><p>{changes.filter(r => r.change === 'Entered').length} entered · {changes.filter(r => r.change === 'Departed').length} departed · {changes.filter(r => r.change === 'Updated').length} updated.</p>
      <p className="muted">Differences may reflect changes to rules, the universe or data. Compare the recorded decisions below.</p>
      <div className="table-scroll"><table><thead><tr><th>Stock</th><th>Change</th><th>Previous path</th><th>Current path</th></tr></thead><tbody>{changes.map(row => <tr key={row.symbol}><td>{row.symbol}</td><td>{row.change}</td>{['before','after'].map(key => <td key={key}>{row[key].map(step => <p key={step.id}>{step.label}: {step.outcome} · {display(step.score)}{step.reason ? ` — ${step.reason}` : ''}</p>)}</td>)}</tr>)}</tbody></table></div>
      {!changes.length && <p>The same stocks are in this outcome.</p>}
    </>}
  </>;
}

function Performance({record, selection, api}) {
  const [benchmark,setBenchmark] = useState('SPY'), [data,setData] = useState(null), [loading,setLoading] = useState(false), [error,setError] = useState('');
  async function load() {
    setLoading(true);setError('');setData(null);
    try {setData(await api(`/history/${record.id}/performance?output_id=${encodeURIComponent(selection.id)}&benchmark=${encodeURIComponent(benchmark)}`));}
    catch(e) {setError(e.message);} finally {setLoading(false);}
  }
  return <><p>Track this saved shortlist after its creation against a benchmark of your choice.</p>
    <label>Benchmark <input aria-label="Benchmark symbol" value={benchmark} disabled={loading} onChange={e => {setBenchmark(e.target.value.toUpperCase());setData(null);}}/></label>
    <button disabled={loading || !record?.id || !benchmark} onClick={load}>{loading ? 'Loading prices…' : 'Calculate forward returns'}</button>
    {error && <p role="alert">{error}</p>}
    {data && <><p>{data.message}</p>{!data.pending && <><p>{data.start} → {data.end} · Equal-weight shortlist: {percent(data.portfolio_return)} · {data.benchmark}: {percent(data.benchmark_return)}</p>
      <div className="table-scroll"><table><thead><tr><th>Stock</th><th>Price return</th></tr></thead><tbody>{data.rows.map(r => <tr key={r.symbol}><td>{r.symbol}</td><td>{percent(r.return_percent)}</td></tr>)}</tbody></table></div></>}</>}
  </>;
}

export default function ResearchPanel({children, rows, selection, nodes, edges, result, catalog, api, openStock, record, history, onRestore}) {
  const [tab,setTab] = useState('stocks'), [weights,setWeights] = useState({}), [tolerance,setTolerance] = useState(10);
  const path = useMemo(() => pathNodes(selection,nodes,edges),[selection,nodes,edges]);
  const ranked = useMemo(() => rankRows(rows,path,result,catalog,weights),[rows,path,result,catalog,weights]);
  const misses = useMemo(() => nearMisses(path,result,catalog,tolerance),[path,result,catalog,tolerance]);
  const output = nodes.find(n => n.id === selection.id)?.data.kind === 'output';
  const tabs = [['stocks','Stocks'],['rank','Rank'],['compare','Compare'],['near','Near misses'],['changes','Changes'],['history','Saved runs'],...(output ? [['performance','Performance']] : [])];
  return <><nav className="research-tabs" aria-label="Stock research views">{tabs.map(([id,label]) => <button key={id} className={tab === id ? 'chosen' : ''} onClick={() => setTab(id)}>{label}</button>)}</nav>
    {tab === 'stocks' ? children : <div className="research-content">
      {tab === 'rank' && <><p>Weighted percentile rank within these {rows.length} stocks. Higher is better. A missing active factor leaves the overall rank unavailable.</p>
        <div className="ranking-weights">{path.map(node => <label key={node.id}>{node.data.label || catalog[node.data.screener]?.label || node.data.screener}<input aria-label={`${node.data.screener} weight`} type="number" min="0" max="10" step="1" value={weights[node.id] ?? 1} onChange={e => setWeights({...weights,[node.id]:Math.max(0,Math.min(10,Number(e.target.value) || 0))})}/></label>)}</div>
        {!path.length ? <p>Add a screener to rank this path.</p> : <div className="table-scroll"><table><thead><tr><th>Stock</th><th>Rank / 100</th><th>Coverage</th>{path.map(n => <th key={n.id}>{n.data.label || catalog[n.data.screener]?.label || n.data.screener}</th>)}</tr></thead><tbody>{ranked.map(row => <tr key={row.symbol}><td><button className="stock-link" onClick={() => openStock(row.symbol)}>{row.symbol}</button></td><td>{display(row.rank)}</td><td>{row.coverage}</td>{row.factors.map(f => <td key={f.id}>{display(f.value)}<small>{display(f.percentile)} percentile · weight {f.weight}</small></td>)}</tr>)}</tbody></table></div>}
      </>}
      {tab === 'compare' && <Comparison rows={rows} api={api}/>}
      {tab === 'near' && <><label>Maximum distance from threshold (%) <input type="number" min="0" max="100" value={tolerance} onChange={e => setTolerance(Math.max(0,Math.min(100,Number(e.target.value) || 0)))}/></label>
        <p className="muted">Failed evaluations on this path, ordered by relative threshold gap. Later screens may not have evaluated these stocks. Zero thresholds only include exact-boundary failures.</p>
        {misses.length ? <div className="table-scroll"><table><thead><tr><th>Stock</th><th>Failed screen</th><th>Actual</th><th>Threshold</th><th>Gap</th></tr></thead><tbody>{misses.map(r => <tr key={`${r.nodeId}-${r.symbol}`}><td><button className="stock-link" onClick={() => openStock(r.symbol,{id:r.nodeId,port:'failed'})}>{r.symbol}</button></td><td>{r.label}</td><td>{display(r.value)}</td><td>{display(r.threshold)}</td><td>{percent(r.percent)}</td></tr>)}</tbody></table></div> : <p>No near misses within this range.</p>}
      </>}
      {tab === 'changes' && (record ? <Changes record={record} history={history} selection={selection} api={api}/> : <p>Complete or restore a saved run to compare changes.</p>)}
      {tab === 'history' && <><p>Completed runs are saved locally, including their workflow and decisions.</p>{history.length ? <ul className="saved-runs">{history.map(r => <li key={r.id}><span>{r.name} · {new Date(r.saved_at).toLocaleString()}</span><button onClick={() => onRestore(r.id)}>Open run</button></li>)}</ul> : <p>No saved runs yet. Complete a workflow to create one.</p>}</>}
      {tab === 'performance' && (record ? <Performance record={record} selection={selection} api={api}/> : <p>Complete and save a run first.</p>)}
    </div>}
  </>;
}
