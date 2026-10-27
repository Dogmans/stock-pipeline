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

test('direct DCF waits for quarterly balances, and model and note drafts survive navigation', async ({page}) => {
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
  await expect(page.getByLabel('Cash & equivalents (m)',{exact:true})).toHaveValue(String(demoQuarterCash));
  await expect(page.getByTestId('fair-value')).toBeVisible();
  const growth=page.getByLabel('Revenue growth, years 1–5 (%)',{exact:true});
  await growth.fill('7');
  await navigate(page,'financials');
  await expect(page).toHaveURL(/\/financials$/);
  await expect(page.getByRole('rowheader',{name:'Free cash flow',exact:true})).toBeVisible();
  await navigate(page,'valuation');
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
  await expect(page.getByLabel('Cash & equivalents (m)',{exact:true})).toHaveValue('35000');
  await expect(page.getByRole('alert')).toContainText('Quarterly history unavailable');
});
