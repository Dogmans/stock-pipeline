"""Shared, JSON-safe research-screen selection and audit exports."""
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd


def build_audit(screener, records, evaluate_benchmarks=True):
    records = json.loads(pd.DataFrame(records).to_json(orient='records', date_format='iso')) if records else []
    by_symbol = {r['symbol']: r for r in records}
    benchmarks = {}
    for symbol in ('HIMX', 'LTRX', 'PNG.V'):
        row = by_symbol.get(symbol)
        if row is None and evaluate_benchmarks:
            row = json.loads(screener.screen_stocks(pd.DataFrame({'symbol': [symbol]})).to_json(orient='records'))[0]
        row = row or {}
        benchmarks[symbol] = {'pass': row.get('meets_threshold'), 'score': row.get('score'),
                              'failed_rules': row.get('failed_rules', []), 'unknown_rules': row.get('unknown_rules', []),
                              'in_initial_universe': symbol in by_symbol, 'evidence': row}
    survivors = sorted([r for r in records if r.get('outcome') == 'passed'], key=lambda r: (-r['score'], r['symbol']))
    misses = sorted([r for r in records if r.get('outcome') in ('failed', 'unavailable') and not r.get('structural_exclusion')],
                    key=lambda r: (len(r.get('failed_rules', [])) + len(r.get('unknown_rules', [])) + sum(c['status'] == 'not_evaluated' for c in r.get('checks', [])),
                                   r.get('near_miss_distance', 0), -r.get('score', 0), r['symbol']))
    candidates, near_misses = survivors[:int(screener.candidate_limit)], misses[:int(screener.near_miss_limit)]
    summary = {'run_date': datetime.now(timezone.utc).date().isoformat(), 'data_provider': 'Financial Modeling Prep',
               'initial_universe_count': len(records), 'effective_settings': screener.settings,
               'eligibility_policy': screener.rule_description(),
               'final_candidate_count': len(candidates), 'near_miss_count': len(near_misses),
               'unselected_survivor_count': len(survivors) - len(candidates), 'benchmark_results': benchmarks,
               'unavailable_count': sum(r.get('outcome') == 'unavailable' for r in records),
               'error_count': sum(r.get('outcome') == 'error' for r in records),
               'count_basis': 'Sequential funnel; benchmark-only evaluations excluded.'}
    remaining = records
    for rule, key in [('country', 'country_eligible_count'), ('exchange', 'exchange_eligible_count'),
                      ('security_type', 'security_type_eligible_count'), ('market_cap', 'market_cap_pass_count'),
                      ('revenue', 'revenue_pass_count'), ('gross_margin', 'gross_margin_pass_count'),
                      ('revenue_growth', 'revenue_growth_pass_count'), ('trading_liquidity', 'trading_liquidity_pass_count'),
                      ('statement_freshness', 'statement_freshness_pass_count'), ('financial_survivability', 'financial_survivability_pass_count')]:
        remaining = [r for r in remaining if any(c['rule'] == rule and c['status'] == 'pass' for c in r.get('checks', []))]
        summary[key] = len(remaining)
    summary['all_hard_filters_pass_count'] = len(survivors)
    selected, review = {r['symbol'] for r in candidates}, {r['symbol'] for r in near_misses}
    for row in records:
        row['selection_reason'] = ('Selected candidate' if row['symbol'] in selected else 'Selected near miss for review' if row['symbol'] in review else
                                   'Passed; outside candidate limit' if row.get('outcome') == 'passed' else 'Retained in audit; outside near-miss selection')
    return {'summary': summary, 'candidates': candidates, 'near_misses': near_misses, 'audit': records}


def write_audit(audit, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for key, value in audit.items():
        (destination / f'proven_technology_emerging_tam_{key}.json').write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
