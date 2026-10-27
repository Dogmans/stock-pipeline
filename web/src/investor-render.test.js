// Server rendering checks work without launching or controlling a browser.
import {before,after,test} from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {createServer} from 'vite';
import {workspaceRoute} from './navigation.js';

let server, ui, watchlistUi, appUi, draftUi, valuationUi, profitabilityUi;
before(async () => {
  server = await createServer({configFile:false,appType:'custom',server:{middlewareMode:true,hmr:false,watch:null},
    optimizeDeps:{noDiscovery:true,include:[]}});
  ui = await server.ssrLoadModule('/src/InvestorWorkspace.jsx');
  watchlistUi = await server.ssrLoadModule('/src/WatchlistContext.jsx');
  appUi = await server.ssrLoadModule('/src/App.jsx');
  draftUi = await server.ssrLoadModule('/src/useLocalDraft.js');
  valuationUi = await server.ssrLoadModule('/src/ValuationPanel.jsx');
  profitabilityUi = await server.ssrLoadModule('/src/ProfitabilityPanel.jsx');
});

test('unsaved model and note drafts survive remounts and remain separate for each company', () => {
  function Draft({draftKey, initial, change}) {
    const draft=draftUi.useLocalDraft(draftKey,initial);
    const applied=React.useRef(false);
    if (change && !applied.current) {applied.current=true;draft.update(change);}
    return React.createElement('output',null,JSON.stringify({value:draft.value,dirty:draft.dirty}));
  }
  const render=props => renderToStaticMarkup(React.createElement(Draft,props));
  render({draftKey:'test:model:A',initial:{growth:10},change:{growth:7}});
  const model=render({draftKey:'test:model:A',initial:{growth:99}});
  assert.ok(model.includes('&quot;growth&quot;:7'));
  assert.ok(model.includes('&quot;dirty&quot;:true'));
  assert.ok(render({draftKey:'test:model:B',initial:{growth:10}}).includes('&quot;growth&quot;:10'));
  render({draftKey:'test:notes:A',initial:{thesis:''},change:{thesis:'Evidence to revisit'}});
  assert.ok(render({draftKey:'test:notes:A',initial:{thesis:''}}).includes('Evidence to revisit'));
});
after(async () => {await server?.close();});

const annual = {period:'annual',periods:[{date:'2025-12-31',fiscal_period:'FY',currency:'USD',revenue:100e6,
  operating_income:20e6,free_cash_flow:15e6,cash:20e6,debt:30e6,minority_interest:0,preferred_stock:0,
  diluted_shares:10e6,sources:{income:{filed_at:'2026-02-01'}}}]};

test('company workspace renders its navigation, loading states and mobile screening access', () => {
  const html=renderToStaticMarkup(React.createElement(watchlistUi.WatchlistProvider,null,
    React.createElement(appUi.default,{initialHash:'#research/AAPL'})));
  for (const text of ['Company ticker','Financials','DCF valuation','Earnings &amp; estimates','Reports &amp; news',
    'Open watchlist company','Screening workflow','Loading source data']) assert.ok(html.includes(text),text);
});

test('screener uses the shared navigation, search and watchlist with an active screening entry', () => {
  const html=renderToStaticMarkup(React.createElement(watchlistUi.WatchlistProvider,null,
    React.createElement(appUi.default,{initialHash:'#screening'})));
  assert.equal((html.match(/class="ir-sidebar"/g) || []).length,1);
  assert.ok(html.includes('aria-label="Company ticker"'));
  assert.ok(html.includes('aria-label="Your watchlist"'));
  assert.ok(html.includes('aria-label="Workspace page"'));
  assert.ok(html.includes('aria-label="Research MSFT"'));
  assert.ok(/<a href="#screening" aria-current="page"/.test(html));
  assert.ok(html.includes('aria-label="Screening workspace"'));
  assert.ok(!html.includes('role="tablist" aria-label="Company research"'));
});

test('switching to research keeps the screener subtree mounted and hides its page', () => {
  const route=workspaceRoute('#research/MSFT/financials',workspaceRoute('#screening'));
  const html=renderToStaticMarkup(React.createElement(watchlistUi.WatchlistProvider,null,
    React.createElement(appUi.WorkspacePages,{route,onPage(){}})));
  assert.ok(/class="ir-screening-page" hidden="">[\s\S]*?aria-label="Screening workspace"/.test(html));
  assert.ok(html.includes('aria-label="Workflow name"'));
});

test('long price histories use an auto-scaled line and one pointer surface', () => {
  const rows=Array.from({length:2500},(_,i) => ({date:`D${i}`,close:100 + i/2500}));
  const line=renderToStaticMarkup(React.createElement(ui.TrendChart,{rows,field:'close',label:'Daily close'}));
  assert.ok(!/<text[^>]*>0<\/text>/.test(line));
  assert.ok((line.match(/<rect /g) || []).length <= 2);
  const bars=renderToStaticMarkup(React.createElement(ui.TrendChart,{rows:rows.slice(0,3),field:'close',label:'Cash flow',bar:true}));
  assert.ok(/<text[^>]*>0<\/text>/.test(bars));
});

test('financial margin changes use percentage points in the statement table', () => {
  const data={...annual,periods:[{...annual.periods[0],operating_income_margin:.2,yoy_pp:{operating_income_margin:.1}}]};
  const html=renderToStaticMarkup(React.createElement(ui.FinancialTable,{data,symbol:'ABC'}));
  assert.ok(html.includes('+10.0pp YoY'));
});

test('watchlist controls show the same saved and unsaved states used by company research', () => {
  const html=renderToStaticMarkup(React.createElement(watchlistUi.WatchlistProvider,null,
    React.createElement(React.Fragment,null,
      React.createElement(watchlistUi.WatchlistButton,{symbol:'AAPL',showLabel:true}),
      React.createElement(watchlistUi.WatchlistButton,{symbol:'NEAR'}))));
  assert.ok(html.includes('aria-label="Remove AAPL from watchlist"'));
  assert.ok(html.includes('aria-pressed="true"'));
  assert.ok(html.includes('On watchlist'));
  assert.ok(html.includes('aria-label="Add NEAR to watchlist"'));
  assert.ok(html.includes('aria-pressed="false"'));
});

test('valuation defaults to direct FCF with explanation, scenarios, sensitivity and forecast', () => {
  const html=renderToStaticMarkup(React.createElement(ui.Valuation,{symbol:'ABC',annual,quarter:null,
    overview:{Price:10,Currency:'USD',SharesOutstanding:10e6},quoteCurrency:'USD',onStatus(){}}));
  for (const text of ['data-testid="fair-value"','Intrinsic value','Sensitivity: Discount rate','Explicit cash flow forecast',
    'Starting free cash flow','Equity value','Current shares outstanding','How this DCF works','FCF(t) = starting FCF',
    'DCF model','Advanced DCF','No additional reinvestment is deducted']) assert.ok(html.includes(text),text);
  assert.ok(!html.includes('Base revenue (m)'));
  assert.ok(!html.includes('Terminal ROIC'));
  assert.ok(!html.includes('Complete every model input'));
  assert.ok(!html.includes('>NaN<'));
  assert.ok(!html.includes('+1pp revenue growth lowers value'));
});

test('valuation explains when extra revenue growth reduces value under the selected assumptions', () => {
  const lowMargin = {...annual,periods:[{...annual.periods[0],operating_income:5e6}]};
  const html=renderToStaticMarkup(React.createElement(valuationUi.ValuationModel,{model:'advanced',symbol:'LOW-MARGIN',annual:lowMargin,quarter:null,
    overview:{Price:10,Currency:'USD',SharesOutstanding:10e6},quoteCurrency:'USD',onStatus(){}}));
  assert.ok(html.includes('+1pp revenue growth lowers value'));
  assert.ok(html.includes('USD per share. Extra sales require investment'));
  assert.ok(html.includes('Incremental sales / capital'));
  assert.ok(html.includes('FCFF = EBIT'));
  assert.ok(html.includes('Terminal ROIC'));
});

test('cross-currency valuation withholds upside and incomplete source inputs explain what is missing', () => {
  const props={symbol:'ABC',annual,quarter:null,overview:{Price:10,SharesOutstanding:10e6},quoteCurrency:'CAD',onStatus(){}};
  const html=renderToStaticMarkup(React.createElement(ui.Valuation,props));
  assert.ok(html.includes('upside is withheld'));
  const missing=renderToStaticMarkup(React.createElement(ui.Valuation,{...props,annual:{periods:[]}}));
  assert.ok(missing.includes('Complete every model input'));
  assert.ok(!missing.includes('data-testid="fair-value"'));
});

test('financial table renders units and filing dates and a sparse chart retains its gaps', () => {
  const html=renderToStaticMarkup(React.createElement(ui.FinancialTable,{data:annual,symbol:'ABC'}));
  assert.ok(html.includes('Filed 2026-02-01'));
  assert.ok(html.includes('money and share counts in millions'));
  const chart=renderToStaticMarkup(React.createElement(ui.TrendChart,{rows:[{date:'2023',fcf:10},{date:'2024',fcf:null},
    {date:'2025',fcf:15}],field:'fcf',label:'Free cash flow'}));
  assert.ok(chart.includes('2 observations'));
  assert.ok(chart.includes('M65,'));
  assert.ok(!chart.includes('L412.5,'));
});


test('profitability renders the four traits, percentage-point changes and missing-data explanations', () => {
  const latest = {date:'2025-12-31',currency:'USD',roe:.2,roa:.128,roce:.4,roe_3y_ago:.1,roe_change_3y:.1,
    comparison_date:'2022-12-31'};
  const html = renderToStaticMarkup(React.createElement(profitabilityUi.default,{symbol:'ABC',data:{latest,history:[latest]}}));
  for (const text of ['TTM return on equity (ROE)','TTM return on assets (ROA)','TTM return on capital employed (ROCE)',
    'ROE change over three years','+10.0pp','2022-12-31','Export profitability CSV','Profitability chart metric']) assert.ok(html.includes(text),text);
  assert.equal((html.match(/Pass<\/small>/g) || []).length,4);
  const missing = renderToStaticMarkup(React.createElement(profitabilityUi.default,{symbol:'ABC',data:{latest:{reasons:{roe:'Missing equity.'}},history:[]}}));
  assert.ok(missing.includes('Missing equity.'));
  assert.ok(missing.includes('Unavailable'));
  assert.ok(!missing.includes('NaN'));
});
