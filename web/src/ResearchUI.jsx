import React, {useState} from 'react';
import {ArrowDownToLine, LoaderCircle} from 'lucide-react';
import {exportCsv} from './browserState.js';

export const metrics = [
  ['revenue','Revenue'], ['gross_profit','Gross profit'], ['operating_income','Operating income'],
  ['net_income','Net income'], ['eps','Diluted EPS','perShare'], ['operating_cash_flow','Operating cash flow'],
  ['capex','Capital expenditure'], ['free_cash_flow','Free cash flow'], ['fcf_per_share','FCF / diluted share','perShare'],
  ['stock_compensation','Stock compensation'], ['diluted_shares','Diluted shares','shares'],
  ['cash','Cash & equivalents'], ['debt','Total debt'], ['net_debt','Net debt'],
  ['equity','Shareholders’ equity'], ['assets','Total assets'], ['dividends','Dividends paid'], ['buybacks','Share repurchases'],
  ['gross_profit_margin','Gross margin','percent'], ['operating_income_margin','Operating margin','percent'],
  ['net_income_margin','Net margin','percent'], ['free_cash_flow_margin','FCF margin','percent'],
  ['cash_conversion','FCF / net income','multiple'], ['current_ratio','Current ratio','multiple'],
];
export function fmt(value, kind = 'compact') {
  if (value == null || value === '' || !Number.isFinite(Number(value))) return '—';
  const n = Number(value);
  if (kind === 'percent') return `${(n * 100).toFixed(1)}%`;
  if (kind === 'change') return `${n > 0 ? '+' : ''}${(n * 100).toFixed(1)}%`;
  if (kind === 'pp') return `${n > 0 ? '+' : ''}${(n * 100).toFixed(1)}pp`;
  if (kind === 'multiple') return n.toFixed(2) + '×';
  return n.toLocaleString('en-GB', {notation:kind === 'compact' || kind === 'shares' ? 'compact' : 'standard', maximumFractionDigits:2});
}
export function Busy({state, children}) {
  if (state.loading && !state.data) return <div className="ir-empty" role="status"><LoaderCircle className="ir-spin" size={20}/> Loading source data…</div>;
  return <>{state.error && <div className="ir-warning" role="alert">{state.error} Use Reload data to retry.</div>}
    {(!state.error || state.data) && children}</>;
}
export function Section({title, eyebrow, action, children, className = ''}) {
  return <section className={`ir-card ${className}`}><div className="ir-card-head"><div>{eyebrow && <span className="ir-eyebrow">{eyebrow}</span>}<h2>{title}</h2></div>{action}</div>{children}</section>;
}
export function TrendChart({rows, field, label, kind = 'compact', color = '#258166', bar = false, height = 235}) {
  const [hover, setHover] = useState(null);
  const valid = rows.map((row,index) => ({...row, index, value:row[field]})).filter(row => typeof row.value === 'number' && Number.isFinite(row.value));
  if (!valid.length) return <div className="ir-empty">No {label.toLowerCase()} observations available.</div>;
  const W = 780, H = height, left = 65, right = 20, top = 24, bottom = 34;
  let lo = Math.min(...valid.map(r => r.value)), hi = Math.max(...valid.map(r => r.value));
  if (bar) {lo = Math.min(lo, 0);hi = Math.max(hi, 0);}
  const pad = (hi - lo || Math.max(Math.abs(hi) * .1, 1)) * .1;
  if (!bar || lo < 0) lo -= pad;
  if (!bar || hi >= 0) hi += pad;
  const x = index => left + (W-left-right) * (rows.length === 1 ? .5 : index / (rows.length-1));
  const y = value => top + (H-top-bottom) * (hi-value)/(hi-lo);
  const tickIndexes = [...new Set([0,Math.floor((rows.length-1)/3),Math.floor((rows.length-1)*2/3),rows.length-1])];
  let path = '', gap = true;
  rows.forEach((row,index) => {if (typeof row[field] !== 'number' || !Number.isFinite(row[field])) {gap = true;return;} path += `${gap ? 'M' : 'L'}${x(index)},${y(row[field])} `;gap = false;});
  const active = hover != null ? valid.find(r => r.index === hover) : valid.at(-1);
  return <div className="ir-chart"><div className="ir-chart-caption"><span>{label}</span><strong>{active?.date} <b>{fmt(active?.value,kind)}</b></strong></div>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${label} over time. ${valid.length} observations. Latest ${valid.at(-1).date}: ${fmt(valid.at(-1).value,kind)}`} onMouseLeave={() => setHover(null)}>
      {[0,1,2,3,4].map(i => {const value = lo + (hi-lo)*i/4; return <g key={i}><line x1={left} x2={W-right} y1={y(value)} y2={y(value)} stroke="#e7ece8" strokeDasharray="3 5"/><text x={left-12} y={y(value)+4} textAnchor="end">{fmt(value,kind)}</text></g>;})}
      {lo < 0 && hi > 0 && <line x1={left} x2={W-right} y1={y(0)} y2={y(0)} stroke="#b6c6bd"/>}
      {bar ? valid.map(r => <rect key={r.index} x={x(r.index)-Math.min(18,480/rows.length)/2} y={Math.min(y(r.value),y(0))} width={Math.min(18,480/rows.length)} height={Math.max(1,Math.abs(y(r.value)-y(0)))} rx="2" fill={r.value < 0 ? '#be6a50' : color} opacity=".85"/>)
        : <path d={path} stroke={color} fill="none" strokeWidth="2.7" strokeLinejoin="round"/>}
      {valid.length < 45 && valid.map(r => <circle key={r.index} cx={x(r.index)} cy={y(r.value)} r="3.5" fill={color}/>)}
      {tickIndexes.map(i => <text key={i} x={x(i)} y={H-8} textAnchor={i === 0 ? 'start' : i === rows.length-1 ? 'end' : 'middle'}>{rows[i].date}</text>)}
      {hover != null && active && <g><line x1={x(active.index)} x2={x(active.index)} y1={top} y2={H-bottom} stroke="#6b8a7a" strokeDasharray="4 4"/><circle cx={x(active.index)} cy={y(active.value)} r="5" fill={color} stroke="white" strokeWidth="2"/></g>}
      <rect x={left} y={top} width={W-left-right} height={H-top-bottom} fill="transparent" onPointerMove={event => {
        const bounds = event.currentTarget.getBoundingClientRect();
        const fraction = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
        setHover(Math.round(fraction * (rows.length-1)));
      }}><title>{active ? `${active.date}: ${fmt(active.value,kind)}` : 'No observation for this period'}</title></rect>
    </svg>
  </div>;
}
export function MetricCard({label, value, change, note, kind}) {
  return <div className="ir-kpi"><span>{label}</span><strong>{fmt(value,kind)}</strong><small className={change == null ? '' : change >= 0 ? 'ir-positive' : 'ir-negative'}>{change == null ? note || 'Unavailable' : `${fmt(change,'change')} YoY`}</small></div>;
}
export function FinancialTable({data, symbol}) {
  const rows = data?.periods || [], reversed = [...rows].reverse();
  const currencies = [...new Set(rows.map(r => r.currency || 'Unknown'))].join(', ');
  return <><div className="ir-table-toolbar"><span>Reported values · {currencies} · money and share counts in millions, except per-share data</span>
    <button disabled={!rows.length} onClick={() => exportCsv(`${symbol}-${data.period}-financials.csv`, [['Metric','Unit',...rows.map(r => r.date)],['Reported currency','currency',...rows.map(r => r.currency)],...metrics.map(([key,label,kind]) => [label,kind === 'percent' ? 'fraction' : kind === 'perShare' ? 'currency / share' : kind || 'currency units',...rows.map(r => r[key])])])}><ArrowDownToLine size={14}/> Export CSV (raw units)</button></div>
    <div className="ir-table-scroll"><table className="ir-table ir-financial-table"><thead><tr><th>Financial metric</th>{reversed.map(r => <th key={r.date}>{r.fiscal_period} {r.date}<small>{r.currency || 'Currency unknown'}</small><small>Filed {r.sources?.income?.filed_at || r.sources?.balance?.filed_at || 'date unavailable'}</small></th>)}</tr></thead>
      <tbody>{metrics.map(([key,label,kind]) => <tr key={key}><th scope="row">{label}</th>{reversed.map(row => {
        const value = row[key] == null ? null : !kind || kind === 'shares' ? row[key]/1e6 : row[key];
        const change = kind === 'percent' ? row.yoy_pp?.[key] : row.yoy?.[key];
        return <td key={row.date}>{fmt(value,kind === 'shares' ? 'number' : kind || 'number')}
          {change != null && <small className={change >= 0 ? 'ir-positive' : 'ir-negative'}>{fmt(change,kind === 'percent' ? 'pp' : 'change')} YoY</small>}
        </td>;
      })}</tr>)}</tbody></table></div></>;
}
