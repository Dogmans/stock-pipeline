// Deterministic illustrative figures for screenshots and browser tests, never live data.
export const demoSymbol = 'AAPL';
export const demoQuote = 152.4;
export const demoQuarterCash = 41000; // Statement-currency millions.
const billion = 1e9;

function period(year, revenue, fcf, fiscalPeriod = 'FY', date = `${year}-09-30`) {
  const row = {date, currency:'USD', fiscal_period:fiscalPeriod,
    revenue:revenue*billion, gross_profit:revenue*.48*billion, operating_income:revenue*.32*billion,
    ebitda:revenue*.35*billion, net_income:revenue*.27*billion, eps:revenue*.27/15,
    diluted_shares:15*billion, operating_cash_flow:(fcf+12)*billion, capex:12*billion,
    free_cash_flow:fcf*billion, fcf_per_share:fcf/15, stock_compensation:12*billion,
    cash:35*billion, debt:90*billion, net_debt:55*billion, equity:75*billion, assets:360*billion,
    current_assets:150*billion, current_liabilities:145*billion, minority_interest:0, preferred_stock:0,
    gross_profit_margin:.48, operating_income_margin:.32, net_income_margin:.27,
    free_cash_flow_margin:fcf/revenue, cash_conversion:fcf/(revenue*.27), current_ratio:150/145,
    dividends:-15*billion, buybacks:-80*billion, sources:{}, yoy:{}, yoy_pp:{}};
  const filed=new Date(`${date}T00:00:00Z`);filed.setUTCDate(filed.getUTCDate()+32);
  for (const kind of ['income','balance','cash_flow']) row.sources[kind] = {currency:'USD',filed_at:filed.toISOString().slice(0,10),url:null};
  return row;
}

const revenues = [215,229,266,260,274,366,394,383,391,416];
const cashFlows = [52,50,64,59,73,93,101,95,98,108];
const annualRows = revenues.map((value,i) => period(2016+i,value,cashFlows[i]));
for (let i=1;i<annualRows.length;i++) {
  const row=annualRows[i], prior=annualRows[i-1];
  for (const metric of ['revenue','gross_profit','operating_income','net_income','eps','free_cash_flow','fcf_per_share'])
    row.yoy[metric]=row[metric]/prior[metric]-1;
  row.yoy_pp.free_cash_flow_margin=row.free_cash_flow_margin-prior.free_cash_flow_margin;
}
const quarterRows = Array.from({length:8},(_,i) => {
  const year=2024+Math.floor((i+2)/4), quarter=(i+2)%4+1;
  const month=String(quarter*3).padStart(2,'0');
  const row=period(year,95+i*2,22+i*1.2,`Q${quarter}`,`${year}-${month}-28`);
  row.cash=(34+i)*billion;row.debt=83*billion;row.net_debt=row.debt-row.cash;
  if (i>=4) row.yoy={revenue:row.revenue/((95+(i-4)*2)*billion)-1,free_cash_flow:row.free_cash_flow/((22+(i-4)*1.2)*billion)-1};
  return row;
});
const history = (rows,period) => ({symbol:demoSymbol,period,periods:rows,missing:[],warnings:[],
  source:'Illustrative demo financial statements',retrieved_at:'2026-10-27T09:00:00Z',
  methodology:'Demo figures only. FCF = operating cash flow less capex. Changes compare the same fiscal period a year earlier.'});
export const demoAnnual = history(annualRows,'annual');
export const demoQuarter = history(quarterRows,'quarter');
export const demoCompany = {symbol:demoSymbol,overview:{
  Name:'Apple Inc. - Demo data',Symbol:demoSymbol,Sector:'Technology',Industry:'Consumer electronics',
  ExchangeShortName:'NASDAQ',Currency:'USD',Price:demoQuote,Change:1.82,ChangesPercentage:1.21,
  QuoteTimestamp:1793030400,OverviewFetchedAt:'2026-10-27T09:00:00Z',FinancialPeriod:'2025-09-30',RatiosPeriod:'2025-09-30',
  MarketCapitalization:demoQuote*14.8*billion,SharesOutstanding:14.8*billion,PERatio:21.4,
  EPS:7.12,PriceToBookRatio:28.3,PriceToSalesRatio:5.4,FreeCashFlowYield:.048,
  '52WeekHigh':176.5,'52WeekLow':118.2,
  Description:'Illustrative company research for the Stock Pipeline demo. Explore cash generation, operating performance and valuation assumptions in a single workspace. Figures shown here are synthetic and are not current market results.',
},news:[{title:'Demo research brief: cash generation and capital allocation',publisher:'Illustrative research',published_at:'2026-10-26',summary:'Example news item for the documentation screenshots. Open a real ticker with your configured FMP connection to load company news.',url:null}]};

const dates=[];
for (let date=new Date('2025-05-01T00:00:00Z');date<=new Date('2026-10-26T00:00:00Z');date.setUTCDate(date.getUTCDate()+1))
  if (![0,6].includes(date.getUTCDay())) dates.push(date.toISOString().slice(0,10));
const values=dates.map((_,i) => 115+i*.095+Math.sin(i/18)*9+Math.cos(i/43)*6);
const scale=demoQuote/values.at(-1);
export const demoPrices={symbol:demoSymbol,prices:dates.map((date,i)=>({date,close:values[i]*scale,volume:42000000})),
  source:'Illustrative demo daily closes; excludes dividends',missing:false};
export const demoEarnings={source:'Illustrative demo earnings',rows:[
  {date:'2026-11-02',eps_actual:null,eps_estimate:2.1,revenue_actual:null,revenue_estimate:115*billion,eps_surprise:null,revenue_surprise:null},
  {date:'2026-07-30',eps_actual:2.02,eps_estimate:1.95,revenue_actual:109*billion,revenue_estimate:106*billion,eps_surprise:2.02/1.95-1,revenue_surprise:109/106-1},
],missing:false};
export const demoEstimates={source:'Illustrative demo analyst estimates',rows:Array.from({length:4},(_,i)=>({date:`${2026+i}-09-30`,
  revenue_low:(430+i*28)*billion,revenue_avg:(446+i*32)*billion,revenue_high:(462+i*36)*billion,
  eps_low:7.5+i*.8,eps_avg:8+i*.9,eps_high:8.5+i,analysts:24-i*3})),missing:false};
export const demoFilings={source:'Illustrative demo filings',rows:[{date:'2026-07-31',form:'10-Q',url:null},{date:'2025-11-01',form:'10-K',url:null}],missing:false};

export function demoStockResponse(url) {
  const match=url.pathname.match(/^\/api\/stocks\/([^/]+)(.*)$/);
  if (!match) return null;
  const [,symbol,suffix]=match;
  if (!suffix) return {...demoCompany,symbol,overview:{...demoCompany.overview,Symbol:symbol}};
  if (suffix==='/research') return url.searchParams.get('period')==='quarter' ? demoQuarter : demoAnnual;
  if (suffix==='/prices') return demoPrices;
  if (suffix==='/evidence/earnings') return demoEarnings;
  if (suffix==='/evidence/estimates') return demoEstimates;
  if (suffix==='/evidence/filings') return demoFilings;
  if (suffix==='/financial-history') return {symbol,source:'Illustrative demo annual statements',missing:[],periods:[...annualRows].reverse().slice(0,5)};
  return null;
}
