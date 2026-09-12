"""Offline coverage for FMP memoization keys and shared HTTP transport."""
import unittest
from unittest.mock import Mock, patch

import main  # Preserve the application's import order.
from cache_config import cache
from data_providers import financial_modeling_prep as fmp
from utils.throttling import create_cache_checker


class FMPCacheTests(unittest.TestCase):
    def test_all_cache_probes_match_memoization_keys(self):
        provider = fmp.FinancialModelingPrepProvider(api_key='offline-cache-check')
        calls = [
            ('get_company_overview', ('CACHE_TEST',), {}),
            ('get_stock_news', ('CACHE_TEST',), {'limit': 8}),
            ('get_historical_prices', (['CACHE_TEST'],), {'period': '1y'}),
            ('get_income_statement', ('CACHE_TEST',), {'annual': False}),
            ('get_balance_sheet', (), {'symbol': 'CACHE_TEST', 'annual': True}),
            ('get_cash_flow', ('CACHE_TEST',), {}),
            ('get_etf_holdings', ('CACHE_TEST',), {}),
            ('get_insider_trading', ('CACHE_TEST',), {'lookback_days': 30}),
        ]
        for name, args, kwargs in calls:
            with self.subTest(method=name):
                method = getattr(provider, name)
                key = method.__cache_key__(provider, *args, **kwargs)
                checker = create_cache_checker(cache, name)
                cache.delete(key)
                self.assertFalse(checker(provider, *args, **kwargs))
                try:
                    for value in (None, {}, [], {'data': 1}):
                        cache.set(key, value, expire=60)
                        self.assertTrue(checker(provider, *args, **kwargs))
                    cache.set(key, {}, expire=-1)
                    self.assertFalse(checker(provider, *args, **kwargs))
                finally:
                    cache.delete(key)

    def test_keys_distinguish_arguments_and_credentials(self):
        provider = fmp.FinancialModelingPrepProvider(api_key='offline-key-one')
        other = fmp.FinancialModelingPrepProvider(api_key='offline-key-two')
        key = provider.get_income_statement.__cache_key__(provider, 'KEY_TEST', annual=True)
        checker = create_cache_checker(cache, 'get_income_statement')
        cache.set(key, [], expire=60)
        try:
            self.assertTrue(checker(provider, 'KEY_TEST', annual=True))
            self.assertFalse(checker(provider, 'KEY_TEST', annual=False))
            self.assertFalse(checker(provider, 'OTHER', annual=True))
            self.assertFalse(checker(other, 'KEY_TEST', annual=True))
            self.assertFalse(checker(provider, 'KEY_TEST', annual=True, force_refresh=True))
        finally:
            cache.delete(key)

    def test_http_use_preserves_cache_keys_across_provider_instances(self):
        provider = fmp.FinancialModelingPrepProvider(api_key='offline-stable-cache')
        other = fmp.FinancialModelingPrepProvider(api_key='offline-stable-cache')
        symbol = 'SESSION_CACHE_TEST'
        key = provider.get_company_overview.__cache_key__(provider, symbol)
        cache.delete(key)
        response = Mock(status_code=200)
        response.json.return_value = [{'companyName': 'Offline', 'pe': 10, 'marketCap': 1000,
                                       'priceToBookRatio': 1, 'priceToSalesRatio': 2}]
        try:
            with patch.object(fmp.fmp_http_session, 'get', return_value=response) as get, \
                 patch.object(fmp.fmp_rate_limiter, 'wait_if_needed'), \
                 patch('time.sleep'):
                first = provider.get_company_overview(symbol)
                self.assertEqual(get.call_count, 3)
                self.assertTrue(create_cache_checker(cache, 'get_company_overview')(provider, symbol))
                with patch('time.sleep', side_effect=AssertionError('Cache hit must not sleep')):
                    self.assertEqual(provider.get_company_overview(symbol), first)
                    self.assertEqual(other.get_company_overview(symbol), first)
                self.assertEqual(get.call_count, 3)
        finally:
            cache.delete(key)


class FMPTransportTests(unittest.TestCase):
    def test_central_and_insider_requests_share_session_across_instances(self):
        first = fmp.FinancialModelingPrepProvider(api_key='offline-session-one')
        second = fmp.FinancialModelingPrepProvider(api_key='offline-session-two')
        response = Mock(status_code=200)
        response.json.return_value = [{'symbol': 'TRANSPORT_TEST'}]
        key = first.get_insider_trading.__cache_key__(first, 'TRANSPORT_TEST')
        cache.delete(key)
        try:
            with patch.object(fmp.fmp_http_session, 'get', return_value=response) as get, \
                 patch.object(fmp.requests, 'get', side_effect=AssertionError('Standalone HTTP request')), \
                 patch.object(fmp.requests, 'Session', side_effect=AssertionError('New session per request')), \
                 patch.object(fmp.fmp_rate_limiter, 'wait_if_needed') as limiter, \
                 patch('time.sleep'):
                self.assertTrue(first._make_api_request('quote', 'TRANSPORT_TEST')[0])
                self.assertTrue(second._make_api_request('grades-consensus', 'TRANSPORT_TEST')[0])
                first.get_insider_trading('TRANSPORT_TEST')
                self.assertEqual(get.call_count, 3)
                self.assertEqual(limiter.call_count, 3)
                calls = get.call_args_list
                self.assertEqual(calls[0].kwargs['params']['apikey'], 'offline-session-one')
                self.assertEqual(calls[1].kwargs['params']['apikey'], 'offline-session-two')
                self.assertEqual(calls[2].kwargs['timeout'], 15)
        finally:
            cache.delete(key)

    def test_price_history_uses_stable_split_adjusted_close_and_cache(self):
        provider = fmp.FinancialModelingPrepProvider(api_key='offline-price-change')
        args = ('PRICE_TEST', '2026-01-01', '2026-01-08')
        key = provider.get_price_change_history.__cache_key__(provider, *args)
        cache.delete(key)
        response = Mock(status_code=200)
        response.json.return_value = [{'date':'2026-01-05','close':100,'adjClose':99,'unadjustedClose':200}]
        try:
            with patch.object(fmp.fmp_http_session, 'get', return_value=response) as get, patch.object(fmp.fmp_rate_limiter, 'wait_if_needed'):
                frame = provider.get_price_change_history(*args)
                self.assertEqual(frame.iloc[0]['Close'],100)
                self.assertIn('/stable/historical-price-eod/full',get.call_args.args[0])
                self.assertEqual(get.call_args.kwargs['params']['symbol'],'PRICE_TEST')
                self.assertEqual(get.call_args.kwargs['params']['to'],'2026-01-08')
                provider.get_price_change_history(*args)
                self.assertEqual(get.call_count,1)
        finally:
            cache.delete(key)
