export const WATCHLIST_KEY = 'stock-pipeline.watchlist.v1';
export const DEFAULT_WATCHLIST = ['AAPL','MSFT','GOOGL'];

export function cleanSymbols(symbols) {
  if (!Array.isArray(symbols)) return [];
  return [...new Set(symbols.filter(s => typeof s === 'string').map(s => s.trim().toUpperCase())
    .filter(s => /^[A-Z0-9.^=-]{1,30}$/.test(s)))];
}

export function readWatchlist(storage) {
  try {
    const saved = storage.getItem(WATCHLIST_KEY);
    return saved == null ? [...DEFAULT_WATCHLIST] : cleanSymbols(JSON.parse(saved));
  } catch {return [...DEFAULT_WATCHLIST];}
}

export function addToWatchlist(current, symbols) {
  return cleanSymbols([...current,...cleanSymbols(symbols)]);
}

export function persistWatchlist(storage, symbols) {
  try {storage.setItem(WATCHLIST_KEY, JSON.stringify(cleanSymbols(symbols)));return true;}
  catch {return false;}
}
