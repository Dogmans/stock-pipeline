import React, {useMemo, useState} from 'react';
import {ArrowDownToLine, ArrowUpRight, Check} from 'lucide-react';
import {dcf, modelDefaults, scenarioInputs, sensitivity} from './valuation.js';
import {download, exportCsv} from './browserState.js';
import {useLocalDraft} from './useLocalDraft.js';
import {Section, TrendChart, fmt} from './ResearchUI.jsx';

export function Valuation({symbol, annual, quarter, overview, quoteCurrency, onStatus}) {
  const [model,setModel] = useState('simple');
  return <><Section title="Valuation method" eyebrow="CHOOSE YOUR CASH FLOW FORECAST" className="ir-model-choice">
    <label>DCF model<select aria-label="DCF model" value={model} onChange={e => setModel(e.target.value)}>
      <option value="simple">Simple DCF — grow free cash flow directly</option>
      <option value="advanced">Advanced DCF — revenue, margins & reinvestment</option>
    </select></label>
    <p className="ir-description">Simple projects the free cash flow you enter. Advanced calculates cash flow from operating assumptions. Each model has its own saved inputs.</p>
  </Section><ValuationModel key={model} {...{symbol,annual,quarter,overview,quoteCurrency,onStatus,model}}/></>;
}

export function ValuationModel({symbol, annual, quarter, overview, quoteCurrency, onStatus, model}) {
  const simple = model === 'simple', rateKey = simple ? 'discountRate' : 'wacc';
  const rateLabel = simple ? 'Discount rate' : 'WACC';
  const initial = useMemo(() => modelDefaults(annual,quarter,overview,model), [annual,quarter,overview,model]);
  const storageKey = simple ? `stock-pipeline.dcf.simple.v1.${symbol}` : `stock-pipeline.dcf.v1.${symbol}`;
  const {value:inputs, update:setInputs, save, dirty, saved} = useLocalDraft(storageKey, initial);
  const [scenario,setScenario] = useState('base');
  const effective = scenarioInputs({...inputs,model},scenario);
  const comparable = !!inputs.currency && inputs.currency === quoteCurrency;
  const quote = comparable && overview.Price != null && overview.Price !== '' ? Number(overview.Price) : null;
  const result = dcf(effective,quote), grid = result.error ? [] : sensitivity(effective);
  const higherGrowth = simple || result.error ? null : dcf({...effective,growth:Number(effective.growth)+1},quote);
  const inputGroups = simple ? [
    ['Starting cash flow', [['fcf','Starting free cash flow (m)',1], ['shares','Share count (m)',1]]],
    ['Forecast assumptions', [['growth','Annual FCF growth (%)',.5]]],
    ['Terminal assumptions', [['discountRate','Discount rate / required return (%)',.25], ['terminalGrowth','Terminal FCF growth (%)',.25]]],
  ] : [
    ['Operating base', [['revenue','Base revenue (m)',1], ['startMargin','Base EBIT margin (%)',.5]]],
    ['Forecast assumptions', [['growth','Revenue growth, years 1–5 (%)',.5], ['targetMargin','Terminal EBIT margin (%)',.5],
      ['taxRate','Cash tax rate (%)',.5], ['salesCapital','Incremental sales / capital (×)',.1]]],
    ['Terminal assumptions', [['wacc','WACC (%)',.25], ['terminalGrowth','Terminal growth (%)',.25], ['terminalRoic','Terminal ROIC (%)',.5]]],
    ['Equity bridge', [['cash','Cash & equivalents (m)',1], ['debt','Debt (m)',1], ['otherClaims','Minority & preferred claims (m)',1], ['shares','Share count (m)',1]]],
  ];
  const update = (key,value) => setInputs(a => ({...a,[key]:value}));
  return <div className="ir-valuation-layout"><Section title="Model assumptions" eyebrow="YOUR UNDERWRITING" className="ir-assumptions" action={<button title="Reset all assumptions using the latest source data" onClick={() => {setInputs({...initial});setScenario('base');}}>Reset</button>}>
    <p className="ir-description">{simple ? 'Grow starting FCF directly, then discount it at your required equity return. No additional reinvestment is deducted.' : 'Forecast revenue, operating margins, tax and reinvestment to calculate unlevered FCFF.'} Monetary inputs are millions of the statement currency.</p>
    {inputGroups.map(([group, fields]) => <fieldset className="ir-model-group" key={group}><legend>{group}</legend><div className="ir-model-fields">
      {(group === 'Operating base' || group === 'Starting cash flow') && <label>Statement currency<input aria-label="Statement currency" maxLength={3} value={inputs.currency} onChange={e => update('currency',e.target.value.toUpperCase())}/></label>}
      {group === 'Forecast assumptions' && <label>Explicit forecast<select value={inputs.years} onChange={e => update('years',Number(e.target.value))}><option value={10}>{simple ? '10 years · constant FCF growth' : '10 years · growth fades after year 5'}</option><option value={5}>5 years · step to terminal growth</option></select></label>}
      {fields.map(([key,label,step]) => <label key={key}>{label}<input type="number" step={step} value={inputs[key] ?? ''} onChange={e => update(key,e.target.value)} placeholder="Required"/></label>)}
    </div></fieldset>)}
    <p className="ir-source">{simple ? 'FCF base' : 'Income base'}: {inputs.baseDate || 'manual'}{!simple && <> · Balance: {inputs.balanceDate || 'manual'}</>}<br/>{inputs.sharesBasis}. All seed assumptions require review.</p>
    <p className="ir-source" role="status">{dirty ? 'Unsaved changes. Your draft is retained while you navigate.' : saved ? 'Saved in this browser.' : 'Review the starting assumptions, then save your base model.'}</p>
    <div className="ir-inline-actions"><button className="ir-primary" onClick={() => {const ok = save();onStatus(ok ? 'Base model saved in this browser.' : 'Browser storage is unavailable. Export the model to keep it.');}}><Check size={14}/>{saved ? 'Model saved' : 'Save base model'}</button>
      <button onClick={() => download(`${symbol}-dcf-${model}-${scenario}.json`,JSON.stringify({symbol,exported_at:new Date().toISOString(),scenario,inputs:effective,result},null,2),'application/json')}><ArrowDownToLine size={14}/> Export model</button></div>
  </Section><div className="ir-valuation-results">
    <Section title="Intrinsic value" eyebrow={`${scenario.toUpperCase()} CASE · ${inputs.currency || 'CURRENCY REQUIRED'} PER SHARE`}>
      {result.error ? <p className="ir-warning" role="alert">{result.error}</p> : <>
        <div className="ir-value-hero"><strong data-testid="fair-value">{fmt(result.fairValue,'number')}</strong><div><span>vs. quote {fmt(quote,'number')} {comparable ? quoteCurrency : ''}</span><b className={result.upside >= 0 ? 'ir-positive' : 'ir-negative'}>{result.upside == null ? 'Quote comparison unavailable' : `${fmt(result.upside,'change')} implied upside`}</b></div></div>
        {!comparable && <p className="ir-warning">Statement and quote currencies differ or are unknown. Value is shown in {inputs.currency}; upside is withheld. No automatic FX conversion.</p>}
        {result.equityValue <= 0 && <p className="ir-warning">The model gives nonpositive residual equity value. This is not an executable share-price target.</p>}
        {higherGrowth && !higherGrowth.error && higherGrowth.fairValue < result.fairValue && <p className="ir-warning">With these assumptions, +1pp revenue growth lowers value by {fmt(result.fairValue-higherGrowth.fairValue,'number')} {inputs.currency} per share. Extra sales require investment; review EBIT margins and incremental sales / capital.</p>}
        <div className="ir-bridge">{[['PV of explicit cash flows',result.pv],['PV of terminal value',result.terminalPv],...(!simple ? [['Enterprise value',result.enterpriseValue],['+ Cash',Number(effective.cash)],['− Debt',-Number(effective.debt)],['− Other claims',-Number(effective.otherClaims)]] : []),['Equity value',result.equityValue]].map(([label,value]) => <div key={label}><span>{label}</span><b>{fmt(value,'number')}m</b></div>)}</div>
        <p className={result.terminalWeight > .75 ? 'ir-warning' : 'ir-source'}>Terminal value accounts for {fmt(result.terminalWeight,'percent')} of {simple ? 'equity' : 'enterprise'} value.</p>
      </>}
    </Section>
    <Section title="How this DCF works" className="ir-dcf-explanation" eyebrow={simple ? 'SIMPLE · DIRECT FREE CASH FLOW' : 'ADVANCED · OPERATING CASH FLOW'}>
      {simple ? <><p>Your FCF growth rate applies in every forecast year. It changes only projected FCF; there is no separate assumption about investment needed to generate growth. With positive starting FCF, higher growth increases value when other inputs stay fixed.</p>
        <ol><li>Forecast: <code>FCF(t) = starting FCF × (1 + growth)^t</code>.</li>
          <li>Discount each year: <code>PV(t) = FCF(t) / (1 + discount rate)^t</code>.</li>
          <li>Terminal value: <code>FCF(n) × (1 + terminal growth) / (discount rate − terminal growth)</code>, discounted back n years.</li>
          <li>Add the discounted cash flows and terminal value, then divide by shares.</li></ol>
        <p className="ir-source">The starting value is reported operating cash flow less capex, used as a proxy for cash available to shareholders. Review and normalise it for financing needs and interest classification. This model treats entered FCF as equity cash flow: it does not add cash or subtract debt separately. Discount rate is your required equity return.</p>
      </> : <><p>Revenue growth generates sales. EBIT margins and tax determine operating profit; the sales / capital assumption determines additional investment. These are explicit assumptions about how growth is funded, so faster growth can lower value.</p>
        <ol><li><code>Revenue(t) = revenue(t−1) × (1 + revenue growth)</code>.</li>
          <li><code>Reinvestment = max(change in revenue, 0) / sales-to-capital</code>.</li>
          <li><code>FCFF = EBIT − cash tax − reinvestment</code>. Discount FCFF at WACC.</li>
          <li>Discount terminal FCFF, add cash, subtract debt and other claims, then divide by shares.</li></ol>
      </>}
      {!result.error && <p className="ir-source">With your inputs, year 1 {simple ? 'FCF' : 'FCFF'} is {fmt(result.forecast[0][simple ? 'fcf' : 'fcff'],'number')}m; its present value is {fmt(result.forecast[0].presentValue,'number')}m. Discounted forecast cash flows ({fmt(result.pv,'number')}m) + discounted terminal value ({fmt(result.terminalPv,'number')}m){simple ? '' : ' + cash − debt − other claims'} = equity value of {fmt(result.equityValue,'number')}m. Divide by {fmt(Number(effective.shares),'number')}m shares = {fmt(result.fairValue,'number')} {inputs.currency} per share.</p>}
    </Section>
    <Section title="Scenario comparison" eyebrow="ASSUMPTIONS DRIVE VALUE"><p className="ir-source">Bear / bull change {simple ? 'FCF' : 'revenue'} growth by −/+3pp{!simple && ', terminal margin by −/+2pp'} and {rateLabel} by +/−1pp. Editing growth alone leaves the other assumptions fixed.</p><div className="ir-scenarios">{['bear','base','bull'].map(s => {const a = scenarioInputs({...inputs,model},s), r = dcf(a,quote);return <button key={s} aria-pressed={s===scenario} onClick={() => setScenario(s)}><span>{s.toUpperCase()}</span><strong>{r.error ? '—' : fmt(r.fairValue,'number')}</strong><small>{fmt(a.growth/100,'percent')} growth · {fmt(a[rateKey]/100,'percent')} {rateLabel}</small></button>;})}</div></Section>
    {!result.error && <>
      <Section title={`Sensitivity: ${rateLabel} × terminal growth`} eyebrow="VALUE PER SHARE"><div className="ir-table-scroll"><table className="ir-table ir-sensitivity"><thead><tr><th>{rateLabel} ↓ / g →</th>{[-1,-.5,0,.5,1].map(d => <th key={d}>{(Number(effective.terminalGrowth)+d).toFixed(2)}%</th>)}</tr></thead><tbody>{grid.map((r,i) => <tr key={i}><th>{r[rateKey].toFixed(2)}%</th>{r.values.map((v,j) => <td key={j} className={i===2&&j===2 ? 'ir-base-cell' : ''} style={{background: !v.error && quote && v.fairValue > quote ? '#edf6f0' : undefined}}>{v.error ? '—' : fmt(v.fairValue,'number')}</td>)}</tr>)}</tbody></table></div></Section>
      <Section title="Explicit cash flow forecast" eyebrow="STATEMENT CURRENCY · MILLIONS" action={<button onClick={() => exportCsv(`${symbol}-dcf-${model}-forecast.csv`,simple ? [['Year','FCF (m)','PV FCF (m)'],...result.forecast.map(r => [r.year,r.fcf,r.presentValue])] : [['Year','Revenue (m)','EBIT (m)','Cash tax (m)','Reinvestment (m)','FCFF (m)','PV FCFF (m)'],...result.forecast.map(r => [r.year,r.revenue,r.ebit,r.tax,r.reinvestment,r.fcff,r.presentValue])])}><ArrowDownToLine size={14}/> CSV</button>}>
        <TrendChart rows={result.forecast.map(r => ({...r,date:`Y${r.year}`}))} field={simple ? 'fcf' : 'fcff'} label={`Forecast ${simple ? 'FCF' : 'FCFF'} (m)`} bar/>
        <div className="ir-table-scroll"><table className="ir-table"><thead><tr><th>Year</th>{!simple && <><th>Revenue</th><th>EBIT margin</th><th>Cash tax</th><th>Net reinvestment</th></>}<th>{simple ? 'FCF' : 'FCFF'}</th><th>PV {simple ? 'FCF' : 'FCFF'}</th></tr></thead><tbody>{result.forecast.map(r => <tr key={r.year}><th>Y{r.year}</th>{!simple && <><td>{fmt(r.revenue,'number')}</td><td>{fmt(r.margin,'percent')}</td><td>{fmt(r.tax,'number')}</td><td>{fmt(r.reinvestment,'number')}</td></>}<td>{fmt(r[simple ? 'fcf' : 'fcff'],'number')}</td><td>{fmt(r.presentValue,'number')}</td></tr>)}</tbody></table></div>
      </Section>
    </>}
    {!simple && <details className="ir-card ir-methodology-details"><summary>Advanced methodology & limitations</summary><div className="ir-methodology"><p>FCFF = EBIT − cash tax − net reinvestment. Cash tax = max(EBIT, 0) × tax rate; no loss carryforwards are modelled. Net reinvestment = max(change in revenue, 0) / sales-to-capital ratio, covering net capex and working capital. No asset releases are assumed when revenue contracts.</p>
      <p>EBIT margins move linearly from base to target. Revenue grows at the selected rate in years 1–5, then fades linearly to terminal growth in a 10-year model. A 5-year model steps directly to stable growth. End-year discounting; the model begins after the selected annual base period, with no stub adjustment to today.</p>
      <p>Terminal FCFF = year n+1 NOPAT × (1 − g / terminal ROIC). Terminal value = terminal FCFF / (WACC − g). Equity = enterprise value + cash − debt − minority/preferred claims. Cash includes equivalents only; add other nonoperating assets manually after review.</p>
      <p>Stock compensation remains an operating expense through the EBIT margin; it is not added back. Share count is fixed. Review dilution, leases, pension deficits, investments and other claims independently. Defaults of 10% growth, 10% WACC, 25% tax, 2× sales/capital and 12% terminal ROIC are editable placeholders, not analyst estimates. Bear / bull shift base growth by −/+3pp, target margin by −/+2pp and WACC by +/−1pp. <a href="https://pages.stern.nyu.edu/~adamodar/pdfiles/country/val2daySept24.pdf" target="_blank" rel="noreferrer">FCFF methodology reference <ArrowUpRight size={12}/></a></p></div></details>}
    {simple && <p className="ir-source">End-year discounting from the displayed annual base; no stub-period adjustment. Shares stay fixed. Growth, terminal growth and discount rate are editable assumptions, not analyst estimates. <a href="https://pages.stern.nyu.edu/~adamodar/New_Home_Page/background/valintro.htm" target="_blank" rel="noreferrer">Equity cash-flow methodology <ArrowUpRight size={12}/></a></p>}
  </div></div>;
}
