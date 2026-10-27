import React, {useMemo, useState} from 'react';
import {ArrowDownToLine, ArrowUpRight, Check} from 'lucide-react';
import {dcf, modelDefaults, scenarioInputs, sensitivity} from './valuation.js';
import {download, exportCsv} from './browserState.js';
import {useLocalDraft} from './useLocalDraft.js';
import {Section, TrendChart, fmt} from './ResearchUI.jsx';

export function Valuation({symbol, annual, quarter, overview, quoteCurrency, onStatus}) {
  const initial = useMemo(() => modelDefaults(annual,quarter,overview), [annual,quarter,overview]);
  const storageKey = `stock-pipeline.dcf.v1.${symbol}`;
  const {value:inputs, update:setInputs, save, dirty, saved} = useLocalDraft(storageKey, initial);
  const [scenario,setScenario] = useState('base');
  const effective = scenarioInputs(inputs,scenario);
  const comparable = !!inputs.currency && inputs.currency === quoteCurrency;
  const quote = comparable && overview.Price != null && overview.Price !== '' ? Number(overview.Price) : null;
  const result = dcf(effective,quote), grid = result.error ? [] : sensitivity(effective);
  const inputGroups = [
    ['Operating base', [['revenue','Base revenue (m)',1], ['startMargin','Base EBIT margin (%)',.5]]],
    ['Forecast assumptions', [['growth','Revenue growth, years 1–5 (%)',.5], ['targetMargin','Terminal EBIT margin (%)',.5],
      ['taxRate','Cash tax rate (%)',.5], ['salesCapital','Sales / invested capital (×)',.1]]],
    ['Terminal assumptions', [['wacc','WACC (%)',.25], ['terminalGrowth','Terminal growth (%)',.25], ['terminalRoic','Terminal ROIC (%)',.5]]],
    ['Equity bridge', [['cash','Cash & equivalents (m)',1], ['debt','Debt (m)',1], ['otherClaims','Minority & preferred claims (m)',1], ['shares','Share count (m)',1]]],
  ];
  const update = (key,value) => setInputs(a => ({...a,[key]:value}));
  return <div className="ir-valuation-layout"><Section title="Model assumptions" eyebrow="YOUR UNDERWRITING" className="ir-assumptions" action={<button title="Reset all assumptions using the latest source data" onClick={() => {setInputs({...initial});setScenario('base');}}>Reset</button>}>
    <p className="ir-description">Unlevered cash flow to the firm. Monetary inputs are millions of the statement currency.</p>
    {inputGroups.map(([group, fields]) => <fieldset className="ir-model-group" key={group}><legend>{group}</legend><div className="ir-model-fields">
      {group === 'Operating base' && <label>Statement currency<input aria-label="Statement currency" maxLength={3} value={inputs.currency} onChange={e => update('currency',e.target.value.toUpperCase())}/></label>}
      {group === 'Forecast assumptions' && <label>Explicit forecast<select value={inputs.years} onChange={e => update('years',Number(e.target.value))}><option value={10}>10 years · growth fades after year 5</option><option value={5}>5 years · step to terminal growth</option></select></label>}
      {fields.map(([key,label,step]) => <label key={key}>{label}<input type="number" step={step} value={inputs[key]} onChange={e => update(key,e.target.value)} placeholder="Required"/></label>)}
    </div></fieldset>)}
    <p className="ir-source">Income base: {inputs.baseDate || 'manual'} · Balance: {inputs.balanceDate || 'manual'}<br/>{inputs.sharesBasis}. All seed assumptions require review.</p>
    <p className="ir-source" role="status">{dirty ? 'Unsaved changes. Your draft is retained while you navigate.' : saved ? 'Saved in this browser.' : 'Review the starting assumptions, then save your base model.'}</p>
    <div className="ir-inline-actions"><button className="ir-primary" onClick={() => {const ok = save();onStatus(ok ? 'Base model saved in this browser.' : 'Browser storage is unavailable. Export the model to keep it.');}}><Check size={14}/>{saved ? 'Model saved' : 'Save base model'}</button>
      <button onClick={() => download(`${symbol}-dcf-${scenario}.json`,JSON.stringify({symbol,exported_at:new Date().toISOString(),scenario,inputs:effective,result},null,2),'application/json')}><ArrowDownToLine size={14}/> Export model</button></div>
  </Section><div className="ir-valuation-results">
    <Section title="Intrinsic value" eyebrow={`${scenario.toUpperCase()} CASE · ${inputs.currency || 'CURRENCY REQUIRED'} PER SHARE`}>
      {result.error ? <p className="ir-warning" role="alert">{result.error}</p> : <>
        <div className="ir-value-hero"><strong data-testid="fair-value">{fmt(result.fairValue,'number')}</strong><div><span>vs. quote {fmt(quote,'number')} {comparable ? quoteCurrency : ''}</span><b className={result.upside >= 0 ? 'ir-positive' : 'ir-negative'}>{result.upside == null ? 'Quote comparison unavailable' : `${fmt(result.upside,'change')} implied upside`}</b></div></div>
        {!comparable && <p className="ir-warning">Statement and quote currencies differ or are unknown. Value is shown in {inputs.currency}; upside is withheld. No automatic FX conversion.</p>}
        {result.equityValue <= 0 && <p className="ir-warning">The model gives nonpositive residual equity value. This is not an executable share-price target.</p>}
        <div className="ir-bridge">{[['PV of explicit cash flows',result.pv],['PV of terminal value',result.terminalPv],['Enterprise value',result.enterpriseValue],['+ Cash',Number(effective.cash)],['− Debt',-Number(effective.debt)],['− Other claims',-Number(effective.otherClaims)],['Equity value',result.equityValue]].map(([label,value]) => <div key={label}><span>{label}</span><b>{fmt(value,'number')}m</b></div>)}</div>
        <p className={result.terminalWeight > .75 ? 'ir-warning' : 'ir-source'}>Terminal value accounts for {fmt(result.terminalWeight,'percent')} of enterprise value.</p>
      </>}
    </Section>
    <Section title="Scenario comparison" eyebrow="ASSUMPTIONS DRIVE VALUE"><div className="ir-scenarios">{['bear','base','bull'].map(s => {const a = scenarioInputs(inputs,s), r = dcf(a,quote);return <button key={s} aria-pressed={s===scenario} onClick={() => setScenario(s)}><span>{s.toUpperCase()}</span><strong>{r.error ? '—' : fmt(r.fairValue,'number')}</strong><small>{fmt(a.growth/100,'percent')} growth · {fmt(a.wacc/100,'percent')} WACC</small></button>;})}</div></Section>
    {!result.error && <>
      <Section title="Sensitivity: WACC × terminal growth" eyebrow="VALUE PER SHARE"><div className="ir-table-scroll"><table className="ir-table ir-sensitivity"><thead><tr><th>WACC ↓ / g →</th>{[-1,-.5,0,.5,1].map(d => <th key={d}>{(Number(effective.terminalGrowth)+d).toFixed(2)}%</th>)}</tr></thead><tbody>{grid.map((r,i) => <tr key={i}><th>{r.wacc.toFixed(2)}%</th>{r.values.map((v,j) => <td key={j} className={i===2&&j===2 ? 'ir-base-cell' : ''} style={{background: !v.error && quote && v.fairValue > quote ? '#edf6f0' : undefined}}>{v.error ? '—' : fmt(v.fairValue,'number')}</td>)}</tr>)}</tbody></table></div></Section>
      <Section title="Explicit cash flow forecast" eyebrow="STATEMENT CURRENCY · MILLIONS" action={<button onClick={() => exportCsv(`${symbol}-dcf-forecast.csv`,[['Year','Revenue (m)','EBIT (m)','Cash tax (m)','Reinvestment (m)','FCFF (m)','PV FCFF (m)'],...result.forecast.map(r => [r.year,r.revenue,r.ebit,r.tax,r.reinvestment,r.fcff,r.presentValue])])}><ArrowDownToLine size={14}/> CSV</button>}>
        <TrendChart rows={result.forecast.map(r => ({...r,date:`Y${r.year}`}))} field="fcff" label="Forecast FCFF (m)" bar/>
        <div className="ir-table-scroll"><table className="ir-table"><thead><tr><th>Year</th><th>Revenue</th><th>EBIT margin</th><th>Cash tax</th><th>Net reinvestment</th><th>FCFF</th><th>PV FCFF</th></tr></thead><tbody>{result.forecast.map(r => <tr key={r.year}><th>Y{r.year}</th><td>{fmt(r.revenue,'number')}</td><td>{fmt(r.margin,'percent')}</td><td>{fmt(r.tax,'number')}</td><td>{fmt(r.reinvestment,'number')}</td><td>{fmt(r.fcff,'number')}</td><td>{fmt(r.presentValue,'number')}</td></tr>)}</tbody></table></div>
      </Section>
    </>}
    <details className="ir-card ir-methodology-details"><summary>Model methodology & limitations</summary><div className="ir-methodology"><p>FCFF = EBIT − cash tax − net reinvestment. Cash tax = max(EBIT, 0) × tax rate; no loss carryforwards are modelled. Net reinvestment = max(change in revenue, 0) / sales-to-capital ratio, covering net capex and working capital. No asset releases are assumed when revenue contracts.</p>
      <p>EBIT margins move linearly from base to target. Revenue grows at the selected rate in years 1–5, then fades linearly to terminal growth in a 10-year model. A 5-year model steps directly to stable growth. End-year discounting; the model begins after the selected annual base period, with no stub adjustment to today.</p>
      <p>Terminal FCFF = year n+1 NOPAT × (1 − g / terminal ROIC). Terminal value = terminal FCFF / (WACC − g). Equity = enterprise value + cash − debt − minority/preferred claims. Cash includes equivalents only; add other nonoperating assets manually after review.</p>
      <p>Stock compensation remains an operating expense through the EBIT margin; it is not added back. Share count is fixed. Review dilution, leases, pension deficits, investments and other claims independently. Defaults of 10% growth, 10% WACC, 25% tax, 2× sales/capital and 12% terminal ROIC are editable placeholders, not analyst estimates. Bear / bull shift base growth by −/+3pp, target margin by −/+2pp and WACC by +/−1pp. <a href="https://pages.stern.nyu.edu/~adamodar/pdfiles/country/val2daySept24.pdf" target="_blank" rel="noreferrer">FCFF methodology reference <ArrowUpRight size={12}/></a></p></div></details>
  </div></div>;
}
