import {useRef, useState} from 'react';
import {readLocal, saveLocal} from './browserState.js';

// Retain unsaved work across page/stock changes, without writing it to persistent storage.
const drafts = new Map();

export function useLocalDraft(key, initial) {
  const [draft, setDraft] = useState(() => drafts.get(key) || {
    value:{...initial, ...readLocal(key, {})}, dirty:false, saved:false,
  });
  const current = useRef(draft);
  const commit = next => {
    current.current = next;drafts.set(key, next);setDraft(next);
  };
  const update = change => {
    const value = typeof change === 'function' ? change(current.current.value) : change;
    commit({value, dirty:true, saved:false});
  };
  const save = () => {
    const ok = saveLocal(key, current.current.value);
    if (ok) commit({...current.current, dirty:false, saved:true});
    return ok;
  };
  return {...draft, update, save};
}
