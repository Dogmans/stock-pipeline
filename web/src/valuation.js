// All model rates are percentages; all monetary inputs are statement-currency millions.
function numericInput(value) {
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  if (typeof value === 'string' && value.trim() === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function shiftedInput(value, delta) {
  const parsed = numericInput(value);
  return parsed == null ? value : parsed + delta;
}

export function modelDefaults(annual, balance, overview = {}, model = 'advanced') {
  const base = annual?.periods?.filter(r => model === 'simple' ? r.free_cash_flow != null : r.revenue > 0 && r.operating_income != null).at(-1);
  const recent = balance?.periods?.filter(r => r.cash != null && r.debt != null).at(-1)
    || annual?.periods?.filter(r => r.cash != null && r.debt != null).at(-1);
  const spotShares = numericInput(overview.SharesOutstanding);
  const cap = numericInput(overview.MarketCapitalization), price = numericInput(overview.Price);
  const shares = spotShares > 0 ? spotShares : cap > 0 && price > 0 ? cap / price : base?.diluted_shares;
  const balanceCurrency = recent?.sources?.balance ? recent.sources.balance.currency : recent?.currency;
  const sameCurrency = base?.currency && balanceCurrency && base.currency === balanceCurrency;
  const defaults = {
    model, fcf: base?.free_cash_flow != null ? base.free_cash_flow / 1e6 : '', discountRate: 10,
    revenue: base?.revenue != null ? base.revenue / 1e6 : '',
    startMargin: base?.operating_income != null ? base.operating_income / base.revenue * 100 : '',
    targetMargin: base?.operating_income != null ? base.operating_income / base.revenue * 100 : '',
    growth: 10, terminalGrowth: 2.5, wacc: 10, taxRate: 25, salesCapital: 2, terminalRoic: 12,
    years: 10, cash: sameCurrency ? recent.cash / 1e6 : '', debt: sameCurrency ? recent.debt / 1e6 : '',
    otherClaims: sameCurrency && recent.minority_interest != null && recent.preferred_stock != null
      ? (recent.minority_interest + recent.preferred_stock) / 1e6 : '',
    shares: shares > 0 ? shares / 1e6 : '',
    currency: (model === 'simple' && base?.sources?.cash_flow ? base.sources.cash_flow.currency : base?.currency) || '',
    baseDate: base?.date || '', balanceDate: recent?.date || '',
    sharesBasis: spotShares > 0 ? 'Current shares outstanding from quote/profile'
      : cap > 0 && price > 0 ? 'Current market cap / quote price' : 'Annual weighted-average diluted shares (review current dilution)',
  };
  if (model === 'simple') {
    const {fcf,discountRate,growth,terminalGrowth,years,shares,currency,baseDate,sharesBasis} = defaults;
    return {model,fcf,discountRate,growth,terminalGrowth,years,shares,currency,baseDate,sharesBasis};
  }
  return defaults;
}

export function dcf(input, quote = null) {
  if (input.model === 'simple') return simpleDcf(input, quote);
  if (input.model && input.model !== 'advanced') return {error: 'Choose a supported DCF model.'};
  const keys = ['revenue','startMargin','targetMargin','growth','terminalGrowth','wacc','taxRate','salesCapital','terminalRoic','years','cash','debt','otherClaims','shares'];
  const a = Object.fromEntries(keys.map(k => [k, numericInput(input[k])]));
  if (keys.some(k => a[k] == null))
    return {error: 'Complete every model input. Missing balance-sheet claims must be checked and entered, including zero when appropriate.'};
  if (!/^[A-Z]{3}$/.test(input.currency || '')) return {error: 'Enter the three-letter statement currency before valuing the company.'};
  if (a.revenue <= 0 || a.shares <= 0 || a.salesCapital <= 0 || a.terminalRoic <= 0)
    return {error: 'Revenue, shares, sales / capital and terminal ROIC must be positive.'};
  if (![5,10].includes(a.years) || a.wacc <= 0 || a.wacc > 100 || a.terminalGrowth < 0 || a.wacc <= a.terminalGrowth
      || a.terminalRoic <= a.terminalGrowth || a.taxRate < 0 || a.taxRate > 100 || a.growth <= -100 || a.growth > 200
      || a.cash < 0 || a.debt < 0 || a.otherClaims < 0 || Math.abs(a.startMargin) > 100 || a.targetMargin <= 0 || a.targetMargin > 100)
    return {error: 'Use WACC > terminal growth ≥ 0, terminal ROIC > terminal growth, tax 0–100%, growth −100–200%, nonnegative bridge items and a positive terminal margin ≤ 100%.'};
  let revenue = a.revenue, pv = 0;
  const forecast = [];
  for (let year = 1; year <= a.years; year++) {
    // Five explicit growth years; a ten-year model then fades to stable growth.
    const growth = year <= 5 ? a.growth / 100 : (a.growth + (a.terminalGrowth - a.growth) * (year - 5) / 5) / 100;
    const previous = revenue;
    revenue *= 1 + growth;
    const margin = (a.startMargin + (a.targetMargin - a.startMargin) * year / a.years) / 100;
    const ebit = revenue * margin;
    const tax = Math.max(0, ebit) * a.taxRate / 100;
    // Net reinvestment includes net capex and working capital. No release assumed on contraction.
    const reinvestment = Math.max(0, revenue - previous) / a.salesCapital;
    const fcff = ebit - tax - reinvestment;
    const presentValue = fcff / (1 + a.wacc / 100) ** year;
    pv += presentValue;
    forecast.push({year, growth, revenue, margin, ebit, tax, reinvestment, fcff, presentValue});
  }
  const terminalNopat = revenue * (1 + a.terminalGrowth / 100) * a.targetMargin / 100 * (1 - a.taxRate / 100);
  const terminalFcf = terminalNopat * (1 - a.terminalGrowth / a.terminalRoic);
  const terminalValue = terminalFcf / ((a.wacc - a.terminalGrowth) / 100);
  const terminalPv = terminalValue / (1 + a.wacc / 100) ** a.years;
  const enterpriseValue = pv + terminalPv;
  const equityValue = enterpriseValue + a.cash - a.debt - a.otherClaims;
  const fairValue = equityValue / a.shares;
  if (![fairValue, enterpriseValue, terminalPv].every(Number.isFinite)) return {error: 'Model values exceed numerical limits. Review the assumptions.'};
  return {forecast, pv, terminalValue, terminalFcf, terminalPv, enterpriseValue, equityValue, fairValue,
    terminalWeight: enterpriseValue > 0 ? terminalPv / enterpriseValue : null,
    upside: Number.isFinite(quote) && quote > 0 ? fairValue / quote - 1 : null};
}

function simpleDcf(input, quote) {
  const keys = ['fcf','growth','terminalGrowth','discountRate','years','shares'];
  const a = Object.fromEntries(keys.map(k => [k, numericInput(input[k])]));
  if (keys.some(k => a[k] == null)) return {error: 'Complete every model input, including starting free cash flow and share count.'};
  if (!/^[A-Z]{3}$/.test(input.currency || '')) return {error: 'Enter the three-letter statement currency before valuing the company.'};
  if (a.fcf <= 0 || a.shares <= 0) return {error: 'Starting free cash flow and shares must be positive. Enter a normalised positive FCF base if the latest year is negative.'};
  if (![5,10].includes(a.years) || a.growth <= -100 || a.growth > 200 || a.terminalGrowth < 0
      || a.discountRate <= a.terminalGrowth || a.discountRate > 100)
    return {error: 'Use a 5- or 10-year forecast, FCF growth above −100% and up to 200%, and discount rate > terminal growth ≥ 0.'};
  let fcf = a.fcf, pv = 0;
  const forecast = [];
  for (let year = 1; year <= a.years; year++) {
    fcf *= 1 + a.growth / 100;
    const presentValue = fcf / (1 + a.discountRate / 100) ** year;
    pv += presentValue;
    forecast.push({year, growth:a.growth / 100, fcf, presentValue});
  }
  const terminalFcf = fcf * (1 + a.terminalGrowth / 100);
  const terminalValue = terminalFcf / ((a.discountRate - a.terminalGrowth) / 100);
  const terminalPv = terminalValue / (1 + a.discountRate / 100) ** a.years;
  // The entered FCF is treated as available to equity, with no separate cash/debt bridge.
  const equityValue = pv + terminalPv, fairValue = equityValue / a.shares;
  if (![equityValue, fairValue, terminalPv].every(Number.isFinite)) return {error: 'Model values exceed numerical limits. Review the assumptions.'};
  return {forecast, pv, terminalFcf, terminalValue, terminalPv, equityValue, fairValue,
    terminalWeight:terminalPv / equityValue,
    upside:Number.isFinite(quote) && quote > 0 ? fairValue / quote - 1 : null};
}

export function sensitivity(a) {
  const rate = a.model === 'simple' ? 'discountRate' : 'wacc';
  return [-2,-1,0,1,2].map(delta => ({[rate]: shiftedInput(a[rate], delta),
    values: [-1,-.5,0,.5,1].map(d => dcf({...a, [rate]: shiftedInput(a[rate], delta), terminalGrowth: shiftedInput(a.terminalGrowth, d)}))}));
}

export function scenarioInputs(a, scenario) {
  if (scenario === 'base') return {...a};
  const direction = scenario === 'bull' ? 1 : -1;
  if (a.model === 'simple') return {...a, growth:shiftedInput(a.growth, direction * 3), discountRate:shiftedInput(a.discountRate, -direction)};
  return {...a, growth: shiftedInput(a.growth, direction * 3),
    targetMargin: shiftedInput(a.targetMargin, direction * 2), wacc: shiftedInput(a.wacc, -direction)};
}
