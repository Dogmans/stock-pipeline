"""
reporting.py - Text-based reporting module for stock screening results

This module replaces visualization-based outputs with text-based reports
that list stocks passing each screener, ranked by relevant metrics.
"""

import os
import pandas as pd
from datetime import datetime
import importlib

def passing_results(results):
    """Filter scored rows; legacy results without a flag are already screened."""
    if not isinstance(results, pd.DataFrame):
        return pd.DataFrame()
    if 'meets_threshold' in results.columns:
        return results.loc[results['meets_threshold'].eq(True).fillna(False)]
    return results


def generate_summary_report(screening_results, output_path, universe, universe_size,
                            market_status, display_limit=20, errors=None):
    """Write the same passing candidates and display limit as the Markdown report."""
    if display_limit < 0:
        raise ValueError('display_limit must be nonnegative')
    errors = errors or {}
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('Stock Screening Pipeline - Summary Report\n')
        f.write(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
        f.write(f'Universe: {universe} ({universe_size} stocks)\n')
        f.write(f'Market Status: {market_status}\n\n')
        f.write('Top Candidates by Strategy:\n')
        for strategy, results in screening_results.items():
            f.write(f'\n{strategy}:\n')
            if strategy in errors:
                f.write('  Screening failed; results are unavailable. See the run log for details.\n')
                continue
            passing = passing_results(results)
            f.write(f'  Stocks passing: {len(passing)}\n')
            if passing.empty:
                f.write('  No stocks passed this screener.\n')
                continue
            displayed = passing if display_limit == 0 else passing.head(display_limit)
            for _, row in displayed.iterrows():
                f.write(f"  {row['symbol']}: {row.get('score', '')} {row.get('reason', '')}\n")
    return output_path


def get_strategy_description(strategy_name):
    """
    Dynamically get strategy description from the appropriate screener module.
    
    Args:
        strategy_name (str): The name of the strategy (e.g., 'pe_ratio', 'momentum')
    
    Returns:
        str: The strategy description or a fallback description
    """
    # Map strategy names to module names
    module_mapping = {
        '52_week_lows': 'screeners.fifty_two_week_lows',
        'pe_ratio': 'screeners.pe_ratio',
        'price_to_book': 'screeners.price_to_book',
        'peg_ratio': 'screeners.peg_ratio',
        'momentum': 'screeners.momentum',
        'quality': 'screeners.quality',
        'enhanced_quality': 'screeners.enhanced_quality',
        'free_cash_flow_yield': 'screeners.free_cash_flow_yield',
        'sharpe_ratio': 'screeners.sharpe_ratio',
        'insider_buying': 'screeners.insider_buying',
        'fallen_ipos': 'screeners.fallen_ipos',
        'turnaround_candidates': 'screeners.turnaround_candidates',
        'sector_corrections': 'screeners.sector_corrections',
        # Combined screeners handled separately
        'combined': 'screeners.combined',
        'traditional_value': 'screeners.combined',
        'high_performance': 'screeners.combined',
        'comprehensive': 'screeners.combined',
        'distressed_value': 'screeners.combined'
    }
    
    try:
        module_name = module_mapping.get(strategy_name)
        if module_name:
            module = importlib.import_module(module_name)
            
            # For combined screeners, use the STRATEGY_DESCRIPTIONS dictionary
            if strategy_name in ['combined', 'traditional_value', 'high_performance', 'comprehensive', 'distressed_value']:
                if hasattr(module, 'STRATEGY_DESCRIPTIONS'):
                    descriptions = getattr(module, 'STRATEGY_DESCRIPTIONS')
                    return descriptions.get(strategy_name, f'Analysis results for {strategy_name.replace("_", " ")} screening strategy.')
            else:
                # For individual screeners, use STRATEGY_DESCRIPTION constant
                if hasattr(module, 'STRATEGY_DESCRIPTION'):
                    return getattr(module, 'STRATEGY_DESCRIPTION')
        
        # Fallback description
        return f'Analysis results for {strategy_name.replace("_", " ")} screening strategy.'
    
    except (ImportError, AttributeError) as e:
        # Fallback in case of import or attribute errors
        return f'Analysis results for {strategy_name.replace("_", " ")} screening strategy.'

def generate_screening_report(screening_results, output_path, display_limit=20, errors=None):
    """
    Generate a comprehensive markdown report of screening results.
    
    Args:
        screening_results: Dictionary of DataFrames with screening results by strategy
        output_path: Path where the markdown report will be saved
        display_limit: Maximum number of stocks to display per strategy (default 20)
            Zero displays all passing stocks.
        errors: Optional mapping of failed strategy names to error details.
        
    Returns:
        Path to the generated report
    """
    if display_limit < 0:
        raise ValueError('display_limit must be nonnegative')
    errors = errors or {}
    scored_counts = {
        name: len(rows) if isinstance(rows, pd.DataFrame) else 0
        for name, rows in screening_results.items()
    }
    screening_results = {
        name: passing_results(rows) for name, rows in screening_results.items()
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write report header
        f.write(f"# Stock Screening Results Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Summary section
        f.write("## Summary\n\n")
        
        total_stocks = set()
        for strategy, results in screening_results.items():
            if isinstance(results, pd.DataFrame) and not results.empty:
                total_stocks.update(results['symbol'].tolist())
                
        f.write(f"Total unique stocks passing at least one screener: **{len(total_stocks)}**\n\n")
        
        f.write("| Strategy | Stocks Scored | Stocks Passing | Top Stock | Key Metric |\n")
        f.write("|----------|---------------|----------------|-----------|------------|\n")
        
        for strategy, results in screening_results.items():
            if strategy in errors:
                f.write(f"| {strategy} | - | unavailable | - | Failed |\n")
                continue
            if isinstance(results, pd.DataFrame) and not results.empty:
                top_stock = results.iloc[0]['symbol']
                available_metrics = results.iloc[0].dropna().index
                  # Identify key metric based on strategy
                key_metric = ""
                if strategy == 'historic_value' and 'pe_discount_pct' in available_metrics:
                    # Special handling for historic value strategy
                    pe_current = results.iloc[0].get('pe_ratio')
                    pe_historic = results.iloc[0].get('pe_historic') 
                    pe_discount = results.iloc[0].get('pe_discount_pct')
                    if pe_current and pe_historic and pe_discount:
                        key_metric = f"P/E: {pe_current:.1f} vs {pe_historic:.1f} ({pe_discount:.0f}% off)"
                    elif 'pb_discount_pct' in available_metrics:
                        pb_discount = results.iloc[0].get('pb_discount_pct')
                        if pb_discount:
                            key_metric = f"Value discount: {pb_discount:.0f}%"
                elif 'pe_ratio' in available_metrics:
                    key_metric = f"P/E: {results.iloc[0]['pe_ratio']:.2f}"
                elif 'pct_off_high' in available_metrics:
                    key_metric = f"{results.iloc[0]['pct_off_high']:.1f}% off high"
                elif 'price_to_book' in available_metrics:
                    key_metric = f"P/B: {results.iloc[0]['price_to_book']:.3f}"
                elif 'dividend_yield' in available_metrics:
                    key_metric = f"Yield: {results.iloc[0]['dividend_yield']:.2%}"
                elif 'peg_ratio' in available_metrics:
                    key_metric = f"PEG: {results.iloc[0]['peg_ratio']:.2f}"
                elif 'growth_rate' in available_metrics:
                    key_metric = f"Growth: {results.iloc[0]['growth_rate']:.1f}%"
                elif 'sharpe_ratio' in available_metrics:
                    key_metric = f"Sharpe: {results.iloc[0]['sharpe_ratio']:.2f}"
                elif 'momentum_score' in available_metrics:
                    key_metric = f"Momentum: {results.iloc[0]['momentum_score']:.1f}%"
                elif 'quality_score' in available_metrics:
                    key_metric = f"Quality: {results.iloc[0]['quality_score']}/10"
                elif 'fcf_yield' in available_metrics:
                    key_metric = f"FCF Yield: {results.iloc[0]['fcf_yield']:.1f}%"
                
                if not key_metric and 'score' in available_metrics:
                    key_metric = f"Score: {results.iloc[0]['score']:.2f}"

                f.write(f"| {strategy} | {scored_counts[strategy]} | {len(results)} | {top_stock} | {key_metric} |\n")
            else:
                f.write(f"| {strategy} | {scored_counts[strategy]} | 0 | - | - |\n")
                
        f.write("\n")
        
        if errors:
            f.write("## Failed Screeners\n\n")
            for strategy in errors:
                f.write(f"- {strategy}: failed; passing results are unavailable. See the run log for details.\n")
            f.write("\n")

        # Detailed results by strategy
        for strategy, results in screening_results.items():
            f.write(f"## {strategy.replace('_', ' ').title()} Strategy\n\n")
            
            # Get strategy description dynamically from the screener module
            description = get_strategy_description(strategy)
            f.write(f"{description}\n\n")
            
            if strategy in errors:
                f.write("Screening failed; results are unavailable. See the run log for details.\n\n")
                continue
            if not isinstance(results, pd.DataFrame) or results.empty:
                f.write("No stocks passed this screener.\n\n")
                continue
            
            display_results = results if display_limit == 0 else results.head(display_limit)
            if len(display_results) < len(results):
                f.write(f"**Showing top {len(display_results)} of {len(results)} passing stocks**\n\n")

            # Determine key metrics based on strategy type
            key_metrics = []
            if 'pe_ratio' in display_results.columns:
                key_metrics.append('pe_ratio')
            if 'pb_ratio' in display_results.columns:
                key_metrics.append('pb_ratio')
            if 'price_to_book' in display_results.columns:
                key_metrics.append('price_to_book')
            if 'dividend_yield' in display_results.columns:
                key_metrics.append('dividend_yield')
            if 'pct_off_high' in display_results.columns:
                key_metrics.append('pct_off_high')
            if 'pct_above_low' in display_results.columns:
                key_metrics.append('pct_above_low')
            if 'peg_ratio' in display_results.columns:
                key_metrics.append('peg_ratio')
            if 'growth_rate' in display_results.columns:
                key_metrics.append('growth_rate')
            if 'sharpe_ratio' in display_results.columns:
                key_metrics.append('sharpe_ratio')
            if 'momentum_score' in display_results.columns:
                key_metrics.append('momentum_score')
            if 'quality_score' in display_results.columns:
                key_metrics.append('quality_score')
            if 'fcf_yield' in display_results.columns:
                key_metrics.append('fcf_yield')
            
            # Add historic value specific metrics if this is historic value screener
            historic_value_metrics = []
            if strategy == 'historic_value' and any(col in display_results.columns for col in ['pe_historic', 'pb_historic', 'ev_ebitda_historic']):
                if 'pe_historic' in display_results.columns:
                    historic_value_metrics.extend(['pe_ratio', 'pe_historic', 'pe_discount_pct'])
                if 'pb_historic' in display_results.columns:
                    historic_value_metrics.extend(['pb_ratio', 'pb_historic', 'pb_discount_pct'])
                if 'ev_ebitda_historic' in display_results.columns:
                    historic_value_metrics.extend(['ev_ebitda', 'ev_ebitda_historic', 'ev_discount_pct'])
                # Replace standard metrics with historic value specific ones
                key_metrics = historic_value_metrics
                
            # Create table header
            f.write("| Symbol | Company Name | Sector |")
            for metric in key_metrics:
                header_name = metric.replace('_', ' ').title()
                if metric.endswith('_historic'):
                    header_name = header_name.replace(' Historic', ' (Hist Avg)')
                elif metric.endswith('_discount_pct'):
                    header_name = header_name.replace(' Discount Pct', ' Discount')
                f.write(f" {header_name} |")
            f.write("\n")
            
            f.write("|--------|--------------|--------|")
            for _ in key_metrics:
                f.write("----------|")
            f.write("\n")
              # Write table rows using display_results
            for _, row in display_results.iterrows():
                # Handle missing company_name (use security from ETF holdings as fallback)
                company_name = row.get('company_name', row.get('security', 'N/A'))
                # Handle missing sector (use gics_sector as fallback)
                sector = row.get('sector', row.get('gics_sector', 'N/A'))
                f.write(f"| {row['symbol']} | {company_name} | {sector} |")
                for metric in key_metrics:
                    if metric in row and pd.notna(row[metric]):
                        # Special formatting for historic value metrics
                        if metric.endswith('_historic'):
                            f.write(f" {row[metric]:.2f} |")
                        elif metric.endswith('_discount_pct'):
                            if row[metric] is not None:
                                f.write(f" {row[metric]:.1f}% |")
                            else:
                                f.write(" - |")
                        elif metric == 'price_to_book':
                            f.write(f" {row[metric]:.3f} |")
                        elif metric == 'peg_ratio':
                            f.write(f" {row[metric]:.2f} |")
                        elif 'ratio' in metric:
                            f.write(f" {row[metric]:.2f} |")
                        elif 'yield' in metric:
                            f.write(f" {row[metric]:.2%} |")
                        elif 'rate' in metric and 'growth' in metric:
                            f.write(f" {row[metric]:.1f}% |")
                        elif 'rate' in metric:
                            f.write(f" {row[metric]:.2%} |")
                        elif 'pct' in metric:
                            f.write(f" {row[metric]:.1f}% |")
                        elif metric == 'sharpe_ratio':
                            f.write(f" {row[metric]:.2f} |")
                        elif metric == 'momentum_score':
                            f.write(f" {row[metric]:.1f}% |")
                        elif metric == 'quality_score':
                            f.write(f" {row[metric]}/10 |")
                        elif metric == 'fcf_yield':
                            f.write(f" {row[metric]:.1f}% |")
                        else:
                            f.write(f" {row[metric]} |")
                    else:
                        f.write(" - |")
                f.write("\n")
                
            f.write("\n")
            
    return output_path

def generate_metrics_definitions():
    """
    Return markdown text explaining the metrics used in the report.
    """
    return """## Metrics Definitions

| Metric | Definition | Interpretation |
|--------|------------|----------------|
| P/E Ratio | Price to Earnings Ratio | Lower values typically indicate better value |
| P/B Ratio | Price to Book Ratio | Lower values typically indicate better value |
| PEG Ratio | Price/Earnings to Growth Ratio | Lower values indicate better value relative to growth |
| Dividend Yield | Annual dividend / Current price | Higher values indicate better income potential |
| Pct Off High | Percentage below 52-week high | Higher values may indicate undervaluation |
| Pct Above Low | Percentage above 52-week low | Lower values may indicate buying opportunity |
| Growth Rate | Revenue or earnings growth rate | Higher values indicate stronger growth |
"""
