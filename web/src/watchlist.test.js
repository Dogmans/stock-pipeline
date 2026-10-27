import {test} from 'node:test';
import assert from 'node:assert/strict';
import {addToWatchlist,cleanSymbols,DEFAULT_WATCHLIST,persistWatchlist,readWatchlist,WATCHLIST_KEY} from './watchlist.js';

const memoryStorage = () => {
  const values = new Map();
  return {getItem:key => values.get(key) ?? null,setItem:(key,value) => values.set(key,value)};
};

test('screening additions preserve saved research symbols and deduplicate a filtered shortlist', () => {
  const saved = addToWatchlist(['AAPL','SHOP.TO'],['msft','AAPL','MSFT',' NEAR ','bad!','']);
  assert.deepEqual(saved,['AAPL','SHOP.TO','MSFT','NEAR']);
  assert.deepEqual(addToWatchlist(saved,['MSFT','NEAR']),saved);
});

test('watchlist round-trips through the original storage key and preserves an intentionally empty list', () => {
  const storage=memoryStorage();
  assert.deepEqual(readWatchlist(storage),DEFAULT_WATCHLIST);
  storage.setItem(WATCHLIST_KEY,JSON.stringify(['SHOP.TO','near','SHOP.TO']));
  const saved=addToWatchlist(readWatchlist(storage),['MSFT']);
  assert.ok(persistWatchlist(storage,saved));
  assert.deepEqual(readWatchlist(storage),['SHOP.TO','NEAR','MSFT']);
  assert.ok(persistWatchlist(storage,[]));
  assert.deepEqual(readWatchlist(storage),[]);
});

test('storage failures are reported and malformed saved values do not break the workspace', () => {
  const denied={getItem(){throw Error('denied');},setItem(){throw Error('denied');}};
  assert.deepEqual(readWatchlist(denied),DEFAULT_WATCHLIST);
  assert.equal(persistWatchlist(denied,['AAPL']),false);
  const storage=memoryStorage();
  storage.setItem(WATCHLIST_KEY,'broken json');
  assert.deepEqual(readWatchlist(storage),DEFAULT_WATCHLIST);
  storage.setItem(WATCHLIST_KEY,'{"unexpected":true}');
  assert.deepEqual(readWatchlist(storage),[]);
  assert.deepEqual(cleanSymbols([null,42,'aapl','AAPL','SHOP.TO','bad!']),['AAPL','SHOP.TO']);
});
