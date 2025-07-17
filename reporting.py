"""
reporting.py - Text-based reporting module for stock screening results

This module replaces visualization-based outputs with text-based reports
that list stocks passing each screener, ranked by relevant metrics.
"""

import os
import pandas as pd
from datetime import datetime

def generate_screening_report(screening_results, output_path):
    """
    Generate a comprehensive markdown report of screening results.
    
    Args:
        screening_results: Dictionary of DataFrames with screening results by strategy
        output_path: Path where the markdown report will be saved
        
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
                elif 'growth_rate' in results.columns:
                    key_metric = f"Growth: {results.iloc[0]['growth_rate']:.2%}"
                elif 'sharpe_ratio' in results.columns:
                    key_metric = f"Sharpe: {results.iloc[0]['sharpe_ratio']:.2f}"
                
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
            # Determine key metrics based on strategy type
            key_metrics = []
            if 'pe_ratio' in results.columns:
                key_metrics.append('pe_ratio')
            if 'pb_ratio' in results.columns:
                key_metrics.append('pb_ratio')
            if 'price_to_book' in results.columns:
                key_metrics.append('price_to_book')
            if 'dividend_yield' in results.columns:
                key_metrics.append('dividend_yield')
            if 'pct_off_high' in results.columns:
                key_metrics.append('pct_off_high')
            if 'pct_above_low' in results.columns:
                key_metrics.append('pct_above_low')
            if 'growth_rate' in results.columns:
                key_metrics.append('growth_rate')
                
            # Create table header
            f.write("| Symbol | Company Name | Sector |")
            for metric in key_metrics:
                f.write(f" {metric.replace('_', ' ').title()} |")
            f.write("\n")
            
            f.write("|--------|--------------|--------|")
            for _ in key_metrics:
                f.write("----------|")
            f.write("\n")
              # Write table rows
            for _, row in results.iterrows():
                f.write(f"| {row['symbol']} | {row['company_name']} | {row.get('sector', 'N/A')} |")
                for metric in key_metrics:
                    if metric in row:
                        if metric == 'price_to_book':
                            f.write(f" {row[metric]:.3f} |")
                        elif 'ratio' in metric:
                            f.write(f" {row[metric]:.2f} |")
                        elif 'yield' in metric:
                            f.write(f" {row[metric]:.2%} |")
                        elif 'rate' in metric:
                            f.write(f" {row[metric]:.2%} |")
                        elif 'pct' in metric:
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
| Dividend Yield | Annual dividend / Current price | Higher values indicate better income potential |
| Pct Off High | Percentage below 52-week high | Higher values may indicate undervaluation |
| Pct Above Low | Percentage above 52-week low | Lower values may indicate buying opportunity |
| Growth Rate | Revenue or earnings growth rate | Higher values indicate stronger growth |
"""
