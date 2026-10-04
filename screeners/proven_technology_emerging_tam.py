"""Quantitative research-universe generation. No sector inclusion or thematic matching."""
import inspect
import math
from datetime import datetime, timezone
import pandas as pd

from .base_screener import BaseScreener
from data_providers.fmp_screening import FMPScreeningProvider


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def flag(value):
    return value if isinstance(value, bool) else {'true': True, 'false': False}.get(str(value).lower())


def history(frame, quarters):
    """Validate consecutive, same-currency observations before summing flow metrics."""
    if frame is None or frame.empty or 'fiscalDateEnding' not in frame:
        return None
    data = frame.sort_values('fiscalDateEnding', ascending=False).head(quarters).copy()
    if len(data) != quarters or data.fiscalDateEnding.duplicated().any():
        return None
    dates = pd.to_datetime(data.fiscalDateEnding, errors='coerce')
    if dates.isna().any() or len(set(data.get('reportedCurrency', []))) != 1:
        return None
    gaps = -dates.diff().dt.days.iloc[1:]
    if quarters > 1 and not gaps.between(60 if quarters >= 4 else 300, 120 if quarters >= 4 else 430).all():
        return None
    return data


def total(frame, field):
    values = [number(v) for v in frame.get(field, [])]
    return sum(values) if len(values) == len(frame) and all(v is not None for v in values) else None


class ProvenTechnologyEmergingTAMScreener(BaseScreener):
    opt_in = True
    multi_rule = True

    def __init__(self, min_market_cap=100_000_000, max_market_cap=2_500_000_000,
                 min_revenue=20_000_000, min_gross_margin_pct=20, min_revenue_growth_pct=-15,
                 min_daily_dollar_volume=100_000, min_runway_months=12,
                 max_ev_sales=8, max_debt_ebitda=4, max_dilution_pct=10,
                 max_statement_age_days=550, candidate_limit=250, near_miss_limit=100,
                 enrichment_buffer_pct=50,
                 exchanges='NASDAQ,NYSE,AMEX,TSX,TSXV', countries=''):
        super().__init__()
        self.provider = FMPScreeningProvider()
        values = locals().copy()
        for key in inspect.signature(type(self).__init__).parameters:
            if key == 'self':
                continue
            value = values[key]
            if key not in ('exchanges', 'countries'):
                if isinstance(value, bool) or number(value) is None:
                    raise ValueError(f'{key} must be finite.')
                if key != 'min_revenue_growth_pct' and value < 0:
                    raise ValueError(f'{key} must be nonnegative.')
                if key in ('candidate_limit', 'near_miss_limit', 'max_statement_age_days') and int(value) != value:
                    raise ValueError(f'{key} must be an integer.')
            elif not isinstance(value, str):
                raise ValueError(f'{key} must be comma-separated text.')
            setattr(self, key, value)
        if min_market_cap > max_market_cap or not 0 <= min_gross_margin_pct <= 100 or min_revenue_growth_pct < -100:
            raise ValueError('Invalid market-cap, margin or growth bounds.')
        self.settings = {k: getattr(self, k) for k in inspect.signature(type(self).__init__).parameters if k != 'self'}

    def get_strategy_name(self):
        return 'Proven Technology / Emerging TAM'

    def get_strategy_description(self):
        return 'Broad quantitative candidate universe for qualitative research. No thematic keywords or Technology-sector requirement. Score is research priority; eligibility uses all hard checks.'

    def rule_description(self):
        return {'metric': 'All quantitative eligibility checks', 'operator': 'all',
                'settings': self.settings, 'checks': [
                    {'metric': 'Market cap USD', 'operator': 'between', 'value': self.min_market_cap, 'upper_value': self.max_market_cap, 'parameter': 'min_market_cap', 'upper_parameter': 'max_market_cap'},
                    {'metric': 'Revenue USD', 'operator': 'gt', 'value': self.min_revenue, 'parameter': 'min_revenue'},
                    {'metric': 'Gross margin %', 'operator': 'gt', 'value': self.min_gross_margin_pct, 'parameter': 'min_gross_margin_pct'},
                    {'metric': 'Revenue growth %', 'operator': 'gt', 'value': self.min_revenue_growth_pct, 'parameter': 'min_revenue_growth_pct'},
                    {'metric': 'Estimated daily dollar volume', 'operator': 'gte', 'value': self.min_daily_dollar_volume, 'parameter': 'min_daily_dollar_volume'},
                    {'metric': 'Cash runway months (or positive operating cash flow)', 'operator': 'gte', 'value': self.min_runway_months, 'parameter': 'min_runway_months'},
                    {'metric': 'Statement age days', 'operator': 'lte', 'value': self.max_statement_age_days, 'parameter': 'max_statement_age_days'},
                ], 'note': f'Positive operating cash flow OR cash runway ≥ {self.min_runway_months:g} months. Exchanges: {self.exchanges or "all"}; countries: {self.countries or "all"}. Funds, financials, REITs, shells and exploration excluded. Missing required data goes to Unavailable. Leverage, dilution and EV/sales affect score only.'}

    def calculate_score(self, data):
        return self.evaluate(data)['score']

    def meets_threshold(self, score):
        # Eligibility is deliberately not inferred from the priority score.
        raise ValueError('This screen passes only when all hard checks pass.')

    def evaluate(self, data):
        metrics = data.get('metrics', {})
        profile = data.get('profile', {})
        rules = []
        def check(name, value, operator, threshold, passed, detail=None):
            status = 'unknown' if passed is None else 'pass' if passed else 'fail'
            rules.append({'rule': name, 'value': value, 'operator': operator, 'threshold': threshold,
                          'status': status, 'reason': detail or f'{name}: {value!r} {operator} {threshold!r} ({status})'})
        allowed = lambda text: {v.strip().upper() for v in text.split(',') if v.strip()}
        for name, field, setting in [('country', 'country', self.countries), ('exchange', 'exchange', self.exchanges)]:
            value = profile.get(field)
            check(name, value, 'in', sorted(allowed(setting)) or 'all', True if not setting else None if not value else value.upper() in allowed(setting))
        sector, industry = str(profile.get('sector') or '').lower(), str(profile.get('industry') or '').lower()
        excluded = sector in ('financial services', 'financials') or 'reit' in industry or industry in ('shell companies', 'blank check', 'uranium exploration', 'mineral exploration') or ('exploration' in industry and 'production' not in industry)
        etf, fund, active = (flag(profile.get(k)) for k in ('isEtf', 'isFund', 'isActivelyTrading'))
        security = False if excluded or etf is True or fund is True or active is False else None if etf is None or fund is None or active is None or not industry or not sector else True
        check('security_type', {'sector': sector, 'industry': industry, 'isEtf': etf, 'isFund': fund, 'active': active}, 'operating company', True, security)
        for name, field, op, threshold in [
            ('market_cap', 'market_cap_usd', 'between', [self.min_market_cap, self.max_market_cap]),
            ('revenue', 'revenue_usd', '>', self.min_revenue),
            ('gross_margin', 'gross_margin_pct', '>', self.min_gross_margin_pct),
            ('revenue_growth', 'revenue_growth_pct', '>', self.min_revenue_growth_pct),
            ('trading_liquidity', 'daily_dollar_volume_usd', '>=', self.min_daily_dollar_volume),
            ('statement_freshness', 'statement_age_days', '<=', self.max_statement_age_days),
        ]:
            value = number(metrics.get(field))
            passed = None if value is None else threshold[0] <= value <= threshold[1] if op == 'between' else value > threshold if op == '>' else value >= threshold if op == '>=' else 0 <= value <= threshold
            check(name, value, op, threshold, passed)
        ocf, runway = number(metrics.get('operating_cash_flow')), number(metrics.get('runway_months'))
        survival = True if ocf is not None and ocf > 0 or runway is not None and runway >= self.min_runway_months else None if ocf is None or ocf < 0 and runway is None else False
        check('financial_survivability', {'operating_cash_flow': ocf, 'runway_months': runway}, 'positive OCF OR runway >=', self.min_runway_months, survival)
        penalties = []
        for field, boundary, maximum in [('ev_sales', self.max_ev_sales, 20), ('debt_ebitda', self.max_debt_ebitda, 20), ('dilution_pct', self.max_dilution_pct, 15)]:
            value = number(metrics.get(field))
            points = 5 if value is None else min(maximum, max(0, value - boundary) / max(abs(boundary), 1) * maximum)
            penalties.append({'metric': field, 'value': value, 'threshold': boundary, 'points': points,
                              'reason': 'Missing metric' if value is None else 'Bounded excess penalty'})
        if metrics.get('nonpositive_ebitda_with_debt'):
            penalties.append({'metric': 'nonpositive_ebitda_with_debt', 'points': 15, 'reason': 'Debt with nonpositive EBITDA'})
        if metrics.get('current_ratio') is not None and metrics['current_ratio'] < 1:
            penalties.append({'metric': 'current_ratio', 'value': metrics['current_ratio'], 'points': 5, 'reason': 'Current ratio below 1'})
        failed = [r['rule'] for r in rules if r['status'] == 'fail']
        unknown = [r['rule'] for r in rules if r['status'] == 'unknown']
        outcome = 'failed' if failed else 'unavailable' if unknown else 'passed'
        score = max(0, 100 - sum(p['points'] for p in penalties))
        distance = 0
        for rule in rules:
            if rule['status'] != 'fail' or not isinstance(rule['value'], (int, float)):
                continue
            bounds = rule['threshold'] if isinstance(rule['threshold'], list) else [rule['threshold']]
            distance += min(abs(rule['value'] - b) / max(abs(b), 1) for b in bounds)
        structural = any(name in failed for name in ('country', 'exchange', 'security_type'))
        reason = '; '.join(r['reason'] for r in rules)
        if data.get('enrichment_skipped'):
            for rule in rules:
                if rule['status'] == 'unknown' and rule['rule'] not in ('country', 'exchange', 'security_type', 'market_cap', 'trading_liquidity'):
                    rule.update(status='not_evaluated', reason=data['enrichment_skipped'])
            reason = '; '.join(r['reason'] for r in rules)
            unknown = [r['rule'] for r in rules if r['status'] == 'unknown']
        return {**metrics, 'score': score, 'meets_threshold': True if outcome == 'passed' else False if outcome == 'failed' else None,
                'outcome': outcome, 'failed_rules': failed, 'unknown_rules': unknown, 'checks': rules,
                'penalties': penalties, 'effective_settings': self.settings, 'near_miss_distance': distance,
                'structural_exclusion': structural, 'reason': reason, 'data_warnings': data.get('warnings', [])}

    def load_data(self, symbol):
        data = {'profile': {}, 'metrics': {}, 'warnings': [], 'source_dates': {}}
        try:
            data['profile'] = self.provider.profile(symbol)
        except Exception:
            data['warnings'].append('Profile unavailable')
        p, m = data['profile'], data['metrics']
        def fx(currency):
            try:
                quote = self.provider.usd_rate(currency)
                data.setdefault('fx', {})[currency] = quote
                return quote['rate']
            except Exception:
                data['warnings'].append(f'USD conversion unavailable: {currency}')
                return None
        quote_fx = fx(p.get('currency'))
        m['quote_currency'] = p.get('currency')
        cap, price, volume = number(p.get('marketCap')), number(p.get('price')), number(p.get('averageVolume'))
        m.update(market_cap_local=cap, current_price=price, average_volume=volume,
                 market_cap_usd=cap * quote_fx if cap is not None and quote_fx is not None else None,
                 daily_dollar_volume_usd=price * volume * quote_fx if price is not None and volume is not None and quote_fx is not None else None)
        preliminary = self.evaluate(data)
        cap_usd = m.get('market_cap_usd')
        buffer = self.enrichment_buffer_pct / 100
        if preliminary['structural_exclusion'] or cap_usd is not None and (cap_usd < self.min_market_cap * max(0, 1 - buffer) or cap_usd > self.max_market_cap * (1 + buffer)):
            data['enrichment_skipped'] = f'Financial enrichment skipped: structural exclusion or market cap outside the {self.enrichment_buffer_pct:g}% boundary buffer.'
            data['source_dates']['profile'] = p.get('fetched_at')
            return data
        frames = {}
        for label, endpoint, count in [('income', 'income-statement', 8), ('cashflow', 'cash-flow-statement', 4), ('balance', 'balance-sheet-statement', 1)]:
            selected = None
            quarterly_partial = None
            for period, needed in [('quarter', count), ('annual', 2 if label == 'income' else 1)]:
                try:
                    frame = self.provider.statements(endpoint, symbol, period)
                    if label == 'income' and period == 'quarter':
                        quarterly_partial = history(frame, 4)
                    selected = history(frame, needed)
                    if selected is not None:
                        break
                except Exception:
                    pass
            if selected is None and quarterly_partial is not None:
                selected = quarterly_partial
                data['warnings'].append('Only four valid income quarters; year-over-year growth unavailable.')
            if selected is None:
                data['warnings'].append(f'{label} history unavailable or invalid')
            else:
                frames[label] = selected
                data.setdefault('raw_statements', {})[label] = json_records(selected)
                data['source_dates'][label] = {'date': selected.iloc[0].fiscalDateEnding.isoformat(),
                                             'currency': selected.iloc[0].reportedCurrency, 'basis': 'TTM' if len(selected) >= 4 else 'annual' if label != 'balance' else 'latest',
                                             'fetched_at': selected.attrs.get('fetched_at')}
        income = frames.get('income')
        if income is not None:
            current = income.head(4 if len(income) >= 4 else 1)
            previous = income.iloc[len(current):2 * len(current)]
            revenue, prior, gross = total(current, 'totalRevenue'), total(previous, 'totalRevenue'), total(current, 'grossProfit')
            rate = fx(current.iloc[0].reportedCurrency)
            m.update(revenue=revenue, reported_currency=current.iloc[0].reportedCurrency,
                     previous_revenue=prior, gross_profit=gross,
                     revenue_usd=revenue * rate if revenue is not None and rate is not None else None,
                     gross_margin_pct=gross / revenue * 100 if gross is not None and revenue is not None and revenue > 0 else None,
                     revenue_growth_pct=(revenue / prior - 1) * 100 if revenue is not None and prior is not None and prior > 0 else None,
                     ebitda=total(current, 'ebitda'), revenue_basis='TTM' if len(current) == 4 else 'annual')
            shares, old_shares = total(current, 'weightedAverageShsOutDil'), total(previous, 'weightedAverageShsOutDil')
            m['dilution_pct'] = (shares / old_shares - 1) * 100 if shares is not None and old_shares is not None and old_shares > 0 else None
        cf, balance = frames.get('cashflow'), frames.get('balance')
        if cf is not None:
            m['operating_cash_flow'] = total(cf, 'operatingCashflow')
            m['free_cash_flow'] = total(cf, 'freeCashflow')
        if balance is not None:
            b = balance.iloc[0]
            cash = number(b.get('cashAndShortTermInvestments'))
            if cash is None:
                base, investments = number(b.get('cash')), number(b.get('shortTermInvestments'))
                cash = base + (investments or 0) if base is not None else None
            debt = number(b.get('totalDebt'))
            assets, liabilities = number(b.get('totalCurrentAssets')), number(b.get('totalCurrentLiabilities'))
            m.update(cash=cash, total_debt=debt, short_term_debt=number(b.get('shortTermDebt')),
                     current_ratio=assets / liabilities if assets is not None and liabilities is not None and liabilities > 0 else None)
            same_income = income is not None and b.reportedCurrency == income.iloc[0].reportedCurrency
            if same_income and m.get('ebitda') is not None:
                m['debt_ebitda'] = debt / m['ebitda'] if debt is not None and m['ebitda'] > 0 else None
                m['nonpositive_ebitda_with_debt'] = debt is not None and debt > 0 and m['ebitda'] <= 0
            rate = fx(b.reportedCurrency)
            cap_usd, rev_usd = m.get('market_cap_usd'), m.get('revenue_usd')
            m['ev_sales'] = (cap_usd + (debt - cash) * rate) / rev_usd if all(v is not None for v in (cap_usd, debt, cash, rate, rev_usd)) and rev_usd > 0 else None
            m['ev_basis'] = 'Proxy: market cap + total debt - cash and short-term investments; current FX'
            if cf is not None and cf.iloc[0].reportedCurrency == b.reportedCurrency:
                ocf = m.get('operating_cash_flow')
                m['runway_months'] = cash / -ocf * 12 if cash is not None and cash >= 0 and ocf is not None and ocf < 0 else None
                fcf = m.get('free_cash_flow')
                m['fcf_runway_months'] = cash / -fcf * 12 if cash is not None and cash >= 0 and fcf is not None and fcf < 0 else None
        dates = [pd.Timestamp(v['date']) for v in data['source_dates'].values()]
        m['statement_age_days'] = (pd.Timestamp(datetime.now(timezone.utc).date()) - min(dates)).days if len(dates) == 3 else None
        data['source_dates']['profile'] = p.get('fetched_at')
        return data

    def screen_stocks(self, universe_df):
        rows = []
        for symbol in universe_df.symbol.drop_duplicates():
            data = self.load_data(symbol)
            p = data['profile']
            rows.append({'symbol': symbol, 'company_name': p.get('companyName', symbol), 'sector': p.get('sector'),
                         'industry': p.get('industry'), 'country': p.get('country'), 'exchange': p.get('exchange'),
                         'source_dates': data['source_dates'], 'fx': data.get('fx', {}), **self.evaluate(data)})
            rows[-1]['raw_statements'] = data.get('raw_statements', {})
        return self.sort_results(pd.DataFrame(rows)) if rows else pd.DataFrame()

    def sort_results(self, frame):
        return frame.sort_values(['score', 'symbol'], ascending=[False, True], na_position='last')


def json_records(frame):
    import json
    return json.loads(frame.to_json(orient='records', date_format='iso'))
