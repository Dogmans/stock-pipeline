"""
reporting.py - Text-based reporting module for stock screening results

This module replaces visualization-based outputs with text-based reports
that list stocks passing each screener, ranked by relevant metrics.
"""

import os
import pandas as pd
from datetime import datetime

def generate_screening_report(screening_results, output_path, display_limit=20):
    """
    Generate a comprehensive markdown report of screening results.
    
    Args:
        screening_results: Dictionary of DataFrames with screening results by strategy
        output_path: Path where the markdown report will be saved
        display_limit: Maximum number of stocks to display per strategy (default 20)
        
    Returns:
        Path to the generated report
    """
    with open(output_path, 'w') as f:
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
        
        f.write("| Strategy | Stocks Passing | Top Stock | Key Metric |\n")
        f.write("|----------|----------------|-----------|------------|\n")
        
        for strategy, results in screening_results.items():
            if isinstance(results, pd.DataFrame) and not results.empty:
                top_stock = results.iloc[0]['symbol']
                  # Identify key metric based on strategy
                key_metric = ""
                if 'pe_ratio' in results.columns:
                    key_metric = f"P/E: {results.iloc[0]['pe_ratio']:.2f}"
                elif 'pct_off_high' in results.columns:
                    key_metric = f"{results.iloc[0]['pct_off_high']:.1f}% off high"
                elif 'price_to_book' in results.columns:
                    key_metric = f"P/B: {results.iloc[0]['price_to_book']:.3f}"
                elif 'dividend_yield' in results.columns:
                    key_metric = f"Yield: {results.iloc[0]['dividend_yield']:.2%}"
                elif 'peg_ratio' in results.columns:
                    key_metric = f"PEG: {results.iloc[0]['peg_ratio']:.2f}"
                elif 'growth_rate' in results.columns:
                    key_metric = f"Growth: {results.iloc[0]['growth_rate']:.1f}%"
                elif 'sharpe_ratio' in results.columns:
                    key_metric = f"Sharpe: {results.iloc[0]['sharpe_ratio']:.2f}"
                elif 'momentum_score' in results.columns:
                    key_metric = f"Momentum: {results.iloc[0]['momentum_score']:.1f}%"
                elif 'quality_score' in results.columns:
                    key_metric = f"Quality: {results.iloc[0]['quality_score']}/10"
                elif 'fcf_yield' in results.columns:
                    key_metric = f"FCF Yield: {results.iloc[0]['fcf_yield']:.1f}%"
                
                f.write(f"| {strategy} | {len(results)} | {top_stock} | {key_metric} |\n")
            else:
                f.write(f"| {strategy} | 0 | - | - |\n")
                
        f.write("\n")
        
        # Detailed results by strategy
        for strategy, results in screening_results.items():
            f.write(f"## {strategy.replace('_', ' ').title()} Strategy\n\n")
            
            if not isinstance(results, pd.DataFrame) or results.empty:
                f.write("No stocks passed this screener.\n\n")
                continue
            
            # Apply the same filtering logic as the text summary
            # For individual screeners (not combined), filter by meets_threshold if available
            if strategy != 'combined' and 'meets_threshold' in results.columns:
                # Get only stocks meeting the threshold
                filtered_results = results[results['meets_threshold'] == True]
                
                # If fewer than 5 stocks meet the threshold, show top N instead
                if len(filtered_results) < 5:
                    # For display, apply the display limit to full results
                    display_results = results.head(display_limit)
                else:
                    # Otherwise show all that meet threshold (up to the display limit)
                    display_results = filtered_results.head(display_limit)
            else:
                # Special case: If limit is 0, show all results
                if display_limit == 0:
                    display_results = results
                else:
                    # For combined screener, use a smaller default limit
                    if strategy == 'combined':
                        max_display = min(display_limit if display_limit else 10, len(results))
                    else:
                        # For non-combined screeners without meets_threshold, use the normal display limit
                        max_display = display_limit
                    display_results = results.head(max_display)
            
            # Show filtering info
            if len(display_results) < len(results):
                f.write(f"**Showing top {len(display_results)} of {len(results)} stocks**\n\n")
            
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
                
            # Create table header
            f.write("| Symbol | Company Name | Sector |")
            for metric in key_metrics:
                f.write(f" {metric.replace('_', ' ').title()} |")
            f.write("\n")
            
            f.write("|--------|--------------|--------|")
            for _ in key_metrics:
                f.write("----------|")
            f.write("\n")
              # Write table rows using display_results
            for _, row in display_results.iterrows():
                f.write(f"| {row['symbol']} | {row['company_name']} | {row.get('sector', 'N/A')} |")
                for metric in key_metrics:
                    if metric in row:
                        if metric == 'price_to_book':
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
