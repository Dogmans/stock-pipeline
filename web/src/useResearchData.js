import {useEffect, useState} from 'react';

const cache = new Map();
const cacheLifetime = 5 * 60 * 1000;

export default function useResearchData(path, revision = 0) {
  const [state, setState] = useState({path, revision, loading:!!path, data:null, error:''});
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    let timer;
    const settle = (data, expiresAt = Date.now() + cacheLifetime) => {
      if (controller.signal.aborted) return;
      setState({path, revision, data, loading:false, error:''});
      timer = setTimeout(() => setTick(value => value + 1), Math.max(1, expiresAt - Date.now()));
    };
    const cached = cache.get(path);
    if (cached && cached.revision === revision && Date.now() < cached.expiresAt) {
      settle(cached.data, cached.expiresAt);
    } else {
      setState(current => ({path, revision, loading:true, data:current.path === path ? current.data : null, error:''}));
      fetch('/api' + path, {signal:controller.signal}).then(async response => {
        const data = await response.json();
        if (!response.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Research request failed.');
        return data;
      }).then(data => {
        if (controller.signal.aborted) return;
        if (cache.size >= 80) cache.delete(cache.keys().next().value);
        cache.set(path, {data, revision, expiresAt:Date.now() + cacheLifetime});
        settle(data);
      }).catch(error => {
        if (!controller.signal.aborted) setState(current => ({path, revision, data:current.data, loading:false, error:error.message}));
      });
    }
    return () => {controller.abort();clearTimeout(timer);};
  }, [path, revision, tick]);
  return state.path === path && state.revision === revision ? state
    : {loading:!!path, data:state.path === path ? state.data : null, error:''};
}
