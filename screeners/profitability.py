"""Independently configurable screens for the four Investor52 traits."""
import math

import pandas as pd

from .base_screener import BaseScreener
from profitability import profitability, METHOD


class ProfitabilityScreener(BaseScreener):
    opt_in = True
    metric = 'roe'
    label = 'TTM Return on Equity'
    strict_improvement = False

    def __init__(self, min_percent=15.0):
        super().__init__()
        if not math.isfinite(min_percent):
            raise ValueError('Profitability threshold must be finite.')
        self.min_percent = min_percent

    def get_strategy_name(self):
        return self.label

    def get_strategy_description(self):
        return METHOD + ' Score units: ' + ('percentage points.' if self.strict_improvement else 'percent.')

    def calculate_score(self, data):
        value = (data.get('latest') or {}).get(self.metric)
        score = value * 100 if value is not None else None
        return score if score is not None and math.isfinite(score) else None

    def meets_threshold(self, score):
        return score is not None and math.isfinite(score) and (
            score > self.min_percent if self.strict_improvement else score >= self.min_percent)

    def sort_results(self, frame):
        return frame.sort_values('score', ascending=False, na_position='last')

    def screen_stocks(self, universe_df):
        rows = []
        for symbol in universe_df['symbol']:
            data = profitability(self.provider, symbol, strict=True)
            latest = data['latest'] or {}
            score = self.calculate_score(data)
            passed = self.meets_threshold(score) if score is not None else None
            unit, op = ('pp', '>') if self.strict_improvement else ('%', '≥')
            rows.append({'symbol': symbol, 'score': score, 'meets_threshold': passed,
                         'reason': (f'{self.label}: {score:.2f}{unit} {op} {self.min_percent:g}{unit}: '
                                    f'{"pass" if passed else "fail"}. Period {latest.get("date")}.' if score is not None else
                                    latest.get('reasons', {}).get(self.metric, 'Quarterly statements unavailable.')),
                         'profitability': latest, 'profitability_history': data['history'],
                         'methodology': METHOD})
        return pd.DataFrame(rows).sort_values('score', ascending=False, na_position='last') if rows else pd.DataFrame()


class ReturnOnAssetsScreener(ProfitabilityScreener):
    metric = 'roa'
    label = 'TTM Return on Assets'

    def __init__(self, min_percent=10.0):
        super().__init__(min_percent)


class ReturnOnCapitalEmployedScreener(ProfitabilityScreener):
    metric = 'roce'
    label = 'TTM Return on Capital Employed'

    def __init__(self, min_percent=30.0):
        super().__init__(min_percent)


class ReturnOnEquityTrendScreener(ProfitabilityScreener):
    metric = 'roe_change_3y'
    label = 'ROE Improvement over Three Years'
    strict_improvement = True

    def __init__(self, min_percent=0.0):
        super().__init__(min_percent)
