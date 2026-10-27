import React, {useState} from 'react';
import {ArrowDownToLine, ArrowUpRight, BarChart3, Calculator, ChevronRight, LineChart, Star} from 'lucide-react';
import {useWatchlist} from './WatchlistContext.jsx';
import useData from './useResearchData.js';
import {download} from './browserState.js';
import {useLocalDraft} from './useLocalDraft.js';
import {Busy, Section, TrendChart, FinancialTable, MetricCard, fmt, metrics} from './ResearchUI.jsx';
import {Valuation} from './ValuationPanel.jsx';
export {Valuation} from './ValuationPanel.jsx';
export {TrendChart, FinancialTable} from './ResearchUI.jsx';

function Notes({symbol,onStatus}) {
  const key = `stock-pipeline.notes.v1.${symbol}`;
  const {value:notes, update:setNotes, save, dirty, saved} = useLocalDraft(key,{});
  return <Section title="Investment thesis" eyebrow="PRIVATE TO THIS BROWSER" action={<button onClick={() => download(`${symbol}-investment-notes.json`,JSON.stringify({symbol,...notes},null,2),'application/json')}><ArrowDownToLine size={14}/> Export notes</button>}>
    <p className="ir-description">Record the variant view, the evidence that would change your mind, and the catalysts you are watching.</p>
    <div className="ir-notes">{[['thesis','Thesis & variant perception'],['drivers','Key drivers & catalysts'],['risks','Risks & disconfirming evidence'],['questions','Questions for the next earnings call']].map(([field,label]) => <label key={field}>{label}<textarea rows={5} value={notes[field] || ''} onChange={e => setNotes(n => ({...n,[field]:e.target.value}))} placeholder={`Write your ${label.toLowerCase()}…`}/></label>)}</div>
    <button className="ir-primary" onClick={() => onStatus(save() ? 'Investment notes saved in this browser.' : 'Browser storage unavailable. Export notes to keep them.')}>Save investment notes</button>
    <p className="ir-source" role="status">{dirty ? 'Unsaved changes. Your draft is retained while you navigate.' : saved ? 'Saved in this browser.' : 'Save to keep your notes after closing the site.'}</p>
  </Section>;
}

export default function InvestorWorkspace({symbol, page = 'overview', onPage, revision = 0}) {
  const tab = page;
  const [period,setPeriod] = useState('annual');
  const [metric,setMetric] = useState('free_cash_flow'), [growth,setGrowth] = useState(false), [chartType,setChartType] = useState('bar');
  const [range,setRange] = useState('1Y');
  const {watchlist,toggleSymbol,notify} = useWatchlist();
  const base = `/stocks/${encodeURIComponent(symbol)}`;
  const company = useData(base,revision), annual = useData(base+'/research?period=annual',revision), quarter = useData(base+'/research?period=quarter',revision);
  const priceData = useData(tab === 'overview' ? base+'/prices' : null,revision);
  const earnings = useData(tab === 'earnings' ? base+'/evidence/earnings' : null,revision);
  const estimates = useData(tab === 'earnings' ? base+'/evidence/estimates' : null,revision);
  const filings = useData(tab === 'reports' ? base+'/evidence/filings' : null,revision);
  const overview = company.data?.overview || {}, active = period === 'annual' ? annual : quarter;
  const periods = active.data?.periods || [], latest = periods.filter(r => r.revenue != null).at(-1) || periods.at(-1) || {};
  const latestAnnual = annual.data?.periods?.filter(r => r.revenue != null).at(-1) || {};
  const selectedMetric = metrics.find(m => m[0]===metric) || metrics[7];
  const chartRows = periods.map(row => ({...row,chart_value:growth ? (selectedMetric[2] === 'percent' ? row.yoy_pp?.[metric] : row.yoy?.[metric]) ?? null : row[metric]}));
  const allPrices = priceData.data?.prices || [];
  const rangeDays = {'1M':31,'3M':93,'1Y':366,'3Y':1096,'5Y':1827,'10Y':3653}[range];
  const end = allPrices.at(-1)?.date;
  const priceRows = end ? allPrices.filter(r => (new Date(end)-new Date(r.date))/864e5 <= rangeDays) : [];
  const priceReturn = priceRows.length > 1 ? priceRows.at(-1).close / priceRows[0].close - 1 : null;
  const annualCurrency = latestAnnual.currency || 'Currency unknown';
  const currencies = [...new Set(periods.map(r => r.currency || 'Unknown'))];
  const mixedCurrency = currencies.length > 1;
  const starred = watchlist.includes(symbol);
  const valuationState = {
    loading:company.loading || annual.loading || quarter.loading,
    // Seed a new model only after the quarterly bridge request has settled.
    data:company.data && annual.data && (quarter.data || quarter.error) ? annual.data : null,
    error:[company.error, annual.error, quarter.error].filter(Boolean).join(' '),
  };
  return (
      <div className="ir-content"><div className="ir-breadcrumb">RESEARCH <ChevronRight size={12}/>{overview.Sector || 'COMPANY'}<ChevronRight size={12}/>{symbol}</div>
        <div className="ir-company-heading"><div className="ir-company-identity"><span className="ir-company-monogram">{symbol.slice(0,2)}</span><div><div className="ir-title-row"><h1>{overview.Name || symbol}</h1><button aria-label={starred ? 'Remove company from watchlist' : 'Add company to watchlist'} aria-pressed={starred} onClick={() => toggleSymbol(symbol)}><Star size={18} fill={starred ? 'currentColor' : 'none'}/></button></div><p>{symbol} <span>·</span> {overview.ExchangeShortName || overview.Exchange || 'Exchange unavailable'} <span>·</span> {overview.Industry || overview.Sector || 'Company research'}</p></div></div>
          <div className="ir-quote"><strong>{fmt(overview.Price,'number')} <small>{overview.Currency || 'Currency unknown'}</small></strong><span className={Number(overview.ChangesPercentage)>=0 ? 'ir-positive' : 'ir-negative'}>{fmt(overview.Change,'number')} ({fmt(overview.ChangesPercentage === '' || overview.ChangesPercentage == null ? null : Number(overview.ChangesPercentage)/100,'change')})</span><small>{overview.QuoteTimestamp ? `Quote ${new Date(Number(overview.QuoteTimestamp)*1000).toLocaleString('en-GB')}` : 'Quote timestamp unavailable'}</small></div>
        </div>
        <Busy state={company}>{!company.loading && !company.error && !overview.Name && <p className="ir-warning">No company profile available for {symbol}. Check the ticker and FMP coverage.</p>}</Busy>
        {(tab === 'overview' || tab === 'financials') && <><div className="ir-page-intro"><div><h2>{tab === 'overview' ? 'Company overview' : 'Financial history'}</h2><p>{latest.date ? `${period === 'annual' ? 'Annual' : 'Quarterly'} reporting · period ended ${latest.date} · ${latest.currency || 'Currency unknown'}` : 'Reported fundamentals, with gaps kept visible.'}</p></div><div className="ir-segment" aria-label="Reporting frequency"><button aria-pressed={period==='annual'} onClick={()=>setPeriod('annual')}>Annual</button><button aria-pressed={period==='quarter'} onClick={()=>setPeriod('quarter')}>Quarterly</button></div></div>
          <Busy state={active}><>{active.data?.missing?.length > 0 && <p className="ir-warning">Unavailable statements: {active.data.missing.join(', ')}. Your FMP plan or company coverage may limit availability.</p>}{active.data?.warnings?.map((warning,i)=><p key={i} className="ir-warning">{warning}</p>)}
            <div className="ir-kpi-grid"><MetricCard label="Revenue" value={latest.revenue} change={latest.yoy?.revenue} note="Reported period"/><MetricCard label="Free cash flow" value={latest.free_cash_flow} change={latest.yoy?.free_cash_flow} note="Operating cash flow − capex"/><MetricCard label="Operating margin" value={latest.operating_income_margin} kind="percent" note="EBIT / revenue"/><MetricCard label="Diluted EPS" value={latest.eps} kind="number" change={latest.yoy?.eps} note="Reported period"/></div>
            <Section title="Operating performance" eyebrow="FUNDAMENTALS OVER TIME" action={<div className="ir-chart-controls"><select aria-label="Chart metric" value={metric} onChange={e=>{setMetric(e.target.value);setGrowth(false);}}>{metrics.map(([key,label])=><option value={key} key={key}>{label}</option>)}</select><button aria-pressed={growth} onClick={()=>setGrowth(v=>!v)}>YoY change</button><button aria-label="Toggle line or bar chart" onClick={()=>setChartType(t=>t==='bar' ? 'line' : 'bar')}>{chartType==='bar' ? <LineChart size={16}/> : <BarChart3 size={16}/>}</button></div>}>
              <p className="ir-source">{currencies.join(', ')} · {growth ? selectedMetric[2] === 'percent' ? 'Change in percentage points from the same fiscal period a year earlier.' : 'Same fiscal period a year earlier; unavailable for nonpositive prior bases.' : 'Reported values. Hover for period details.'}</p>
              {mixedCurrency ? <div className="ir-warning">Reporting currencies changed across periods. Use the financial table to inspect individual periods; combined charts are withheld.</div> : <TrendChart rows={chartRows} field="chart_value" label={selectedMetric[1]+(growth ? ' · YoY change' : '')} kind={growth ? selectedMetric[2] === 'percent' ? 'pp' : 'change' : selectedMetric[2] || 'compact'} bar={chartType==='bar'}/>}
              <p className="ir-source">{active.data?.methodology}</p>
            </Section>
            {tab === 'financials' && <Section title="Financial statements" eyebrow="SOURCE DATA & YEAR-ON-YEAR CHANGE"><FinancialTable data={active.data} symbol={symbol}/><p className="ir-source">Values retain vendor reporting conventions. Capex is shown as an outflow magnitude; dividend and buyback signs follow the source. FCF is distinct from the modelled FCFF in DCF valuation.</p></Section>}
          </></Busy>
        </>}
        {tab === 'overview' && <>
          <Section title="Price history" eyebrow="MARKET PERFORMANCE" action={<div className="ir-segment">{['1M','3M','1Y','3Y','5Y','10Y'].map(r=><button key={r} aria-pressed={r===range} onClick={()=>setRange(r)}>{r}</button>)}</div>}>
            <Busy state={priceData}><><p className="ir-price-return"><strong className={priceReturn>=0 ? 'ir-positive' : 'ir-negative'}>{fmt(priceReturn,'change')}</strong> price return · {priceRows[0]?.date || '—'} to {end || '—'} · {overview.Currency || 'Currency unknown'}</p><TrendChart rows={priceRows} field="close" label="Daily close" kind="number"/><p className="ir-source">{priceData.data?.source}. Based on available closes; quote may be newer.</p></></Busy>
          </Section>
          <div className="ir-two-column"><Section title="Valuation & capital structure" eyebrow="MARKET SNAPSHOT"><dl className="ir-facts">{[['Market capitalisation',overview.MarketCapitalization],['Trailing P/E',overview.PERatio,'multiple'],['Price / book',overview.PriceToBookRatio,'multiple'],['Price / sales',overview.PriceToSalesRatio,'multiple'],['52-week high',overview['52WeekHigh'],'number'],['52-week low',overview['52WeekLow'],'number'],['Annual FCF yield',overview.FreeCashFlowYield,'percent']].map(([label,value,kind])=><div key={label}><dt>{label}</dt><dd>{fmt(value,kind)}</dd></div>)}</dl><p className="ir-source">Quote / statement currencies may differ. Provider key-metric period: {overview.FinancialPeriod || 'unknown'}; ratios period: {overview.RatiosPeriod || 'unknown'}. Annual ratios are not necessarily TTM.</p></Section>
          <Section title="Company profile" eyebrow="BUSINESS CONTEXT"><p className="ir-company-description">{overview.Description || 'Company description unavailable.'}</p><div className="ir-research-cta"><Calculator size={22}/><div><strong>Build your own valuation</strong><p>Underwrite growth, reinvestment and return expectations.</p></div><button onClick={()=>onPage('valuation')} aria-label="Open DCF valuation"><ArrowUpRight size={18}/></button></div></Section></div>
        </>}
        {tab === 'valuation' && <><div className="ir-page-intro"><div><h2>DCF valuation</h2><p>Annual operating base in {annualCurrency}. Latest available quarterly balance sheet seeds the equity bridge.</p></div></div>{/financial|bank|insurance|reit/i.test(`${overview.Sector} ${overview.Industry}`) && <p className="ir-warning">This operating-company FCFF model is not designed for banks, insurers or REITs. Their financial history is available; use a sector-specific valuation outside this model.</p>}<Busy state={valuationState}>{valuationState.data && <Valuation key={symbol} symbol={symbol} annual={annual.data} quarter={quarter.data} overview={overview} quoteCurrency={overview.Currency} onStatus={notify}/>}</Busy></>}
        {tab === 'earnings' && <>
          <div className="ir-page-intro"><div><h2>Earnings & expectations</h2><p>Reported results against consensus, and the forward estimates behind market expectations.</p></div></div>
          <Section title="Earnings report history" eyebrow="ACTUAL VS CONSENSUS"><Busy state={earnings}>{earnings.data?.rows?.length ? <div className="ir-table-scroll"><table className="ir-table"><thead><tr><th>Report date</th><th>EPS actual</th><th>EPS estimate</th><th>EPS surprise</th><th>Revenue actual</th><th>Revenue estimate</th><th>Revenue surprise</th></tr></thead><tbody>{earnings.data.rows.map((r,i)=><tr key={r.date+i}><th>{r.date}{r.eps_actual==null && r.revenue_actual==null && <small>Actuals unavailable / scheduled</small>}</th><td>{fmt(r.eps_actual,'number')}</td><td>{fmt(r.eps_estimate,'number')}</td><td className={r.eps_surprise>=0 ? 'ir-positive' : 'ir-negative'}>{fmt(r.eps_surprise,'change')}</td><td>{fmt(r.revenue_actual)}</td><td>{fmt(r.revenue_estimate)}</td><td className={r.revenue_surprise>=0 ? 'ir-positive' : 'ir-negative'}>{fmt(r.revenue_surprise,'change')}</td></tr>)}</tbody></table></div> : <p className="ir-empty">{earnings.data?.message || 'No earnings reports available from FMP.'}</p>}</Busy><p className="ir-source">FMP earnings endpoint reports trading-currency values. Surprise = (actual − estimate) / |estimate|; zero estimates remain unavailable. Vendor EPS definitions may differ from reported diluted EPS.</p></Section>
          <Section title="Analyst consensus" eyebrow="ANNUAL ESTIMATES · NOT COMPANY GUIDANCE"><Busy state={estimates}>{estimates.data?.rows?.length ? <><TrendChart rows={[...estimates.data.rows].reverse()} field="revenue_avg" label="Consensus annual revenue"/><div className="ir-table-scroll"><table className="ir-table"><thead><tr><th>Fiscal period</th><th>Revenue low</th><th>Revenue mean</th><th>Revenue high</th><th>EPS low</th><th>EPS mean</th><th>EPS high</th><th>Revenue analysts</th></tr></thead><tbody>{estimates.data.rows.map((r,i)=><tr key={r.date+i}><th>{r.date}</th>{['revenue_low','revenue_avg','revenue_high','eps_low','eps_avg','eps_high','analysts'].map(k=><td key={k}>{fmt(r[k],k.startsWith('revenue') ? 'compact' : 'number')}</td>)}</tr>)}</tbody></table></div></> : <p className="ir-empty">{estimates.data?.message || 'No analyst estimates available from FMP.'}</p>}</Busy><p className="ir-source">Source: FMP analyst estimates. Currency is not provided by this endpoint; compare against financials only after verifying the currency. Consensus includes available fiscal periods and may be revised.</p></Section>
        </>}
        {tab === 'reports' && <><div className="ir-page-intro"><div><h2>Reports & news</h2><p>Regulatory reports and recent company news, with direct links to the source.</p></div></div><div className="ir-two-column">
          <Section title="Regulatory filings" eyebrow="SEC · LAST TWO YEARS · UP TO 100"><Busy state={filings}>{filings.data?.rows?.length ? <div className="ir-filings">{filings.data.rows.map((r,i)=><div key={r.date+i}><span className="ir-form-type">{r.form}</span><div><strong>{r.form === '10-K' ? 'Annual report' : r.form === '10-Q' ? 'Quarterly report' : r.form === '8-K' ? 'Current report' : 'Regulatory filing'}</strong><small>{r.date}</small></div>{r.url && <a href={r.url} target="_blank" rel="noreferrer" aria-label={`Read ${r.form} filed ${r.date}`}><ArrowUpRight size={18}/></a>}</div>)}</div> : <p className="ir-empty">{filings.data?.message || 'No SEC filings available. Non-US companies may report through other regulators.'}</p>}</Busy></Section>
          <Section title="Recent company news" eyebrow="FMP NEWS FEED"><Busy state={company}>{company.data?.news?.length ? <div className="ir-news">{company.data.news.map((r,i)=><article key={i}><span>{r.publisher || 'Publisher unavailable'} · {r.published_at || 'Date unavailable'}</span><h3>{r.title}</h3>{r.summary && <p>{r.summary}</p>}{r.url && <a href={r.url} target="_blank" rel="noreferrer">Read article <ArrowUpRight size={14}/></a>}</article>)}</div> : <p className="ir-empty">No recent news available from FMP.</p>}</Busy></Section>
        </div></>}
        {tab === 'notes' && <Notes key={symbol} symbol={symbol} onStatus={notify}/>}
        <div className="ir-data-footer"><span><i/> FMP · {symbol} · {annual.data?.periods?.length || 0} annual periods available</span><span>Data may be cached · financial statements up to 24h · news 30m · earnings / filings 1h</span></div>
      </div>
  );
}
