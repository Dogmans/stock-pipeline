"""Measure FMP HTTP time, throttle sleeps, and repeated-call caching in isolation.

Run from the repository root with --live to make a small number of API requests.
Only timing metadata is recorded; API keys and response bodies are never printed.
"""
import argparse
from collections import defaultdict
from contextlib import ExitStack
import json
import logging
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from unittest.mock import patch
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Allow live FMP read requests')
    parser.add_argument('--symbol', default='AAPL')
    parser.add_argument('--compare-session', action='store_true',
                        help='Compare three quote requests with and without connection reuse')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.live:
        parser.error('Pass --live to allow the diagnostic API requests')
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    destination = args.output.resolve() if args.output else None
    original_directory = Path.cwd()
    previous_logging_level = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    measurements = []
    requests_made = []
    real_sleep = time.sleep
    sleep_seconds = 0.0
    phase = ''

    def measured_sleep(seconds):
        nonlocal sleep_seconds
        started = time.perf_counter()
        real_sleep(seconds)
        sleep_seconds += time.perf_counter() - started

    with tempfile.TemporaryDirectory(prefix='fmp-diagnostic-') as temporary:
        os.chdir(temporary)
        try:
            # Import via the normal entry point to preserve the project's import order.
            import main as pipeline
            import requests
            from cache_config import cache
            from data_providers.financial_modeling_prep import FinancialModelingPrepProvider, fmp_http_session
            from utils.throttling import create_cache_checker

            provider = FinancialModelingPrepProvider()
            if not provider.api_key:
                raise RuntimeError('FMP API key is not configured')
            real_get = fmp_http_session.get

            def measured_get(url, **kwargs):
                parsed = urlsplit(url)
                if parsed.scheme != 'https' or parsed.hostname != 'financialmodelingprep.com':
                    raise RuntimeError('Diagnostic only permits the configured FMP HTTPS host')
                parts = parsed.path.strip('/').split('/')
                endpoint = parts[2] if parts[:2] == ['api', 'v3'] else '/'.join(parts)
                kwargs.setdefault('timeout', (5, 15))
                kwargs['allow_redirects'] = False
                started = time.perf_counter()
                status = 'exception'
                try:
                    response = real_get(url, **kwargs)
                    status = response.status_code
                    return response
                finally:
                    requests_made.append({'phase': phase, 'endpoint': endpoint,
                                          'status': status,
                                          'seconds': round(time.perf_counter() - started, 4)})

            def measure(name, function):
                nonlocal phase
                phase = name
                start_count = len(requests_made)
                start_sleep = sleep_seconds
                started = time.perf_counter()
                value = function()
                measurements.append({
                    'phase': name, 'elapsed_seconds': round(time.perf_counter() - started, 4),
                    'sleep_seconds': round(sleep_seconds - start_sleep, 4),
                    'http_calls': len(requests_made) - start_count,
                    'has_data': value is not None and len(value) > 0,
                })

            with ExitStack() as stack:
                stack.enter_context(patch.object(fmp_http_session, 'get', side_effect=measured_get))
                stack.enter_context(patch('time.sleep', side_effect=measured_sleep))
                for repetition in ('cold', 'repeat'):
                    measure(f'{repetition}:overview', lambda: provider.get_company_overview(args.symbol))
                    measure(f'{repetition}:history', lambda: provider.get_historical_prices([args.symbol], period='1y'))
                    measure(f'{repetition}:analyst_consensus', lambda: provider.get_analyst_grades_consensus(args.symbol))
                    measure(f'{repetition}:price_target', lambda: provider.get_price_target_consensus(args.symbol))
                second_provider = FinancialModelingPrepProvider()
                measure('new_provider:overview', lambda: second_provider.get_company_overview(args.symbol))
                measure('new_provider:history', lambda: second_provider.get_historical_prices([args.symbol], period='1y'))
                if args.compare_session:
                    real_get = requests.get
                    for number in range(3):
                        measure(f'fresh_connection:quote:{number + 1}',
                                lambda: provider._make_api_request('quote', args.symbol))
                    with requests.Session() as session:
                        real_get = session.get
                        for number in range(3):
                            measure(f'reused_session:quote:{number + 1}',
                                    lambda: provider._make_api_request('quote', args.symbol))

            # Check the manual cache probe against the actual DiskCache memoization key.
            actual_key = provider.get_company_overview.__cache_key__(provider, args.symbol)
            manual_check = create_cache_checker(cache, 'get_company_overview')
            cache_probes = {'actual_memoized_key_present': actual_key in cache,
                            'manual_throttle_cache_probe_hit': manual_check(provider, args.symbol)}
            by_endpoint = defaultdict(list)
            for request in requests_made:
                by_endpoint[request['endpoint']].append(request['seconds'])
            report = {
                'symbol': args.symbol, 'measurements': measurements, 'requests': requests_made,
                'cache_probes': cache_probes,
                'http_seconds': round(sum(row['seconds'] for row in requests_made), 4),
                'sleep_seconds': round(sleep_seconds, 4),
                'endpoint_median_seconds': {key: round(statistics.median(values), 4)
                                            for key, values in by_endpoint.items()},
            }
        finally:
            cache_module = sys.modules.get('cache_config')
            if cache_module is not None:
                cache_module.cache.close()
            logging.shutdown()
            logging.disable(previous_logging_level)
            os.chdir(original_directory)
    encoded = json.dumps(report, indent=2)
    if destination:
        destination.write_text(encoded + '\n', encoding='utf-8')
    print(encoded)


if __name__ == '__main__':
    main()
