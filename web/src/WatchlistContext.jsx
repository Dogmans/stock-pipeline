import React, {createContext, useCallback, useContext, useEffect, useRef, useState} from 'react';
import {Star} from 'lucide-react';
import {addToWatchlist, cleanSymbols, persistWatchlist, readWatchlist, WATCHLIST_KEY} from './watchlist.js';

const WatchlistContext = createContext(null);
function storage() {try {return globalThis.localStorage;} catch {return undefined;}}

export function WatchlistProvider({children}) {
  const [watchlist,setWatchlist] = useState(() => readWatchlist(storage()));
  const current = useRef(watchlist), timer = useRef();
  const [status,setStatus] = useState('');
  const dismissStatus = useCallback(() => {clearTimeout(timer.current);setStatus('');},[]);
  const notify = useCallback(message => {
    clearTimeout(timer.current);setStatus(message);
    timer.current = setTimeout(() => setStatus(''),5000);
  },[]);
  useEffect(() => {
    const sync = event => {
      if (event.key !== WATCHLIST_KEY && event.key !== null) return;
      current.current = readWatchlist(storage());setWatchlist(current.current);
    };
    window.addEventListener('storage',sync);
    return () => {window.removeEventListener('storage',sync);clearTimeout(timer.current);};
  },[]);
  const update = useCallback((next,message) => {
    current.current = next;setWatchlist(next);
    const saved = persistWatchlist(storage(),next);
    notify(saved ? message : `${message} Changes last for this session only; browser storage is unavailable.`);
  },[notify]);
  const addSymbols = useCallback(symbols => {
    const next = addToWatchlist(current.current,symbols), count = next.length-current.current.length;
    if (!count) {notify('These stocks are already on your watchlist.');return;}
    update(next,`${count} ${count === 1 ? 'stock added' : 'stocks added'} to your watchlist.`);
  },[update,notify]);
  const removeSymbol = useCallback(symbol => {
    update(current.current.filter(s => s !== symbol),`${symbol} removed from your watchlist.`);
  },[update]);
  const toggleSymbol = useCallback(symbol => {
    const valid = cleanSymbols([symbol])[0];
    if (!valid) return;
    if (current.current.includes(valid)) removeSymbol(valid);
    else update(addToWatchlist(current.current,[valid]),`${valid} added to your watchlist.`);
  },[removeSymbol,update]);
  return <WatchlistContext.Provider value={{watchlist,addSymbols,removeSymbol,toggleSymbol,notify,status,dismissStatus}}>{children}</WatchlistContext.Provider>;
}

export function useWatchlist() {
  const value = useContext(WatchlistContext);
  if (!value) throw Error('Watchlist controls must be inside WatchlistProvider.');
  return value;
}

export function WatchlistButton({symbol, showLabel = false}) {
  const {watchlist,toggleSymbol} = useWatchlist();
  const saved = watchlist.includes(symbol);
  const label = `${saved ? 'Remove' : 'Add'} ${symbol} ${saved ? 'from' : 'to'} watchlist`;
  return <button type="button" className="watchlist-button" aria-label={label} title={label} aria-pressed={saved}
    onClick={() => toggleSymbol(symbol)}><Star size={15} fill={saved ? 'currentColor' : 'none'}/>{showLabel && (saved ? 'On watchlist' : 'Add to watchlist')}</button>;
}
