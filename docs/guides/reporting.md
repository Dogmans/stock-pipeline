# Stock Pipeline Reporting System

Added: 2025-06-20

## Overview

The visualization system has been replaced with a text-based reporting system that focuses on generating concise reports of stocks that pass each screener strategy. The main benefits are:

1. Cleaner output with focused information on key metrics
2. Ranked results from best to worst by the most relevant metric for each screener
3. Markdown-based reports that can be viewed in any text editor or browser
4. Better compatibility with CI/CD pipelines and automated systems

## Report Structure

The screening report is structured as follows:

1. **Summary Section**: Overview of all strategies and stocks passing
   - Total unique stocks passing at least one screener
   - Table of strategies with stock count and top performer

2. **Strategy Sections**: Detailed results for each strategy
   - Tables sorted by the most relevant metric for that strategy
   - All key metrics included for comparison
   - Company sector information for context

## Example Usage

```powershell
# Run quick pipeline with SP500 universe and value+growth strategies
python main.py --universe sp500 --strategies value,growth

# Run full pipeline with all strategies
python main.py --full

# Check the output directory for reports
Get-Content .\output\screening_report.md
```

## Metrics Prioritization

Each strategy prioritizes different metrics for ranking:

- **Value**: Sorted by P/E ratio (ascending)
- **Growth**: Sorted by growth rate (descending)
- **Income**: Sorted by dividend yield (descending)
- **Mean Reversion**: Sorted by % below 52-week high (descending)

## Output Files

Two main output files are generated:

1. `screening_report.md`: Comprehensive report with all details
2. `summary.txt`: Quick overview of screening results
