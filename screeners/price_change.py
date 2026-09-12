"""Selectable-period split-adjusted price change, with auditable endpoints."""
from datetime import datetime, timezone, timedelta
import math
import pandas as pd
from .base_screener import BaseScreener


class PriceChangeScreener(BaseScreener):
    PERIODS = {'1w':5,'1mo':21,'3mo':63,'6mo':126,'1y':252}

    def __init__(self, period='3mo', custom_days=21, min_change=0.0, max_change=100.0):
        super().__init__()
        if period not in {*self.PERIODS, 'custom'}:
            raise ValueError('Choose 1w, 1mo, 3mo, 6mo, 1y or custom.')
        if isinstance(custom_days,bool) or not isinstance(custom_days,(int,float)) or not math.isfinite(custom_days) or int(custom_days)!=custom_days or not 1<=custom_days<=1260:
            raise ValueError('Custom trading sessions must be an integer between 1 and 1260.')
        if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in (min_change,max_change)) or min_change>max_change or min_change < -100:
            raise ValueError('Use finite minimum/maximum changes with -100 ≤ minimum ≤ maximum.')
        self.period,self.custom_days,self.min_change,self.max_change = period,int(custom_days),min_change,max_change
        self.trading_days = self.PERIODS.get(period,int(custom_days))

    def get_strategy_name(self):
        return 'Price Change'

    def get_strategy_description(self):
        return ('Split-adjusted closing-price change over a selected number of trading sessions. '
                'Includes the latest completed daily observation, excludes dividends, and checks an inclusive percentage range. '
                'Higher percentage changes receive higher percentile ranks; that does not imply better valuation.')

    def evaluate(self, frame, as_of=None):
        today = pd.Timestamp(as_of or datetime.now(timezone.utc).date())
        evidence = {'score':None,'trading_days':self.trading_days,'price_basis':'FMP split-adjusted daily close; excludes dividends',
                    'reason':'Price history is unavailable.'}
        if frame is None or frame.empty or not {'Date','Close'}.issubset(frame.columns):
            return evidence
        data = frame[['Date','Close']].copy()
        data['Date'] = pd.to_datetime(data['Date'],errors='coerce',utc=True).dt.tz_localize(None).dt.normalize()
        if data['Date'].isna().any() or data['Date'].duplicated().any():
            return {**evidence,'reason':'Price history contains missing or duplicate dates.'}
        data = data[data.Date < today].sort_values('Date')
        if len(data) < self.trading_days+1:
            return {**evidence,'reason':f'Need {self.trading_days+1} daily closes for {self.trading_days} sessions; only {len(data)} are available.'}
        window = data.iloc[-(self.trading_days+1):]
        prices = pd.to_numeric(window.Close,errors='coerce')
        if not all(pd.notna(v) and math.isfinite(v) and v>0 for v in prices):
            return {**evidence,'reason':'The selected period contains missing, nonpositive or nonfinite closing prices.'}
        if window.Date.diff().dt.days.max()>10:
            return {**evidence,'reason':'The selected price history contains a gap longer than 10 calendar days.'}
        start,end = float(prices.iloc[0]),float(prices.iloc[-1])
        change = (end/start-1)*100
        if not math.isfinite(change):
            return {**evidence,'reason':'Price change is nonfinite.'}
        return {**evidence,'score':change,'start_price':start,'end_price':end,
                'start_date':window.Date.iloc[0].date().isoformat(),'end_date':window.Date.iloc[-1].date().isoformat(),
                'reason':f'Price change {change:+.2f}% over {self.trading_days} sessions; allowed {self.min_change:g}% to {self.max_change:g}%: {"pass" if self.meets_threshold(change) else "fail"}.'}

    def calculate_score(self,data):
        return self.evaluate(data.get('prices'))['score']

    def meets_threshold(self,score):
        return score is not None and math.isfinite(score) and self.min_change <= score <= self.max_change

    def screen_stocks(self,universe_df):
        today = datetime.now(timezone.utc).date()
        start = today-timedelta(days=self.trading_days*2+30)
        rows = []
        for symbol in universe_df['symbol']:
            frame = self.provider.get_price_change_history(symbol,start.isoformat(),(today-timedelta(days=1)).isoformat())
            evidence = self.evaluate(frame,as_of=today)
            try:
                overview = self.provider.get_company_overview(symbol) or {}
            except Exception:
                overview = {}
            rows.append({'symbol':symbol,'company_name':overview.get('Name',symbol),'sector':overview.get('Sector','Unknown'),
                         'currency':overview.get('Currency'),**evidence,
                         'meets_threshold':self.meets_threshold(evidence['score']) if evidence['score'] is not None else None})
        return self.sort_results(pd.DataFrame(rows)) if rows else pd.DataFrame()

    def sort_results(self,frame):
        return frame.sort_values('score',ascending=False,na_position='last')
