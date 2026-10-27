from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from diskcache import FanoutCache

from data_providers.price_history_cache import DAY, history_key, price_history


class PriceHistoryCacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = FanoutCache(self.directory.name, shards=2)
        self.now = datetime(2026, 1, 18, 12, tzinfo=timezone.utc).timestamp()
        self.factor, self.calls = 1, []

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def fetch(self, start, end):
        self.calls.append((start, end))
        day, stop = date.fromisoformat(start), date.fromisoformat(end)
        rows = []
        while day <= stop:
            if day.weekday() < 5:
                rows.append({'date': day.isoformat(), 'close': day.toordinal() * self.factor, 'volume': 100})
            day += timedelta(days=1)
        return rows

    def get(self, start='2025-01-01', end='2025-12-31', **kwargs):
        return price_history(self.store, 'offline-test', 'ABC', start, end, self.fetch, now=kwargs.pop('now', self.now), **kwargs)

    def test_subsets_and_normalized_symbols_reuse_one_series(self):
        self.get()
        rows = price_history(self.store, 'offline-test', ' abc ', '2025-06-01', '2025-06-30', self.fetch, self.now)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(rows.Date.iloc[0], '2025-06-02')
        rows.loc[0, 'Close'] = 0
        self.assertGreater(self.get('2025-06-01', '2025-06-30').Close.iloc[0], 0)

    def test_prefix_tail_and_disjoint_requests_cover_the_gaps(self):
        self.get()
        self.get('2024-12-01', '2025-12-31')
        self.assertEqual(self.calls[-1], ('2024-12-01', '2025-01-15'))
        self.get('2026-01-15', '2026-01-16')
        self.assertEqual(self.calls[-1], ('2025-12-17', '2026-01-16'))
        self.get('2025-01-01', '2026-01-14')
        self.assertEqual(len(self.calls), 3)

    def test_stale_tail_and_weekly_reconciliation(self):
        self.get(end='2026-01-16')
        self.get(end='2026-01-16', now=self.now + DAY + 1)
        self.assertEqual(self.calls[-1], ('2026-01-02', '2026-01-16'))
        self.get('2025-06-01', '2025-06-30', now=self.now + 8 * DAY)
        self.assertEqual(self.calls[-1], ('2025-01-01', '2026-01-16'))

    def test_revised_adjusted_prices_refresh_the_entire_retained_history(self):
        original = self.get()
        self.factor = .5
        revised = self.get(end='2026-01-16')
        self.assertEqual(self.calls[1], ('2025-12-17', '2026-01-16'))
        self.assertEqual(self.calls[2], ('2025-01-01', '2026-01-16'))
        self.assertEqual(revised.Close.iloc[0], original.Close.iloc[0] / 2)

    def test_current_day_changes_do_not_trigger_a_historical_reload(self):
        now = datetime(2026, 1, 16, 12, tzinfo=timezone.utc).timestamp()
        self.get(end='2026-01-16', now=now)
        original_fetch = self.fetch
        def revised_tail(start, end):
            rows = original_fetch(start, end)
            for row in rows:
                if row['date'] == '2026-01-16': row['close'] += 1
            return rows
        price_history(self.store, 'offline-test', 'ABC', '2025-01-01', '2026-01-16', revised_tail, now + DAY)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[-1][0], '2026-01-02')

    def test_empty_weekend_results_are_rechecked_without_caching_failures(self):
        empty = Mock(return_value=[])
        for clock in (self.now, self.now + 100, self.now + 901):
            rows = price_history(self.store, 'offline-test', 'ABC', '2026-01-17', '2026-01-18', empty, clock)
            self.assertTrue(rows.empty)
            self.assertEqual(list(rows.columns), ['Date', 'Close'])
        self.assertEqual(empty.call_count, 2)

    def test_failure_or_invalid_response_leaves_the_snapshot_unchanged(self):
        self.get()
        key = history_key('offline-test', 'ABC')
        original = self.store.get(key)
        failures = [RuntimeError('offline'), [], [original['rows']['2025-12-31']], [{'date': 'invalid', 'close': 1}],
                    [{'date': '2026-01-15', 'close': 0}], [{'date': '2026-01-15', 'close': float('inf')}],
                    [{'date': '2026-01-15', 'close': 1}] * 2, {'error': 'unavailable'}]
        for failure in failures:
            fetch = Mock(side_effect=failure) if isinstance(failure, Exception) else Mock(return_value=failure)
            with self.subTest(failure=failure), self.assertRaises(RuntimeError):
                price_history(self.store, 'offline-test', 'ABC', '2025-01-01', '2026-01-16', fetch, self.now)
            self.assertEqual(self.store.get(key), original)
        self.assertFalse(self.get(end='2026-01-16').empty)

    def test_empty_earlier_subsets_retry_after_fifteen_minutes(self):
        empty = Mock(return_value=[])
        price_history(self.store, 'offline-test', 'ABC', '2025-01-01', '2025-12-31', empty, self.now)
        price_history(self.store, 'offline-test', 'ABC', '2025-01-01', '2025-01-31', empty, self.now + 901)
        self.assertEqual(empty.call_count, 2)

    def test_large_ranges_are_chunked_below_the_endpoint_limit(self):
        rows = self.get('1990-01-01', '2025-12-31')
        self.assertGreater(len(self.calls), 1)
        self.assertTrue(all((date.fromisoformat(b)-date.fromisoformat(a)).days <= 3653 for a, b in self.calls))
        self.assertFalse(rows.Date.duplicated().any())

    def test_credentials_are_isolated_and_future_dates_are_not_marked_covered(self):
        self.get()
        price_history(self.store, 'other-account', 'ABC', '2025-01-01', '2025-12-31', self.fetch, self.now)
        self.assertEqual(len(self.calls), 2)
        self.assertNotEqual(history_key('offline-test', 'ABC'), history_key('other-account', 'ABC'))
        self.assertTrue(self.get('2027-01-01', '2027-02-01').empty)
        self.assertEqual(len(self.calls), 2)
        with self.assertRaises(ValueError): self.get('2026-01-02', '2026-01-01')

    def test_threads_do_not_lose_concurrent_extensions(self):
        self.get()
        def run(bounds):
            with FanoutCache(self.directory.name, shards=2) as store:
                def fetch(start, end):
                    time.sleep(.02)
                    return self.fetch(start, end)
                return price_history(store, 'offline-test', 'ABC', *bounds, fetch, self.now)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(run, [('2024-01-01', '2025-12-31'), ('2025-01-01', '2026-01-16')]))
        rows = self.get('2024-01-01', '2026-01-16')
        self.assertEqual(rows.Date.iloc[0], '2024-01-01')
        self.assertEqual(rows.Date.iloc[-1], '2026-01-16')
        self.assertEqual(len(self.calls), 3)

    def test_only_price_requests_accept_successful_empty_responses(self):
        from data_providers import financial_modeling_prep as fmp
        provider = fmp.FinancialModelingPrepProvider(api_key='offline-empty')
        response = Mock(status_code=200)
        response.json.return_value = []
        with patch.object(fmp.fmp_http_session, 'get', return_value=response), patch.object(fmp.fmp_rate_limiter, 'wait_if_needed'):
            self.assertTrue(provider._make_api_request('historical-price-eod/full', 'ABC', allow_empty=True)[0])
            with self.assertLogs(fmp.logger, level='ERROR'):
                self.assertFalse(provider._make_api_request('income-statement', 'ABC')[0])
