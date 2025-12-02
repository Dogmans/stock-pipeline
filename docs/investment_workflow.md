# Investment Workflow & Strategy Guide

This document outlines a methodical approach to using the Stock Pipeline screeners within a broader professional investment process.

## The "Idea Funnel" Methodology

Do not use screeners in isolation. Use them as the filtering mechanism between **Macro Ideas** and **Micro Analysis**.

### Step 1: Macro & Secular Trend Identification (Top-Down)

Before running code, identify the current market regime.

| Market Regime | Characteristics | Recommended Screeners |
| :--- | :--- | :--- |
| **Early Cycle / Recovery** | Low rates, improving growth | `small_cap_value` (Russell2000), `turnaround_candidates` |
| **Mid Cycle / Momentum** | Strong earnings, stable rates | `momentum`, `analyst_sentiment_momentum`, `growth_at_reasonable_price` |
| **Late Cycle / Defensive** | High inflation, slowing growth | `quality`, `fcf_yield`, `dividend_growth` |
| **Bear Market / Crash** | Panic selling, high volatility | `historic_value`, `fifty_two_week_lows`, `cash_rich` |

### Step 2: Quantitative Screening (The Pipeline)

Execute the pipeline based on the regime identified above.

#### Example: The "Fear & Value" Routine
*Use when the market has dropped 5-10%.*
```powershell
# Find high-quality companies trading below historic norms
python main.py --universe sp500 --strategies historic_value quality --limit 20
```

#### Example: The "Institutional Momentum" Routine
*Use when the market is breaking out to new highs.*
```powershell
# Find stocks analysts are upgrading that have price momentum
python main.py --universe sp500 --strategies analyst_sentiment_momentum momentum --limit 20
```

#### Example: The "Cash Cow" Routine
*Use for income-focused or defensive portfolio construction.*
```powershell
# Find companies generating massive cash relative to price
python main.py --universe sp500 --strategies fcf_yield enhanced_quality --limit 20
```

### Step 3: Qualitative Deep Dive (The Human Element)

The screener output is your **Watchlist**, not your Buy list. Perform these checks on the top 3-5 results:

1.  **Earnings Call Review**: Read the transcript of the last earnings call. Are management confident? Are they dodging questions?
2.  **Insider Alignment**: Check `insider_buying` data. Is management buying their own stock?
3.  **Competitive Advantage**: Does the company have pricing power? (Check Gross Margins in the `quality` screener output).

### Step 4: Technical Execution

Use the `market_data` module to ensure you aren't fighting the trend.

1.  Check `is_market_in_correction()` status.
2.  If market is in correction, wait for a "Follow Through Day" (strong buying volume) before deploying capital into screener results.

## Daily Routine Checklist

1.  **08:00 AM**: Check Macro (Bond Yields, VIX, Sector Rotation).
2.  **09:00 AM**: Formulate a hypothesis (e.g., "Tech is oversold").
3.  **04:30 PM**: Run specific pipeline strategies to test hypothesis.
4.  **05:30 PM**: Review generated Markdown reports.
5.  **05:30 PM**: Add 1-2 best candidates to TradingView/Watchlist for technical monitoring.
