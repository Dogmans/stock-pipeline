import test from 'node:test';
import assert from 'node:assert/strict';
import {dcf,modelDefaults,scenarioInputs,sensitivity} from './valuation.js';

const assumptions = {currency:'USD',revenue:100,startMargin:20,targetMargin:20,growth:0,terminalGrowth:0,
  wacc:10,taxRate:25,salesCapital:2,terminalRoic:12,years:10,cash:20,debt:30,otherClaims:0,shares:10};
const simple = {model:'simple',currency:'USD',fcf:15,growth:0,terminalGrowth:0,discountRate:10,years:10,shares:10};

test('simple DCF discounts a perpetual equity cash flow once without a debt or reinvestment adjustment', () => {
  const r = dcf({...simple,cash:500,debt:200,otherClaims:50,salesCapital:0},10);
  assert.ok(Math.abs(r.equityValue-150) < 1e-10);
  assert.ok(Math.abs(r.fairValue-15) < 1e-10);
  assert.ok(Math.abs(r.upside-.5) < 1e-10);
  assert.equal(r.forecast[0].fcf,15);
  assert.equal(r.enterpriseValue,undefined);
});

test('simple DCF compounds FCF for the full horizon and discounts terminal value from the final year', () => {
  const r = dcf({...simple,years:5,growth:10,terminalGrowth:2});
  const cashFlows = [16.5,18.15,19.965,21.9615,24.15765];
  cashFlows.forEach((fcf,i) => assert.ok(Math.abs(r.forecast[i].fcf-fcf) < 1e-10));
  assert.ok(Math.abs(r.terminalFcf-24.15765*1.02) < 1e-10);
  assert.ok(Math.abs(r.terminalPv-(24.15765*1.02/.08)/1.1**5) < 1e-10);
  assert.ok(Math.abs(r.pv-75) < 1e-10);
});

test('simple DCF value rises as FCF growth increases with other assumptions fixed', () => {
  for (const years of [5,10]) {
    let previous = -Infinity;
    for (const growth of [-30,-5,0,5,10,20,50]) {
      const r = dcf({...simple,years,growth});
      assert.ok(r.fairValue > previous);
      previous = r.fairValue;
    }
  }
});

test('simple scenarios and sensitivity use required return and do not require operating inputs', () => {
  const a = {...simple,growth:8,terminalGrowth:2};
  assert.ok(dcf(scenarioInputs(a,'bull')).fairValue > dcf(a).fairValue);
  assert.ok(dcf(scenarioInputs(a,'bear')).fairValue < dcf(a).fairValue);
  assert.equal(scenarioInputs(a,'bull').discountRate,9);
  const grid = sensitivity(a);
  assert.equal(grid[2].values[2].fairValue,dcf(a).fairValue);
  assert.ok(grid[0].values[2].fairValue > grid[4].values[2].fairValue);
  assert.equal(a.growth,8);
});

test('simple DCF validates only its own inputs and never fills missing values', () => {
  for (const field of ['fcf','growth','terminalGrowth','discountRate','years','shares']) {
    for (const value of ['',null,undefined,NaN,Infinity,true,{}]) {
      const invalid = {...simple,[field]:value};
      for (const scenario of ['base','bull','bear']) assert.ok(dcf(scenarioInputs(invalid,scenario)).error);
      assert.ok(sensitivity(invalid).every(row => row.values.every(r => r.error)));
    }
  }
  for (const patch of [{fcf:0},{fcf:-1},{shares:0},{discountRate:2,terminalGrowth:3},{growth:-100},{years:7},{currency:''}])
    assert.ok(dcf({...simple,...patch}).error);
  const strings = Object.fromEntries(Object.entries(simple).map(([key,value]) => [key,String(value)]));
  assert.equal(dcf(strings).fairValue,dcf(simple).fairValue);
});

test('simple defaults use reported FCF even when operating or balance data is missing', () => {
  const a = modelDefaults({periods:[{date:'2025-12-31',currency:'USD',free_cash_flow:12e6}]},null,{SharesOutstanding:3e6},'simple');
  assert.equal(a.fcf,12);
  assert.equal(a.model,'simple');
  assert.equal(a.salesCapital,undefined);
  assert.equal(a.cash,undefined);
  assert.equal(a.debt,undefined);
  assert.ok(!dcf(a).error);
  assert.equal(modelDefaults({periods:[]},null,{},'simple').fcf,'');
  const source = {periods:[{date:'2025-12-31',currency:'USD',free_cash_flow:12e6,sources:{cash_flow:{currency:'CAD'}}}]};
  assert.equal(modelDefaults(source,null,{},'simple').currency,'CAD');
  source.periods[0].sources.cash_flow.currency = null;
  assert.equal(modelDefaults(source,null,{},'simple').currency,'');
});

test('a zero-growth perpetual business values the perpetuity once and applies the equity bridge', () => {
  const r = dcf(assumptions,10);
  // EBIT 20, taxes 5, no reinvestment -> perpetual FCFF 15 / 10% = EV 150.
  assert.ok(Math.abs(r.enterpriseValue - 150) < 1e-10);
  assert.ok(Math.abs(r.equityValue - 140) < 1e-10);
  assert.ok(Math.abs(r.fairValue - 14) < 1e-10);
  assert.ok(Math.abs(r.upside - .4) < 1e-10);
  assert.equal(r.forecast.length,10);
});

test('growth requires reinvestment and terminal growth requires sustainable reinvestment', () => {
  const r = dcf({...assumptions,growth:10,terminalGrowth:3});
  const first = r.forecast[0];
  assert.ok(Math.abs(first.revenue - 110) < 1e-10);
  assert.ok(Math.abs(first.reinvestment - 5) < 1e-10);
  assert.ok(Math.abs(first.fcff - 11.5) < 1e-10);
  assert.equal(r.forecast.at(-1).growth,.03);
  const final = r.forecast.at(-1);
  assert.ok(Math.abs(r.terminalFcf - final.revenue * 1.03 * .2 * .75 * .75) < 1e-10);
  assert.ok(dcf({...assumptions,growth:10,salesCapital:1}).fairValue < dcf({...assumptions,growth:10,salesCapital:3}).fairValue);
});

test('negative operating income receives no invented tax benefit and negative revenue growth releases no capital', () => {
  const r = dcf({...assumptions,startMargin:-50,targetMargin:10,growth:-5});
  assert.equal(r.forecast[0].tax,0);
  assert.equal(r.forecast[0].reinvestment,0);
  assert.ok(r.forecast[0].fcff<0);
});

test('higher growth raises value for a profitable business despite lower near-term cash flow', () => {
  const a = {...assumptions,growth:10,terminalGrowth:2.5};
  const base = dcf(a), faster = dcf({...a,growth:15});
  assert.ok(faster.forecast[0].fcff < base.forecast[0].fcff);
  assert.ok(faster.fairValue > base.fairValue);
});

test('higher growth can reduce value when low margins do not justify the reinvestment', () => {
  const a = {...assumptions,startMargin:5,targetMargin:5,growth:10,terminalGrowth:2.5};
  const base = dcf(a), faster = dcf({...a,growth:15});
  // Extra first-year revenue of 5 earns 0.1875 after tax but requires 2.5 of investment.
  assert.ok(Math.abs(faster.forecast[0].reinvestment-base.forecast[0].reinvestment-2.5) < 1e-10);
  assert.ok(Math.abs(faster.forecast[0].fcff-base.forecast[0].fcff+2.3125) < 1e-10);
  assert.ok(faster.terminalPv > base.terminalPv);
  assert.ok(base.pv-faster.pv > faster.terminalPv-base.terminalPv);
  assert.ok(faster.fairValue < base.fairValue);
});

test('rejects missing bridge data, unstable terminal assumptions, zero shares, and unsupported horizons', () => {
  for (const patch of [{otherClaims:''},{cash:null},{revenue:Infinity},{wacc:2,terminalGrowth:3},
    {terminalRoic:2,terminalGrowth:3},{shares:0},{salesCapital:0},{growth:-100},{taxRate:101},{years:7},{currency:''},{debt:-1}])
    assert.ok(dcf({...assumptions,...patch}).error,JSON.stringify(patch));
  assert.equal(dcf(assumptions).upside,null);
  assert.equal(dcf(assumptions,0).upside,null);
});

test('scenario and sensitivity values respond in the expected direction without modifying the base', () => {
  const a = {...assumptions,growth:8,terminalGrowth:2};
  assert.ok(dcf(scenarioInputs(a,'bull')).fairValue > dcf(a).fairValue);
  assert.ok(dcf(scenarioInputs(a,'bear')).fairValue < dcf(a).fairValue);
  assert.equal(a.growth,8);
  const grid = sensitivity(a);
  assert.equal(grid.length,5);
  assert.equal(grid[2].values[2].fairValue,dcf(a).fairValue);
  assert.ok(grid[0].values[2].fairValue>grid[4].values[2].fairValue);
});

test('scenario and sensitivity adjustments never fill missing required assumptions with zero', () => {
  const fields = ['revenue','startMargin','targetMargin','growth','terminalGrowth','wacc','taxRate',
    'salesCapital','terminalRoic','years','cash','debt','otherClaims','shares'];
  for (const field of fields) {
    const incomplete = {...assumptions,[field]:''};
    for (const scenario of ['bear','base','bull'])
      assert.ok(dcf(scenarioInputs(incomplete,scenario)).error,`${field}: ${scenario}`);
    assert.ok(sensitivity(incomplete).every(row => row.values.every(value => value.error)),field);
  }
});

test('invalid numeric values stay invalid in the model and all adjusted cases', () => {
  for (const value of ['   ',null,undefined,NaN,Infinity,-Infinity,true,false,[],{},['10']]) {
    for (const field of ['growth','targetMargin','wacc','terminalGrowth']) {
      const invalid = {...assumptions,[field]:value};
      for (const scenario of ['bear','base','bull'])
        assert.ok(dcf(scenarioInputs(invalid,scenario)).error,`${field}: ${String(value)}: ${scenario}`);
      assert.ok(sensitivity(invalid).every(row => row.values.every(result => result.error)),field);
    }
  }
});

test('finite numeric strings retain the same valuation and scenario adjustments as numbers', () => {
  const strings=Object.fromEntries(Object.entries(assumptions).map(([key,value]) => [key,String(value)]));
  assert.equal(dcf(strings).fairValue,dcf(assumptions).fairValue);
  for (const scenario of ['bear','base','bull'])
    assert.equal(dcf(scenarioInputs(strings,scenario)).fairValue,dcf(scenarioInputs(assumptions,scenario)).fairValue);
  assert.equal(sensitivity(strings)[2].values[2].fairValue,dcf(assumptions).fairValue);
});

test('defaults align source currencies, use the latest quarterly bridge and current rather than weighted shares', () => {
  const annual = {periods:[{date:'2025-12-31',currency:'USD',revenue:100e6,operating_income:20e6,
    cash:10e6,debt:30e6,minority_interest:0,preferred_stock:0,diluted_shares:10e6}]};
  const quarter = {periods:[{date:'2026-06-30',currency:'USD',cash:12e6,debt:29e6,minority_interest:2e6,preferred_stock:0}]};
  const a = modelDefaults(annual,quarter,{SharesOutstanding:9e6});
  assert.equal(a.shares,9);assert.equal(a.cash,12);assert.equal(a.debt,29);assert.equal(a.otherClaims,2);
  assert.equal(a.startMargin,20);assert.equal(a.balanceDate,'2026-06-30');
  const mismatch = modelDefaults(annual,{periods:[{...quarter.periods[0],currency:'CAD'}]});
  assert.equal(mismatch.cash,'');assert.equal(mismatch.debt,'');
  assert.equal(modelDefaults(annual,null,{MarketCapitalization:90e6,Price:10}).shares,9);
  assert.equal(modelDefaults(annual,null,{}).shares,10);
  assert.equal(modelDefaults({periods:[]},null,{}).revenue,'');
});

test('the equity bridge uses the balance source currency rather than an inherited income currency', () => {
  const annual={periods:[{date:'2025-12-31',currency:'USD',revenue:100e6,operating_income:20e6,
    diluted_shares:10e6,sources:{income:{currency:'USD'}}}]};
  const balance={date:'2026-06-30',currency:'USD',cash:12e6,debt:29e6,minority_interest:2e6,preferred_stock:0};
  for (const currency of [null,undefined,'CAD']) {
    const result=modelDefaults(annual,{periods:[{...balance,sources:{balance:{currency}}}]});
    assert.equal(result.cash,'');
    assert.equal(result.debt,'');
    assert.equal(result.otherClaims,'');
  }
  const matching=modelDefaults(annual,{periods:[{...balance,sources:{balance:{currency:'USD'}}}]});
  assert.equal(matching.cash,12);
  assert.equal(matching.debt,29);
  assert.equal(matching.otherClaims,2);
  const legacy=modelDefaults(annual,{periods:[balance]});
  assert.equal(legacy.cash,12);
  assert.equal(legacy.debt,29);
});
