import React, {useEffect, useState} from 'react';
import {Activity, ArrowUpRight, BarChart3, Building2, Calculator, ChevronRight, FileText, GitBranch, LineChart, RefreshCw, Search, X} from 'lucide-react';
import {researchHref, researchPages} from './navigation.js';
import {cleanSymbols} from './watchlist.js';
import {useWatchlist} from './WatchlistContext.jsx';

const pageIcons = {overview:Activity, financials:BarChart3, valuation:Calculator,
  earnings:LineChart, reports:FileText, notes:FileText};

export default function WorkspaceShell({route, onSymbol, onPage, onReload, children}) {
  const {symbol, page, screening} = route;
  const [query, setQuery] = useState(symbol);
  const {watchlist, removeSymbol, notify, status, dismissStatus} = useWatchlist();
  useEffect(() => {setQuery(symbol);}, [symbol]);

  function search(event) {
    event.preventDefault();
    const valid = cleanSymbols([query])[0];
    if (valid) {setQuery(valid);onSymbol(valid);}
    else notify('Enter an exchange ticker, for example AAPL or SHOP.TO.');
  }

  return <div className="investor-app">
    <aside className="ir-sidebar">
      <a className="ir-brand" href={researchHref(symbol)}><span><GitBranch size={23}/></span>stock<span>pipeline</span></a>
      <div className="ir-workspace-tag"><i/> INVESTOR WORKSPACE</div>
      <span className="ir-sidebar-label">WORKSPACE</span>
      <nav aria-label="Workspace navigation">
        {researchPages.map(([id, label]) => {
          const Icon = pageIcons[id], active = !screening && page === id;
          return <a key={id} href={researchHref(symbol, id)} aria-current={active ? 'page' : undefined} title={label}>
            <Icon size={17}/>{label}{active && <ChevronRight size={14}/>}
          </a>;
        })}
        <a href="#screening" aria-current={screening ? 'page' : undefined} title="Screening workflow">
          <GitBranch size={17}/>Screening workflow{screening && <ChevronRight size={14}/>}
        </a>
      </nav>
      <div className="ir-watch-heading"><span className="ir-sidebar-label">WATCHLIST</span><span>{watchlist.length}</span></div>
      <div className="ir-watchlist" aria-label="Your watchlist">
        {watchlist.map(ticker => <div key={ticker} className={!screening && ticker === symbol ? 'active' : ''}>
          <button aria-label={`Research ${ticker}`} onClick={() => onSymbol(ticker)}><span className="ir-ticker-icon">{ticker[0]}</span>{ticker}</button>
          <button aria-label={`Remove ${ticker} from watchlist`} onClick={() => removeSymbol(ticker)}><X size={12}/></button>
        </div>)}
        {!watchlist.length && <p>Add stocks from screening results or star a company in research.</p>}
      </div>
      <div className="ir-sidebar-bottom"><Building2 size={19}/><div>Local research workspace<small>FMP data · your assumptions</small></div></div>
    </aside>
    <main className="ir-main">
      <header className="ir-topbar">
        <form onSubmit={search}><Search size={17}/><input aria-label="Company ticker" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search ticker, e.g. AAPL" autoComplete="off"/><button type="submit">Research <ArrowUpRight size={13}/></button></form>
        <span className="ir-topbar-source"><i/> FMP RESEARCH DATA</span>
        {!screening && <button aria-label="Reload data" title="Reload data (provider cache still applies)" onClick={onReload}><RefreshCw size={15}/></button>}
      </header>
      <div className="ir-mobile-tools">
        <select aria-label="Workspace page" value={screening ? 'screening' : page} onChange={e => onPage(e.target.value)}>
          {researchPages.map(([id, label]) => <option key={id} value={id}>{label}</option>)}<option value="screening">Screening workflow</option>
        </select>
        <select aria-label="Open watchlist company" value="" onChange={e => {if (e.target.value) onSymbol(e.target.value);}}>
          <option value="">Watchlist ({watchlist.length})</option>{watchlist.map(ticker => <option key={ticker} value={ticker}>{ticker}</option>)}
        </select>
      </div>
      {children}
    </main>
    {status && <div className="ir-toast" role="status">{status}<button aria-label="Dismiss notification" onClick={dismissStatus}><X size={14}/></button></div>}
  </div>;
}
