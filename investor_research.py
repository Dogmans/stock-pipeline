"""Small, source-labelled adapters for the investor workspace; no invented observations."""
from datetime import datetime, timedelta, timezone
import logging

import pandas as pd

from research import number

logger = logging.getLogger(__name__)


def safe_url(value):
    return value if isinstance(value, str) and value.startswith(('https://', 'http://')) else None


def iso_date(value):
    parsed = pd.to_datetime(value, errors='coerce', utc=True)
    return None if pd.isna(parsed) else parsed.date().isoformat()


def first_date(row, keys):
    return next((value for key in keys if (value := iso_date(row.get(key))) is not None), None)


FIELDS = {
    'income': {
        'revenue': ['totalRevenue', 'revenue'], 'gross_profit': ['grossProfit'],
        'operating_income': ['operatingIncome'], 'ebitda': ['ebitda'],
        'net_income': ['netIncome'], 'eps': ['epsDiluted', 'eps'],
        'diluted_shares': ['weightedAverageShsOutDil'],
        'tax_expense': ['incomeTaxExpense'], 'pretax_income': ['incomeBeforeTax'],
        'interest_expense': ['interestExpense'],
    },
    'balance': {
        'cash': ['cash', 'cashAndCashEquivalents'], 'debt': ['totalDebt'],
        'equity': ['totalShareholderEquity', 'totalEquity', 'totalStockholdersEquity'],
        'assets': ['totalAssets'], 'current_assets': ['totalCurrentAssets'],
        'current_liabilities': ['totalCurrentLiabilities'],
        'short_term_investments': ['shortTermInvestments'],
        'minority_interest': ['minorityInterest'], 'preferred_stock': ['preferredStock'],
    },
    'cash_flow': {
        'operating_cash_flow': ['operatingCashflow', 'netCashProvidedByOperatingActivities', 'operatingCashFlow'],
        'capex': ['capitalExpenditures', 'capitalExpenditure'],
        'free_cash_flow': ['freeCashflow', 'freeCashFlow'],
        'stock_compensation': ['stockBasedCompensation'],
        'depreciation': ['depreciationAndAmortization'],
        'dividends': ['dividendPayout', 'dividendsPaid', 'commonDividendsPaid'],
        'buybacks': ['repurchaseOfStock', 'commonStockRepurchased', 'stockRepurchased'],
    },
}

GROWTH_SOURCES = {metric: statement for statement, fields in FIELDS.items() for metric in fields}
GROWTH_SOURCES.update({'net_debt': 'balance', 'current_ratio': 'balance',
                       'fcf_per_share': 'cash_flow', 'cash_conversion': 'cash_flow'})
MARGIN_FIELDS = ['gross_profit_margin', 'operating_income_margin', 'net_income_margin', 'free_cash_flow_margin']
ESTIMATE_FIELDS = {
    'revenue_low': ['revenueLow', 'estimatedRevenueLow'], 'revenue_high': ['revenueHigh', 'estimatedRevenueHigh'],
    'revenue_avg': ['revenueAvg', 'estimatedRevenueAvg'], 'eps_low': ['epsLow', 'estimatedEpsLow'],
    'eps_high': ['epsHigh', 'estimatedEpsHigh'], 'eps_avg': ['epsAvg', 'estimatedEpsAvg'],
    'analysts': ['numAnalystsRevenue', 'numberAnalystEstimatedRevenue'],
}


def first_number(row, keys):
    return next((value for key in keys if (value := number(row.get(key))) is not None), None)


def ratio(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def financials(provider, symbol, annual=True):
    periods, missing, warnings = {}, [], []
    for statement, fields in FIELDS.items():
        try:
            frame = provider.get_research_statements(symbol, statement, annual=annual)
            if frame is None or frame.empty:
                missing.append(statement)
                continue
            # Prefer the first observation if the vendor returns duplicate/restated dates.
            seen = set()
            for _, row in frame.iterrows():
                date = first_date(row, ['fiscalDateEnding', 'date'])
                if not date or date in seen:
                    continue
                seen.add(date)
                period = periods.setdefault(date, {'date': date, 'sources': {}})
                currency = row.get('reportedCurrency')
                currency = currency if isinstance(currency, str) and currency else None
                known_currencies = {source['currency'] for source in period['sources'].values() if source['currency']}
                if currency and known_currencies and currency not in known_currencies:
                    warnings.append(f'{date}: statements have different currencies; {statement} excluded.')
                    continue
                # Do not infer an income statement's currency from a balance sheet.
                if currency and ('income' not in period['sources'] or period.get('currency')):
                    period['currency'] = currency
                if statement == 'income' or 'fiscal_period' not in period:
                    fiscal_period = row.get('period')
                    period['fiscal_period'] = fiscal_period if isinstance(fiscal_period, str) and fiscal_period else ('FY' if annual else 'Quarter')
                period['sources'][statement] = {
                    'filed_at': first_date(row, ['filingDate', 'fillingDate']),
                    'url': safe_url(row.get('finalLink')) or safe_url(row.get('link')),
                    'currency': currency,
                }
                for field, keys in fields.items():
                    period[field] = first_number(row, keys)
        except Exception:
            logger.exception('Research statements unavailable: %s %s', symbol, statement)
            missing.append(statement)
    rows = sorted(periods.values(), key=lambda row: row['date'])
    for row in rows:
        if row.get('capex') is not None:
            row['capex'] = abs(row['capex'])
        if row.get('free_cash_flow') is None and row.get('operating_cash_flow') is not None and row.get('capex') is not None:
            row['free_cash_flow'] = row['operating_cash_flow'] - row['capex']
        income_currency = row['sources'].get('income', {}).get('currency')
        cash_currency = row['sources'].get('cash_flow', {}).get('currency')
        aligned_cash = income_currency and income_currency == cash_currency
        for metric in ['gross_profit', 'operating_income', 'net_income', 'free_cash_flow']:
            row[metric + '_margin'] = ratio(row.get(metric), row.get('revenue')) if metric != 'free_cash_flow' or aligned_cash else None
        row['net_debt'] = row['debt'] - row['cash'] if row.get('debt') is not None and row.get('cash') is not None else None
        row['fcf_per_share'] = ratio(row.get('free_cash_flow'), row.get('diluted_shares')) if aligned_cash else None
        row['cash_conversion'] = ratio(row.get('free_cash_flow'), row.get('net_income')) if aligned_cash else None
        row['current_ratio'] = ratio(row.get('current_assets'), row.get('current_liabilities'))
        row['yoy'], row['yoy_pp'] = {}, {}
        # Compare full fiscal years / the same quarter, never adjacent quarters.
        date = datetime.fromisoformat(row['date'])
        prior = next((old for old in reversed(rows) if 330 <= (date - datetime.fromisoformat(old['date'])).days <= 400
                      and old.get('currency') and old.get('currency') == row.get('currency')
                      and (annual or row['fiscal_period'] in ('Q1', 'Q2', 'Q3', 'Q4')
                           and old['fiscal_period'] == row['fiscal_period'])), None)
        if prior:
            for metric, statement in GROWTH_SOURCES.items():
                current, previous = row.get(metric), prior.get(metric)
                currency = row['sources'].get(statement, {}).get('currency')
                matching = currency and currency == prior['sources'].get(statement, {}).get('currency')
                # Negative/zero denominators are not meaningful percentage growth.
                row['yoy'][metric] = current / previous - 1 if matching and current is not None and previous is not None and previous > 0 else None
            for metric in MARGIN_FIELDS:
                current, previous = row.get(metric), prior.get(metric)
                row['yoy_pp'][metric] = current - previous if current is not None and previous is not None else None
    return {'symbol': symbol, 'period': 'annual' if annual else 'quarter', 'periods': rows,
            'missing': missing, 'warnings': warnings, 'source': 'FMP reported financial statements',
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'methodology': 'FCF = operating cash flow less absolute capex; this is reported levered cash flow, not FCFF. Growth compares the same fiscal period a year earlier; nonpositive bases are unavailable.'}


def prices(provider, symbol):
    today = datetime.now(timezone.utc).date()
    try:
        frame = provider.get_price_change_history(symbol, (today - timedelta(days=3653)).isoformat(), today.isoformat())
        records = []
        for _, row in frame.iterrows():
            date, close = first_date(row, ['Date', 'date']), first_number(row, ['Close', 'close'])
            if date and close is not None and close > 0:
                records.append({'date': date, 'close': close, 'volume': first_number(row, ['Volume', 'volume'])})
        records = sorted({row['date']: row for row in records}.values(), key=lambda row: row['date'])
        return {'symbol': symbol, 'prices': records, 'source': 'FMP daily split-adjusted closes; excludes dividends', 'missing': not bool(records)}
    except Exception:
        logger.exception('Research prices unavailable for %s', symbol)
        return {'symbol': symbol, 'prices': [], 'missing': True, 'source': 'FMP daily split-adjusted closes'}


def evidence(provider, symbol, kind):
    """Optional datasets fail independently and are fetched only when their tab opens."""
    try:
        if kind == 'earnings':
            raw = provider.get_earnings_reports(symbol)
            rows = [{'date': iso_date(r.get('date')), 'eps_actual': number(r.get('epsActual')),
                     'eps_estimate': number(r.get('epsEstimated')), 'revenue_actual': number(r.get('revenueActual')),
                     'revenue_estimate': number(r.get('revenueEstimated')), 'updated_at': iso_date(r.get('lastUpdated'))} for r in raw]
            for r in rows:
                for metric in ['eps', 'revenue']:
                    actual, estimate = r[metric + '_actual'], r[metric + '_estimate']
                    r[metric + '_surprise'] = (actual - estimate) / abs(estimate) if actual is not None and estimate not in (None, 0) else None
        elif kind == 'estimates':
            frame = provider.get_analyst_estimates(symbol, period='annual')
            rows = []
            for _, r in frame.iterrows():
                rows.append({'date': iso_date(r.get('date')),
                    **{field: first_number(r, keys) for field, keys in ESTIMATE_FIELDS.items()}})
        elif kind == 'filings':
            rows = [{'date': first_date(r, ['filingDate', 'fillingDate']),
                     'form': r.get('formType') or r.get('type') or 'Filing',
                     'url': safe_url(r.get('finalLink')) or safe_url(r.get('link'))}
                    for r in provider.get_research_filings(symbol)]
        else:
            raise ValueError('Unknown dataset')
        rows = sorted((r for r in rows if r.get('date')), key=lambda r: r['date'], reverse=True)
        return {'symbol': symbol, 'rows': rows, 'missing': not bool(rows), 'source': f'FMP {kind}',
                'retrieved_at': datetime.now(timezone.utc).isoformat()}
    except Exception:
        logger.exception('Research %s unavailable for %s', kind, symbol)
        return {'symbol': symbol, 'rows': [], 'missing': True, 'source': f'FMP {kind}',
                'message': 'Unavailable from your FMP plan, no coverage, or a provider error. Other research remains available.'}
