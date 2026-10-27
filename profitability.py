"""The video's four profitability traits, using reported quarterly statements.

Ratios are fractions here; screener scores convert them to percent / percentage
points. Closing balances deliberately match the video's definitions.
"""
from datetime import datetime, timezone
import logging

import pandas as pd

from research import number

logger = logging.getLogger(__name__)
METHOD = ('TTM = four consecutive reported quarters. ROE = TTM net income / closing '
          'shareholders’ equity; ROA = TTM net income / closing total assets; '
          'ROCE = TTM EBIT / (closing assets − current liabilities). '
          'EBIT = net income + income tax expense + interest expense when reported EBIT is absent. '
          'ROE change = current ROE − ROE at the same fiscal quarter three years earlier, in percentage points. '
          'Positive denominators and matching reported currencies are required. No annual or TTM vendor ratio is substituted.')
FIELDS = ('roe', 'roa', 'roce', 'roe_change_3y')


def statement_rows(frame):
    rows = {}
    if frame is None or frame.empty:
        return rows
    for row in frame.to_dict('records'):
        date = next((parsed for key in ('fiscalDateEnding', 'date')
                     if pd.notna(parsed := pd.to_datetime(row.get(key), errors='coerce', utc=True))), None)
        if date is not None:
            rows.setdefault(date.date().isoformat(), row)
    return rows


def first(row, *keys):
    return next((v for key in keys if (v := number(row.get(key))) is not None), None)


def ebit(row):
    reported = first(row, 'ebit')
    if reported is not None:
        return reported
    components = [first(row, key) for key in ('netIncome', 'incomeTaxExpense', 'interestExpense')]
    return sum(components) if all(v is not None for v in components) else None


def calculate_profitability(income, balance):
    incomes, balances = statement_rows(income), statement_rows(balance)
    dates = sorted(incomes)
    history = []
    for index, date in enumerate(dates):
        closing, current = balances.get(date), incomes[date]
        row = {'date': date, 'fiscal_period': current.get('period') if isinstance(current.get('period'), str) else None,
               'currency': current.get('reportedCurrency') if isinstance(current.get('reportedCurrency'), str) else None,
               **dict.fromkeys(FIELDS), 'roe_3y_ago': None, 'comparison_date': None,
               'net_income_ttm': None, 'ebit_ttm': None, 'reasons': {}}
        quarters = [incomes[d] for d in dates[max(0, index-3):index+1]]
        quarter_dates = dates[max(0, index-3):index+1]
        consecutive = (len(quarters) == 4 and all(
            65 <= (pd.Timestamp(quarter_dates[i+1])-pd.Timestamp(quarter_dates[i])).days <= 115
            for i in range(3)) and
            [q.get('period') for q in quarters] in [
                ['Q1', 'Q2', 'Q3', 'Q4'], ['Q2', 'Q3', 'Q4', 'Q1'],
                ['Q3', 'Q4', 'Q1', 'Q2'], ['Q4', 'Q1', 'Q2', 'Q3']])
        currencies = [q.get('reportedCurrency') for q in quarters] + [closing.get('reportedCurrency') if closing else None]
        aligned = all(isinstance(c, str) and c for c in currencies) and len(set(currencies)) == 1
        if not consecutive or closing is None or not aligned:
            reason = ('Four consecutive fiscal quarters are required.' if not consecutive else
                      'Matching closing balance sheet is missing.' if closing is None else
                      'Income and balance currencies are missing or do not match.')
            row['reasons'].update(dict.fromkeys(('roe', 'roa', 'roce'), reason))
        else:
            profits = [first(q, 'netIncome') for q in quarters]
            earnings = [ebit(q) for q in quarters]
            profit = number(sum(profits)) if all(v is not None for v in profits) else None
            earnings = number(sum(earnings)) if all(v is not None for v in earnings) else None
            assets = first(closing, 'totalAssets')
            equity = first(closing, 'totalShareholderEquity', 'totalStockholdersEquity', 'totalEquity')
            liabilities = first(closing, 'totalCurrentLiabilities')
            capital = number(assets - liabilities) if assets is not None and liabilities is not None else None
            row.update(net_income_ttm=profit, ebit_ttm=earnings, equity=equity,
                       assets=assets, current_liabilities=liabilities, capital_employed=capital,
                       quarter_dates=quarter_dates,
                       filed_at=next((current.get(k) for k in ('filingDate', 'fillingDate') if isinstance(current.get(k), str)), None))
            for metric, numerator, denominator in [('roe', profit, equity), ('roa', profit, assets), ('roce', earnings, capital)]:
                value = number(numerator / denominator) if numerator is not None and denominator is not None and denominator > 0 else None
                row[metric] = value
                if value is None:
                    row['reasons'][metric] = 'TTM profit or a positive closing denominator is unavailable.'
        prior = next((old for old in reversed(history)
                      if 1060 <= (pd.Timestamp(date)-pd.Timestamp(old['date'])).days <= 1130
                      and current.get('period') == old['fiscal_period']), None)
        if prior:
            row.update(roe_3y_ago=prior['roe'], comparison_date=prior['date'])
        if prior and prior['roe'] is not None and row['roe'] is not None and row['currency'] == prior['currency']:
            row['roe_change_3y'] = number(row['roe'] - prior['roe'])
        else:
            row['reasons']['roe_change_3y'] = 'Comparable TTM ROE at the same fiscal quarter three years earlier is unavailable.'
        history.append(row)
    return history


def profitability(provider, symbol, strict=False):
    frames, missing = {}, []
    for statement in ('income', 'balance'):
        try:
            frames[statement] = provider.get_research_statements(symbol, statement, annual=False)
        except Exception:
            if strict:
                raise
            logger.exception('Profitability %s unavailable for %s', statement, symbol)
            frames[statement] = pd.DataFrame()
        if frames[statement] is None or frames[statement].empty:
            missing.append(statement)
    history = calculate_profitability(frames['income'], frames['balance'])
    return {'symbol': symbol, 'latest': history[-1] if history else None, 'history': history,
            'missing': missing, 'methodology': METHOD, 'source': 'FMP reported quarterly income and balance statements',
            'retrieved_at': datetime.now(timezone.utc).isoformat()}
