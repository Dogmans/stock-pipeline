import {test} from 'node:test';
import assert from 'node:assert/strict';
import {researchHref,workspaceRoute} from './navigation.js';

test('old company URLs stay compatible while research pages have shareable history entries', () => {
  assert.equal(workspaceRoute('#research/msft').page,'overview');
  const route=workspaceRoute('#research/SHOP.TO/financials');
  assert.equal(route.symbol,'SHOP.TO');
  assert.equal(route.page,'financials');
  assert.equal(researchHref(route.symbol,route.page),'#research/SHOP.TO/financials');
  assert.equal(researchHref('AAPL'),'#research/AAPL');
});

test('screening navigation preserves the research company/page and visited workspace state', () => {
  const research=workspaceRoute('#research/MSFT/valuation');
  const screening=workspaceRoute('#screening',research);
  assert.equal(screening.symbol,'MSFT');
  assert.equal(screening.page,'valuation');
  assert.ok(screening.screeningVisited && screening.researchVisited);
  const returned=workspaceRoute(researchHref(screening.symbol,screening.page),screening);
  assert.equal(returned.page,'valuation');
  assert.equal(returned.screening,false);
  assert.ok(returned.screeningVisited);
});

test('a direct screener visit loads no research page and unknown sections fall back safely', () => {
  assert.equal(workspaceRoute('#screening').researchVisited,false);
  assert.equal(workspaceRoute('#research/AAPL/notapage').page,'overview');
  assert.equal(workspaceRoute('#research/bad!').symbol,'AAPL');
});
