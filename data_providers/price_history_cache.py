"""Incremental, split-adjusted daily history in the existing DiskCache."""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import math
from threading import Lock
import time

import pandas as pd

DAY = 86400
OVERLAP = timedelta(days=14)
_LOCKS = tuple(Lock() for _ in range(16))


def history_key(namespace, symbol):
    return ('daily-split-v1', sha256(repr((namespace, symbol.strip().upper())).encode()).hexdigest())


def _download(fetch, ranges):
    rows = {}
    for start, end in ranges:
        while start <= end:
            stop = min(end, start + timedelta(days=3653))  # Below FMP's 5,000-row cap.
            data = fetch(start.isoformat(), stop.isoformat())
            if not isinstance(data, list):
                raise RuntimeError('Invalid daily price history.')
            for row in data:
                try:
                    day = date.fromisoformat(row['date'])
                    close = float(row['close'])
                    if not start <= day <= stop or day.isoformat() in rows or not math.isfinite(close) or close <= 0:
                        raise ValueError
                except (KeyError, TypeError, ValueError):
                    raise RuntimeError('Invalid daily price history.') from None
                rows[day.isoformat()] = {**row, 'close': close}
            start = stop + timedelta(days=1)
    return rows


def price_history(store, namespace, symbol, from_date, to_date, fetch, now=None):
    start, end = date.fromisoformat(str(from_date)), date.fromisoformat(str(to_date))
    if start > end:
        raise ValueError('Start date must not follow end date.')
    now = time.time() if now is None else now
    today = datetime.fromtimestamp(now, timezone.utc).date()
    end = min(end, today)
    if start > end:
        return pd.DataFrame(columns=['Date', 'Close'])
    key = history_key(namespace, symbol)
    # Keep each read/fetch/merge/write sequence together across request threads.
    with _LOCKS[int(key[1][0], 16)]:
        old = store.get(key)
        lo, hi = (min(start, old['start']), max(end, old['end'])) if old else (start, end)
        full = not old or now - old['full_at'] >= 7 * DAY
        ranges = [(lo, hi)] if full else []
        if not full:
            if start < old['start']:
                ranges.append((lo, min(hi, old['start'] + OVERLAP)))
            if end > old['end'] or ((not old['rows'] or end >= old['end'] - OVERLAP) and now >= old['refresh_at']):
                ranges.append((max(lo, old['end'] - OVERLAP), hi))
            if len(ranges) == 2 and ranges[0][1] >= ranges[1][0]:
                ranges = [(lo, hi)]
        if ranges:
            fresh = _download(fetch, ranges)
            previous = old['rows'] if old else {}
            provisional = old.get('provisional', set()) if old else set()
            if not full and any(day in previous and day not in provisional and day < today.isoformat()
                                and row['close'] != previous[day]['close'] for day, row in fresh.items()):
                full, ranges = True, [(lo, hi)]
                fresh = _download(fetch, ranges)
            covered = lambda day: any(a <= date.fromisoformat(day) <= b for a, b in ranges)
            if any(covered(day) and day not in fresh for day in previous):
                raise RuntimeError('Daily price history unexpectedly lost cached observations.')
            rows = {day: row for day, row in previous.items() if not covered(day)}
            rows.update(fresh)
            tail_checked = any(b == hi for _, b in ranges)
            refresh_at = now + (900 if hi >= today or not rows or max(rows) < hi.isoformat() else DAY)
            old = {'start': lo, 'end': hi, 'rows': rows,
                   'full_at': now if full else old['full_at'],
                   'refresh_at': refresh_at if tail_checked else old['refresh_at'],
                   'provisional': {day for day in provisional if not covered(day)} | ({today.isoformat()} & fresh.keys())}
            store.set(key, old, expire=30 * DAY, retry=True)
        selected = [row for day, row in sorted(old['rows'].items()) if start.isoformat() <= day <= end.isoformat()]
    return pd.DataFrame(selected).rename(columns={'date': 'Date', 'close': 'Close'}) if selected else pd.DataFrame(columns=['Date', 'Close'])
