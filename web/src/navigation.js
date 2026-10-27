export const researchPages = [
  ['overview', 'Overview'],
  ['financials', 'Financials'],
  ['valuation', 'DCF valuation'],
  ['earnings', 'Earnings & estimates'],
  ['reports', 'Reports & news'],
  ['notes', 'Investment notes'],
];

export function researchHref(symbol, page = 'overview') {
  return `#research/${symbol}${page === 'overview' ? '' : `/${page}`}`;
}

export function workspaceRoute(hash, previous = {}) {
  const screening = hash === '#screening';
  const match = hash.match(/^#research\/([A-Z0-9.^=-]{1,30})(?:\/([a-z]+))?$/i);
  const symbol = match ? match[1].toUpperCase() : previous.symbol || 'AAPL';
  const requestedPage = match?.[2]?.toLowerCase();
  const page = screening ? previous.page || 'overview'
    : researchPages.some(([id]) => id === requestedPage) ? requestedPage : 'overview';
  return {symbol, page, screening,
    researchVisited: previous.researchVisited || !screening,
    screeningVisited: previous.screeningVisited || screening};
}
