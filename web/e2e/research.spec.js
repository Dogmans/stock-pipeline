import {test,expect} from '@playwright/test';
import workflow from '../../workflows/value_quality.json' with {type:'json'};

test('research views compare, explain, restore and track a shortlist', async ({page}, testInfo) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const a = {symbol:'AAPL',company_name:'Apple',sector:'Technology',score:8,reason:'Quality 8 ≥ 7'},
    b = {symbol:'MSFT',company_name:'Microsoft',sector:'Technology',score:9,reason:'Quality 9 ≥ 7'},
    near = {symbol:'NEAR',company_name:'Near miss',sector:'Technology',score:6.8,reason:'Quality 6.8 < 7'};
  const outcome = (passed,failed=[]) => ({input_count:passed.length+failed.length,outcomes:{passed,failed,unavailable:[],error:[]},counts:{passed:passed.length,failed:failed.length,unavailable:0,error:0}});
  const result = {snapshot_id:'snap',snapshot_created_at:'2026-01-01T12:00:00Z',nodes:{
    universe:outcome([a,b,near]),quality:outcome([a,b],[near]),
    value:outcome([{...a,score:10,reason:'P/E 10 ≤ 20'},{...b,score:15,reason:'P/E 15 ≤ 20'}]),
    shortlist:outcome([a,b])},edges:{},shortlist:[a,b]};
  const current = {id:'abc',saved_at:'2026-01-02T12:00:00Z',workflow,result};
  const previous = structuredClone(current);previous.id='def';previous.saved_at='2026-01-01T12:00:00Z';
  previous.result.nodes.shortlist = outcome([a]);
  const history = [current,previous].map(r => ({id:r.id,saved_at:r.saved_at,name:r.workflow.name}));
  await page.route('**/api/**',async route => {
    const path = new URL(route.request().url()).pathname;
    let body;
    if(path === '/api/screeners') body = [
      {id:'quality',label:'Quality',description:'Financial quality',parameters:[],default_rule:{metric:'Quality score',operator:'gte',value:7}},
      {id:'pe_ratio',label:'P/E',description:'Valuation',parameters:[],default_rule:{metric:'P/E',operator:'lte',value:15}}];
    else if(path === '/api/history') body=history;
    else if(path === '/api/history/abc') body=current;
    else if(path === '/api/history/def') body=previous;
    else if(path.endsWith('/performance')) body={pending:true,message:'At least two benchmark trading closes after the saved run are needed.'};
    else if(path.endsWith('/financial-history')) body={source:'FMP annual financial statements',missing:[],periods:[{date:'2025-12-31',currency:'USD',revenue:100,debt:10,free_cash_flow:20},{date:'2024-12-31',currency:'USD',revenue:80}]};
    else if(path.startsWith('/api/stocks/')) body={symbol:path.split('/').pop(),overview:{Name:'Example company',Sector:'Technology',Price:100,Currency:'USD'},news:[]};
    else throw new Error(`Unexpected endpoint ${path}`);
    await route.fulfill({json:body});
  });
  await page.goto('/');
  await page.getByRole('button',{name:'Saved runs',exact:true}).click();
  await page.getByRole('button',{name:'Open run',exact:true}).first().click();
  await expect(page.getByRole('button',{name:'AAPL',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Rank',exact:true}).click();
  await expect(page.getByRole('columnheader',{name:'Rank / 100'})).toBeVisible();
  await page.getByRole('button',{name:'Compare',exact:true}).click();
  await page.getByRole('button',{name:'Expand results'}).click();
  await page.getByLabel('AAPL',{exact:true}).check();
  await page.getByLabel('MSFT',{exact:true}).check();
  await page.getByRole('button',{name:'Compare 2 stocks'}).click();
  await expect(page.getByRole('rowheader',{name:'Annual revenue growth',exact:true})).toBeVisible();
  await expect(page.getByRole('cell',{name:'25%',exact:true})).toHaveCount(2);
  await page.screenshot({path:testInfo.outputPath('comparison.png'),fullPage:true});
  await page.getByRole('button',{name:'Near misses',exact:true}).click();
  await page.getByRole('button',{name:'NEAR',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Why this stock?'})).toBeVisible();
  await expect(page.getByText('Quality 6.8 < 7',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Load five-year financial history'}).click();
  await expect(page.getByText('2025-12-31',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Close stock details'}).click();
  await page.getByRole('button',{name:'Changes',exact:true}).click();
  await page.getByRole('combobox').filter({has:page.locator('option[value="def"]')}).selectOption('def');
  await expect(page.getByText('1 entered · 0 departed · 0 updated.')).toBeVisible();
  await page.getByRole('button',{name:'Performance',exact:true}).click();
  await page.getByRole('button',{name:'Calculate forward returns'}).click();
  await expect(page.getByText('At least two benchmark trading closes after the saved run are needed.')).toBeVisible();
  expect(errors).toEqual([]);
});
