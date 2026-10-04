"""Isolated stable FMP access for discovery screens; legacy consumers are unchanged."""
import math
import time
from datetime import datetime, timezone

import pandas as pd

from cache_config import cache
from .financial_modeling_prep import FinancialModelingPrepProvider, fmp_http_session, fmp_rate_limiter


class FMPScreeningProvider(FinancialModelingPrepProvider):
    @cache.memoize(expire=24 * 3600)
    def fetch(self, endpoint, symbol=None, period=None, limit=None, exchange=None, page=None, allow_empty=False):
        params = {'apikey': self.api_key}
        params.update({k: v for k, v in {'symbol': symbol, 'period': period, 'limit': limit, 'exchange': exchange, 'page': page}.items() if v is not None})
        for attempt in range(3):
            fmp_rate_limiter.wait_if_needed()
            response = fmp_http_session.get(f'{self.stable_base_url}/{endpoint}', params=params, timeout=(5, 20))
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                try:
                    delay = float(response.headers.get('Retry-After', 2 ** attempt))
                except (TypeError, ValueError):
                    delay = 2 ** attempt
                time.sleep(min(30, max(0, delay)))
                continue
            # Avoid exposing API keys through requests' URL-containing exceptions.
            if response.status_code != 200:
                raise RuntimeError(f'FMP {endpoint} unavailable (HTTP {response.status_code}).')
            data = response.json()
            if not isinstance(data, list) or (not data and not allow_empty):
                raise RuntimeError(f'FMP {endpoint} returned no records.')
            return {'records': data, 'fetched_at': datetime.now(timezone.utc).isoformat()}

    def profile(self, symbol):
        response = self.fetch('profile', symbol)
        return {**response['records'][0], 'fetched_at': response['fetched_at']}

    def statements(self, endpoint, symbol, period='quarter'):
        response = self.fetch(endpoint, symbol, period=period, limit=8 if period == 'quarter' else 3)
        mappings = {
            'income-statement': {'revenue': 'totalRevenue', 'grossProfitRatio': 'grossProfitMargin'},
            'balance-sheet-statement': {'cashAndCashEquivalents': 'cash', 'totalStockholdersEquity': 'totalShareholderEquity'},
            'cash-flow-statement': {'netCashProvidedByOperatingActivities': 'operatingCashflow', 'freeCashFlow': 'freeCashflow'},
        }
        frame = self._process_financial_statement(response['records'], mappings[endpoint])
        frame.attrs['fetched_at'] = response['fetched_at']
        return frame

    def usd_rate(self, currency):
        if currency == 'USD':
            return {'rate': 1.0, 'pair': 'USDUSD', 'fetched_at': None}
        if not isinstance(currency, str) or len(currency) != 3 or not currency.isupper():
            raise RuntimeError('Missing or unsupported currency code.')
        for pair, inverse in ((currency + 'USD', False), ('USD' + currency, True)):
            try:
                quote = self.fetch('quote', pair)
                price = float(quote['records'][0]['price'])
                if math.isfinite(price) and price > 0:
                    return {'rate': 1 / price if inverse else price, 'pair': pair, 'fetched_at': quote['fetched_at']}
            except (RuntimeError, KeyError, TypeError, ValueError):
                continue
        raise RuntimeError(f'USD conversion unavailable for {currency}.')

    def listing_universe(self):
        # No cap/volume prefilter: preserve honest funnel counts and boundary misses.
        records = []
        for exchange in ('NASDAQ', 'NYSE', 'AMEX', 'TSX', 'TSXV'):
            seen = set()
            for page in range(100):
                response = self.fetch('company-screener', exchange=exchange, page=page, limit=1000, allow_empty=True)
                rows = response['records']
                symbols = {row.get('symbol') for row in rows}
                if rows and not symbols - seen:
                    raise RuntimeError(f'FMP repeated a listing page for {exchange}; coverage cannot be verified.')
                seen.update(symbols)
                records.extend(rows)
                if len(rows) < 1000:
                    break
            else:
                raise RuntimeError(f'FMP listing pagination exceeded the bound for {exchange}.')
        frame = pd.DataFrame(records)
        if 'symbol' not in frame:
            raise RuntimeError('FMP listing universe has no symbols.')
        frame = frame.dropna(subset=['symbol']).drop_duplicates('symbol')
        if 'exchangeShortName' in frame:
            frame['exchange'] = frame['exchangeShortName']
        # Explicit discovery scope; do not substitute an index or ETF universe.
        if 'exchange' not in frame:
            raise RuntimeError('FMP listing response lacks exchange metadata; discovery coverage cannot be verified.')
        frame = frame[frame['exchange'].isin(['NASDAQ', 'NYSE', 'AMEX', 'TSX', 'TSXV'])].copy()
        frame['security'] = frame['name'] if 'name' in frame else frame['symbol']
        return frame
