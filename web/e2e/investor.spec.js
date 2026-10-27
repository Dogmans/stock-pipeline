import {test,expect} from '@playwright/test';
import {demoStockResponse,demoQuarterCash} from '../scripts/research-demo.mjs';

async function navigate(page, section) {
  const mobile = page.getByRole('combobox',{name:'Workspace page',exact:true});
  if (await mobile.isVisible()) await mobile.selectOption(section);
  else {
    const labels={overview:'Overview',financials:'Financials',valuation:'DCF valuation',notes:'Investment notes'};
    await page.getByRole('link',{name:labels[section],exact:true}).click();
  }
}

test('advanced DCF waits for quarterly balances, and model and note drafts survive navigation', async ({page}) => {
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  let releaseQuarter;
  const quarterGate=new Promise(resolve=>{releaseQuarter=resolve;});
  await page.route('**/api/**',async route=>{
    const url=new URL(route.request().url());
    if (url.pathname.endsWith('/research') && url.searchParams.get('period')==='quarter') await quarterGate;
    const body=demoStockResponse(url);
    if (!body) throw Error(`Unexpected API request ${url.pathname}`);
    await route.fulfill({json:body});
  });
  await page.goto('/#research/AAPL/valuation');
  await expect(page.getByRole('heading',{name:'Apple Inc. - Demo data',exact:true})).toBeVisible();
  await expect(page.getByLabel('Cash & equivalents (m)',{exact:true})).toHaveCount(0);
  releaseQuarter();
  await page.getByRole('combobox',{name:'DCF model',exact:true}).selectOption('advanced');
  await expect(page.getByLabel('Cash & equivalents (m)',{exact:true})).toHaveValue(String(demoQuarterCash));
  await expect(page.getByTestId('fair-value')).toBeVisible();
  const growth=page.getByLabel('Revenue growth, years 1–5 (%)',{exact:true});
  await growth.fill('7');
  await navigate(page,'financials');
  await expect(page).toHaveURL(/\/financials$/);
  await expect(page.getByRole('rowheader',{name:'Free cash flow',exact:true})).toBeVisible();
  await navigate(page,'valuation');
  await page.getByRole('combobox',{name:'DCF model',exact:true}).selectOption('advanced');
  await expect(growth).toHaveValue('7');
  await page.getByLabel('WACC (%)',{exact:true}).fill('');
  await page.getByRole('button',{name:/^BULL/}).click();
  await expect(page.getByTestId('fair-value')).toHaveCount(0);
  await page.getByLabel('WACC (%)',{exact:true}).fill('10');
  await expect(page.getByTestId('fair-value')).toBeVisible();
  await navigate(page,'notes');
  const thesis=page.getByRole('textbox',{name:'Thesis & variant perception',exact:true});
  await thesis.fill('Revisit cash conversion after the next earnings report.');
  await navigate(page,'overview');
  await page.goBack();
  await expect(thesis).toHaveValue('Revisit cash conversion after the next earnings report.');
  await page.getByRole('button',{name:'Save investment notes',exact:true}).click();
  await page.reload();
  await expect(thesis).toHaveValue('Revisit cash conversion after the next earnings report.');
  expect(errors).toEqual([]);
});

test('DCF can use the annual balance sheet when quarterly history fails', async ({page}) => {
  await page.route('**/api/**',async route=>{
    const url=new URL(route.request().url());
    if (url.pathname.endsWith('/research') && url.searchParams.get('period')==='quarter') {
      await route.fulfill({status:503,json:{detail:'Quarterly history unavailable'}});return;
    }
    const body=demoStockResponse(url);
    if (!body) throw Error(`Unexpected API request ${url.pathname}`);
    await route.fulfill({json:body});
  });
  await page.goto('/#research/AAPL/valuation');
  await expect(page.getByTestId('fair-value')).toBeVisible();
  await page.getByRole('combobox',{name:'DCF model',exact:true}).selectOption('advanced');
  await expect(page.getByLabel('Cash & equivalents (m)',{exact:true})).toHaveValue('35000');
  await expect(page.getByRole('alert')).toContainText('Quarterly history unavailable');
});

test('financial rows select their history chart by mouse or keyboard', async ({page}) => {
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/api/**',async route=>{
    const url=new URL(route.request().url()), body=demoStockResponse(url);
    if (!body) throw Error(`Unexpected API request ${url.pathname}`);
    await route.fulfill({json:body});
  });
  await page.goto('/#research/AAPL/financials');
  const chart=page.getByRole('region',{name:'Financial metric chart',exact:true});
  await expect(chart.getByRole('img',{name:/Free cash flow over time/})).toBeVisible();
  const revenue=page.getByRole('rowheader',{name:'Revenue',exact:true}).locator('..');
  await revenue.getByRole('cell').first().click();
  await expect(page.getByRole('combobox',{name:'Chart metric',exact:true})).toHaveValue('revenue');
  await expect(revenue.getByRole('button',{name:'Revenue',exact:true})).toHaveAttribute('aria-pressed','true');
  await expect(chart.getByRole('img',{name:/Revenue over time/})).toBeInViewport();
  await page.getByRole('button',{name:'YoY change',exact:true}).click();
  await expect(chart.getByRole('img',{name:/Revenue.*YoY change over time/})).toBeVisible();
  const margin=page.getByRole('rowheader',{name:'Operating margin',exact:true}).getByRole('button');
  await margin.focus();
  await margin.press('Enter');
  await expect(margin).toHaveAttribute('aria-pressed','true');
  await expect(page.getByRole('button',{name:'YoY change',exact:true})).toHaveAttribute('aria-pressed','false');
  await expect(chart.getByRole('img',{name:/Operating margin over time/})).toBeInViewport();
  await page.getByRole('button',{name:'Quarterly',exact:true}).click();
  await expect(page.getByRole('combobox',{name:'Chart metric',exact:true})).toHaveValue('operating_income_margin');
  await expect(chart.getByRole('img',{name:/Operating margin over time/})).toBeVisible();
  await page.getByRole('combobox',{name:'Chart metric',exact:true}).selectOption('gross_profit');
  await expect(page.getByRole('rowheader',{name:'Gross profit',exact:true}).getByRole('button')).toHaveAttribute('aria-pressed','true');
  expect(errors).toEqual([]);
});


test('profitability traits show matching ratios, selectable history and CSV export', async ({page},testInfo) => {
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  const latest={date:'2025-12-31',currency:'USD',roe:.2,roa:.128,roce:.4,roe_change_3y:.1,
    roe_3y_ago:.1,comparison_date:'2022-12-31'};
  await page.route('**/api/**',async route=>{
    const url=new URL(route.request().url()),body=demoStockResponse(url);
    if (!body) throw Error(`Unexpected API request ${url.pathname}`);
    if (url.pathname==='/api/stocks/AAPL') body.profitability={latest,history:[{...latest,date:'2024-12-31',roce:.32},latest],source:'Illustrative quarterly statements'};
    await route.fulfill({json:body});
  });
  await page.goto('/#research/AAPL');
  const panel=page.locator('.ir-card').filter({has:page.getByRole('heading',{name:'Profitability traits',exact:true})});
  await expect(panel.locator('.ir-kpi').getByText('20.0%',{exact:true})).toBeVisible();
  await expect(panel.getByText('12.8%',{exact:true})).toBeVisible();
  await expect(panel.getByText('+10.0pp',{exact:true})).toBeVisible();
  await panel.getByRole('combobox',{name:'Profitability chart metric'}).selectOption('roce');
  await expect(panel.getByRole('img',{name:/TTM return on capital employed.*Latest 2025-12-31: 40.0%/})).toBeVisible();
  const downloadPromise=page.waitForEvent('download');
  await panel.getByRole('button',{name:'Export profitability CSV'}).click();
  const download=await downloadPromise;
  expect(download.suggestedFilename()).toBe('AAPL-profitability.csv');
  const stream=await download.createReadStream();
  const chunks=[];for await (const chunk of stream) chunks.push(chunk);
  const csv=Buffer.concat(chunks).toString();
  expect(csv).toContain('ROE (fraction)');expect(csv).toContain('"0.128"');expect(csv).toContain('2022-12-31');
  await panel.screenshot({path:testInfo.outputPath('profitability.png')});
  await navigate(page,'financials');
  await expect(page.getByRole('heading',{name:'Profitability traits',exact:true})).toBeVisible();
  expect(errors).toEqual([]);
});
