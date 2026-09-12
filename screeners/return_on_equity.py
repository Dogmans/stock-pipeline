"""Annual ROE using aligned statements and positive, meaningful equity bases."""
import math
import pandas as pd
from .base_screener import BaseScreener


class ReturnOnEquityScreener(BaseScreener):
    def __init__(self, min_roe=15.0, min_equity_ratio=5.0):
        super().__init__()
        if not math.isfinite(min_roe):
            raise ValueError('Minimum ROE must be finite.')
        if not math.isfinite(min_equity_ratio) or not 0 <= min_equity_ratio <= 100:
            raise ValueError('Minimum equity / assets must be between 0 and 100%.')
        self.min_roe = min_roe
        self.min_equity_ratio = min_equity_ratio

    def get_strategy_name(self):
        return 'Return on Equity'

    def get_strategy_description(self):
        return ('Annual net income / average shareholders’ equity, expressed as a percentage. '
                'Checks positive equity and minimum average equity / assets; includes annual history. '
                'ROE also contributes to Quality and Enhanced Quality, so combining their ranking weights increases its influence.')

    @staticmethod
    def periods(frame):
        if frame is None or frame.empty or 'fiscalDateEnding' not in frame:
            return {}
        values = {}
        for record in frame.to_dict('records'):
            date = pd.to_datetime(record.get('fiscalDateEnding'), errors='coerce')
            if pd.notna(date):
                values.setdefault(date.date().isoformat(), record)
        return values

    def evaluate(self, income, balance):
        incomes, balances = self.periods(income), self.periods(balance)
        dates = sorted(incomes, reverse=True)[:5]
        history = []
        for date in dates:
            row = {'period':date, 'roe':None, 'equity_ratio':None}
            closing = balances.get(date)
            prior_dates = [d for d in balances if 300 <= (pd.Timestamp(date)-pd.Timestamp(d)).days <= 430]
            opening = balances[max(prior_dates)] if prior_dates else None
            statement = incomes[date]
            row['currency'] = statement.get('reportedCurrency') if isinstance(statement.get('reportedCurrency'),str) else None
            profit = self.safe_float(statement.get('netIncome'))
            if closing is None or opening is None or profit is None:
                row['reason'] = 'Missing net income or matching consecutive annual equity balances.'
            else:
                currencies = [s.get('reportedCurrency') for s in (statement,closing,opening)]
                if not all(isinstance(c,str) and c for c in currencies) or len(set(currencies)) != 1:
                    row['reason'] = 'Statement currencies are missing or do not match.'
                    history.append(row)
                    continue
                def equity(s):
                    return next((self.safe_float(s.get(k)) for k in ('totalShareholderEquity','totalStockholdersEquity') if self.safe_float(s.get(k)) is not None),None)
                start, end = equity(opening), equity(closing)
                start_assets, end_assets = self.safe_float(opening.get('totalAssets')), self.safe_float(closing.get('totalAssets'))
                if start is None or end is None:
                    row['reason'] = 'Shareholders’ equity is unavailable.'
                elif start <= 0 or end <= 0:
                    row['reason'] = 'Nonpositive opening or closing equity makes ROE unsuitable for ranking.'
                elif start_assets is None or end_assets is None or start_assets <= 0 or end_assets <= 0:
                    row['reason'] = 'Positive asset balances are required to check the equity base.'
                else:
                    average = start/2+end/2
                    row.update(net_income=profit, average_equity=average,
                               equity_ratio=100*(average/(start_assets/2+end_assets/2)))
                    raw_roe = (profit/average)*100
                    if row['equity_ratio'] < self.min_equity_ratio:
                        row['reason'] = f"Small equity base: average equity / assets {row['equity_ratio']:.2f}% < {self.min_equity_ratio:g}%."
                    elif not math.isfinite(raw_roe):
                        row['reason'] = 'ROE calculation is nonfinite.'
                    else:
                        row['roe'] = raw_roe
                        row['reason'] = f'Annual ROE {raw_roe:.2f}% ≥ {self.min_roe:g}%: {"pass" if self.meets_threshold(raw_roe) else "fail"}.'
            history.append(row)
        latest = history[0] if history else {'roe':None,'reason':'Annual income statements are unavailable.'}
        recent = history[:3]
        return {**latest,'roe_history':history,
                'roe_three_year_average':sum(r['roe'] for r in recent)/3 if len(recent)==3 and all(r['roe'] is not None for r in recent) and all(300 <= (pd.Timestamp(recent[i]['period'])-pd.Timestamp(recent[i+1]['period'])).days <= 430 for i in (0,1)) else None}

    def calculate_score(self, data):
        return self.evaluate(data.get('income'),data.get('balance'))['roe']

    def meets_threshold(self, score):
        return score is not None and math.isfinite(score) and score >= self.min_roe

    def screen_stocks(self, universe_df):
        rows = []
        for symbol in universe_df['symbol']:
            # Provider errors propagate to the workflow's separate Error outcome.
            income = self.provider.get_income_statement(symbol,annual=True)
            balance = self.provider.get_balance_sheet(symbol,annual=True)
            evidence = self.evaluate(income,balance)
            try:
                overview = self.provider.get_company_overview(symbol) or {}
            except Exception:
                overview = {}
            rows.append({'symbol':symbol,'company_name':overview.get('Name',symbol),
                         'sector':overview.get('Sector','Unknown'),'score':evidence['roe'],
                         'meets_threshold':self.meets_threshold(evidence['roe']) if evidence['roe'] is not None else None,
                         'outcome':'unavailable' if evidence['roe'] is None else 'passed' if self.meets_threshold(evidence['roe']) else 'failed',
                         'debt_to_equity':self.safe_float(overview.get('DebtToEquityRatio')),
                         **evidence})
        return self.sort_results(pd.DataFrame(rows)) if rows else pd.DataFrame()

    def sort_results(self, frame):
        return frame.sort_values('score',ascending=False,na_position='last')
