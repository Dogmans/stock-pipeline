// Capture the real built UI with deterministic, explicitly labelled demo data.
// Run from web/: node scripts/capture-readme.mjs (requires a Playwright browser).
import {createServer} from 'node:http';
import {readFile, mkdir} from 'node:fs/promises';
import {resolve, sep, extname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from '@playwright/test';

const build = fileURLToPath(new URL('../dist/',import.meta.url));
const imageDirectory = fileURLToPath(new URL('../../docs/images/',import.meta.url));
const workflow = JSON.parse(await readFile(new URL('../../workflows/value_quality.json',import.meta.url),'utf8'));
workflow.name = 'Quality at a fair price · Demo data';
const names = ['Apple','Microsoft','Alphabet','Amazon','Meta Platforms','Johnson & Johnson','JPMorgan Chase','Exxon Mobil'];
const quality = [8.2,9,8.6,7.5,8.1,7.8,6.8,6.6];
const pe = [28,30,18,35,19,15];
const sectors = ['Technology','Technology','Communication Services','Consumer Cyclical','Communication Services','Healthcare','Financial Services','Energy'];
const stocks = workflow.universe.symbols.map((symbol,i) => ({symbol,company_name:names[i],sector:sectors[i],score:quality[i],reason:`Quality ${quality[i]} ≥ 7: ${quality[i]>=7?'pass':'fail'}`}));
const valued = stocks.slice(0,6).map((row,i) => ({...row,score:pe[i],reason:`P/E ${pe[i]} ≤ 20: ${pe[i]<=20?'pass':'fail'}`}));
const shortlist = valued.filter(row => row.score<=20);
const outcomes = (passed,failed=[],rule=null) => ({input_count:passed.length+failed.length,rule,
  outcomes:{passed,failed,unavailable:[],error:[]},counts:{passed:passed.length,failed:failed.length,unavailable:0,error:0}});
const result = {snapshot_id:'demo',snapshot_created_at:'2026-09-12T09:00:00Z',nodes:{
  universe:outcomes(stocks),quality:outcomes(stocks.slice(0,6),stocks.slice(6),{metric:'Quality score',operator:'gte',value:7,field:'score'}),
  value:outcomes(shortlist,valued.filter(row => row.score>20),{metric:'Score',operator:'lte',value:20,field:'score'}),shortlist:outcomes(shortlist)},
  edges:Object.fromEntries(workflow.edges.map((edge,i) => [edge.id,{count:[8,6,3][i]}])),shortlist};
const catalog = [
  ['pe_ratio','P/E Ratio'],['price_to_book','Price to Book'],['peg_ratio','PEG Ratio'],['quality','Quality'],
  ['enhanced_quality','Enhanced Quality'],['fcf_yield','Free Cash Flow Yield'],['historic_value','Historic Value'],
  ['momentum','Momentum'],['sharpe_ratio','Sharpe Ratio'],['fifty_two_week_lows','52-Week Lows'],
  ['insider_buying','Insider Buying'],['analyst_sentiment_momentum','Analyst Sentiment Momentum'],['composite_score','Composite Score'],
].map(([id,label]) => ({id,label,description:label,parameters:[],default_rule:id==='quality' ? {metric:'Quality score',operator:'gte',value:7} : id==='pe_ratio' ? {metric:'P/E',operator:'lte',value:15} : null}));
const record = {id:'abc',saved_at:'2026-09-12T09:01:00Z',workflow,result};
const server = createServer(async (request,response) => {
  try {
    const path = decodeURIComponent(new URL(request.url,'http://localhost').pathname);
    const target = resolve(build,'.'+(path==='/'?'/index.html':path));
    if (!target.startsWith(resolve(build)+sep)) {response.writeHead(403).end();return;}
    const bytes = await readFile(target);
    response.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[extname(target)] || 'application/octet-stream');
    response.end(bytes);
  } catch {response.writeHead(404).end();}
});
await new Promise(done => server.listen(0,'127.0.0.1',done));
let browser;
try {
  browser = await chromium.launch({channel:process.env.STOCK_UI_BROWSER_CHANNEL || undefined});
  const page = await browser.newPage({viewport:{width:1600,height:1100},deviceScaleFactor:1});
  await page.route('**/api/**',async route => {
    const path = new URL(route.request().url()).pathname;
    const body = path==='/api/screeners' ? catalog : path==='/api/history' ? [{id:record.id,saved_at:record.saved_at,name:workflow.name}] : path==='/api/history/abc' ? record : null;
    if (body===null) throw new Error(`Unexpected request: ${path}`);
    await route.fulfill({json:body});
  });
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  await page.getByRole('button',{name:'Saved runs',exact:true}).click();
  await page.getByRole('button',{name:'Open run',exact:true}).click();
  await page.getByRole('button',{name:'Rank',exact:true}).click();
  await page.getByRole('columnheader',{name:'Rank / 100'}).waitFor();
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(350); // Allow React Flow's fit-view transition to finish.
  await mkdir(imageDirectory,{recursive:true});
  await page.screenshot({path:resolve(imageDirectory,'workflow-editor.png'),fullPage:true});
  console.log('Captured docs/images/workflow-editor.png using demo data.');
} finally {
  await browser?.close();
  await new Promise(done => server.close(done));
}
