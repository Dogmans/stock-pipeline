import React, {useState} from 'react';
import {ArrowDownToLine} from 'lucide-react';
import {exportCsv} from './browserState.js';
import {Section, TrendChart, fmt} from './ResearchUI.jsx';

export const profitabilityMetrics = [
  ['roe','TTM return on equity (ROE)','percent',.15],
  ['roa','TTM return on assets (ROA)','percent',.10],
  ['roe_change_3y','ROE change over three years','pp',0],
  ['roce','TTM return on capital employed (ROCE)','percent',.30],
];

export default function ProfitabilityPanel({data, symbol}) {
  const [metric,setMetric] = useState('roe');
  const latest = data?.latest || {}, rows = data?.history || [];
  const selected = profitabilityMetrics.find(m => m[0] === metric);
  return <Section title="Profitability traits" eyebrow="BUSINESS QUALITY · TRAILING 12 MONTHS" action={<button disabled={!rows.length} onClick={() => exportCsv(`${symbol}-profitability.csv`,
    [['Period','Currency','ROE (fraction)','ROA (fraction)','ROCE (fraction)','ROE 3 years ago (fraction)','Comparison period','ROE change (fraction; ×100 for pp)'],
      ...rows.map(r => [r.date,r.currency,r.roe,r.roa,r.roce,r.roe_3y_ago,r.comparison_date,r.roe_change_3y])])}><ArrowDownToLine size={14}/> Export profitability CSV</button>}>
    <p className="ir-source">Period ended {latest.date || 'unavailable'} · {latest.currency || 'Currency unavailable'} · Closing balance-sheet denominators</p>
    <div className="ir-kpi-grid">{profitabilityMetrics.map(([key,label,kind,threshold]) => {
      const value = latest[key], pass = value != null && (key === 'roe_change_3y' ? value > threshold : value >= threshold);
      return <div className="ir-kpi" key={key}><span>{label}</span><strong>{fmt(value,kind)}</strong><small>{key === 'roe_change_3y' ? '> 0pp' : `≥ ${fmt(threshold,'percent')}`} · {value == null ? 'Unavailable' : pass ? 'Pass' : 'Fail'}</small>
        {value == null && <small>{latest.reasons?.[key] || 'Quarterly statements unavailable.'}</small>}</div>;
    })}</div>
    <p className="ir-source">ROE three years earlier: {fmt(latest.roe_3y_ago,'percent')} · {latest.comparison_date || 'Comparison period unavailable'}</p>
    <label>Profitability chart <select aria-label="Profitability chart metric" value={metric} onChange={e=>setMetric(e.target.value)}>{profitabilityMetrics.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
    <TrendChart rows={rows} field={metric} label={selected[1]} kind={selected[2]}/>
    <p className="ir-source">{data?.methodology || 'Four consecutive reported quarters and matching balance-sheet data are required.'}</p>
    <p className="ir-source">Source: {data?.source || 'FMP reported quarterly statements'}. <a href="https://www.youtube.com/watch?v=ESjh3718bnI" target="_blank" rel="noreferrer">Video methodology</a>. Its stacked example excludes financial services, energy, utilities, basic materials and real estate. Ratios remain visible for all sectors here; these thresholds are research filters.</p>
  </Section>;
}
