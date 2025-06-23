# FMP API Endpoints for Company Metrics

Date: 2025-07-31

## Overview

During the refactoring of our stock screening pipeline, we needed to identify the correct Financial Modeling Prep API endpoints to retrieve company metrics needed for screening.

## Required Metrics

The following metrics were identified as needed but not all available in the `/profile` endpoint:

1. MarketCapitalization
2. PERatio
3. EPS
4. Beta
5. 52WeekHigh
6. 52WeekLow
7. LastDividendDate
8. PriceToBookRatio
9. PriceToSalesRatio

## Endpoint Investigation Results

After reviewing the FMP API documentation, we identified these endpoints as sources:

### `/profile/{symbol}`
- Contains: Beta, partial 52-week range, LastDividendDate (lastDiv)
- Also includes: sector, industry, company name, description
- Missing some key metrics like accurate PERatio

### `/quote/{symbol}`
- Contains: Latest market data including accurate PERatio, EPS
- Also includes precise 52WeekHigh and 52WeekLow as separate fields
- Updated more frequently than profile data

### `/market-capitalization/{symbol}`
- Contains: Most accurate and latest market capitalization value
- Also includes number of outstanding shares for calculations

### `/key-metrics/{symbol}`
- Contains: PriceToBookRatio, PriceToSalesRatio
- Also includes many other useful financial metrics
- Available in annual and quarterly versions

### `/ratios/{symbol}`
- Contains: Additional ratios like DebtToEquityRatio
- Useful as backup data source for some metrics

## Implementation Notes

1. We should modify `get_company_overview` to fetch from multiple endpoints
2. Caching should be applied to each endpoint separately to optimize refresh cycles
3. Quote data should be fetched first as it contains most of the time-sensitive metrics

## Example API Responses

### Sample `/quote` response for metrics
```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "price": 181.16,
  "changesPercentage": 0.12,
  "change": 0.22,
  "dayLow": 180.63,
  "dayHigh": 182.34,
  "yearHigh": 199.62,
  "yearLow": 124.17,
  "marketCap": 2847743898319,
  "priceAvg50": 176.95,
  "priceAvg200": 172.69,
  "volume": 51897634,
  "avgVolume": 59994196,
  "exchange": "NASDAQ",
  "open": 181.27,
  "previousClose": 180.94,
  "eps": 5.95,
  "pe": 30.40,
  "earningsAnnouncement": "2023-07-27T10:59:00.000Z",
  "sharesOutstanding": 15728700000,
  "timestamp": 1689974454
}
```

### Sample `/key-metrics` response for ratios
```json
{
  "symbol": "AAPL",
  "date": "2023-03-31",
  "period": "annual",
  "revenuePerShare": 22.85,
  "netIncomePerShare": 5.88,
  "operatingCashFlowPerShare": 7.64,
  "freeCashFlowPerShare": 6.93,
  "cashPerShare": 3.35,
  "bookValuePerShare": 3.58,
  "tangibleBookValuePerShare": 3.58,
  "shareholdersEquityPerShare": 3.58,
  "debtToEquity": 2.38,
  "debtToAssets": 0.69,
  "netDebtToEBITDA": 0.74,
  "currentRatio": 0.94,
  "interestCoverage": 33.22,
  "incomeQuality": 1.30,
  "dividendYield": 0.0058,
  "dividendPayoutRatio": 0.15,
  "priceToBookRatio": 45.25,
  "priceToSalesRatio": 7.18,
  "priceToEarningsRatio": 30.96,
  "priceToFreeCashFlowsRatio": 26.14,
  "priceEarningsToGrowthRatio": 2.51,
  "enterpriseValueMultiple": 22.53
}
```
