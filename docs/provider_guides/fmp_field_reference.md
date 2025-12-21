# Financial Modeling Prep (FMP) API Field Reference

Quick reference guide for FMP API field names and common mistakes.

## 📋 Table of Contents

- [Company Overview](#company-overview)
- [Income Statement](#income-statement)
- [Balance Sheet](#balance-sheet)
- [Cash Flow](#cash-flow)
- [Historical Prices](#historical-prices)
- [Common Mistakes](#common-mistakes)

---

## Company Overview

**Method:** `provider.get_company_overview(symbol)`  
**Type:** `FMPCompanyOverview` (see `fmp_types.py`)

### Available Fields

```python
overview = provider.get_company_overview('AAPL')

# Basic Info
overview['Symbol']           # 'AAPL'
overview['Name']            # 'Apple Inc'
overview['Sector']          # 'Technology'
overview['Industry']        # 'Consumer Electronics'
overview['Description']     # Company description

# Market Data
overview['MarketCapitalization']  # Market cap in dollars
overview['SharesOutstanding']     # Shares outstanding
overview['Beta']                  # Beta coefficient

# Valuation Ratios
overview['PERatio']              # P/E ratio
overview['EPS']                  # Earnings per share
overview['PriceToBookRatio']     # P/B ratio
overview['PriceToSalesRatio']    # P/S ratio
overview['EVToEBITDA']           # EV/EBITDA
overview['DebtToEquityRatio']    # Debt to equity

# Profitability (⚠️ DECIMAL format: 0.30 = 30%)
overview['ReturnOnEquityTTM']    # ROE as decimal
overview['ReturnOnAssetsTTM']    # ROA as decimal
overview['ProfitMargin']         # Profit margin as decimal
overview['OperatingMarginTTM']   # Operating margin as decimal
overview['RevenueGrowth']        # Revenue growth as decimal

# Price Range
overview['52WeekHigh']           # 52-week high (string)
overview['52WeekLow']            # 52-week low (string)
```

### ⚠️ Not Available in Overview

```python
# CurrentRatio - Calculate from balance sheet instead:
balance = provider.get_balance_sheet(symbol)
latest = balance.iloc[0]
current_ratio = latest['totalCurrentAssets'] / latest['totalCurrentLiabilities']
```

---

## Income Statement

**Method:** `provider.get_income_statement(symbol)`  
**Type:** `pd.DataFrame` with `FMPIncomeStatement` rows

### Available Fields

```python
income = provider.get_income_statement('AAPL')
latest = income.iloc[0]

# Revenue (⚠️ Use 'totalRevenue' NOT 'revenue')
latest['totalRevenue']          # ✅ Correct
latest['revenue']               # ❌ Returns None

# Operating Metrics
latest['operatingIncome']       # Operating income
latest['netIncome']            # Net income
latest['operatingExpenses']    # Operating expenses

# Costs
latest['costOfRevenue']        # Cost of revenue
latest['grossProfit']          # Gross profit

# Margins
latest['grossProfitMargin']    # Gross profit margin

# Expenses
latest['researchAndDevelopmentExpenses']  # R&D expenses
latest['sellingGeneralAndAdministrativeExpenses']  # SG&A

# Calculate Operating Margin:
operating_margin = latest['operatingIncome'] / latest['totalRevenue']
```

---

## Balance Sheet

**Method:** `provider.get_balance_sheet(symbol)`  
**Type:** `pd.DataFrame` with `FMPBalanceSheet` rows

### Available Fields

```python
balance = provider.get_balance_sheet('AAPL')
latest = balance.iloc[0]

# Assets
latest['cash']                    # Cash
latest['totalCurrentAssets']      # Current assets
latest['totalAssets']            # Total assets

# Liabilities
latest['totalCurrentLiabilities']  # Current liabilities
latest['totalLiabilities']         # Total liabilities
latest['totalDebt']               # Total debt

# Equity (⚠️ Use these, NOT 'totalStockholdersEquity')
latest['totalEquity']              # ✅ Correct
latest['totalShareholderEquity']   # ✅ Also correct
latest['totalStockholdersEquity']  # ❌ Returns None

# Calculate Key Ratios:
current_ratio = latest['totalCurrentAssets'] / latest['totalCurrentLiabilities']
debt_to_equity = latest['totalDebt'] / latest['totalEquity']
```

---

## Cash Flow

**Method:** `provider.get_cash_flow(symbol)`  
**Type:** `pd.DataFrame` with `FMPCashFlow` rows

### Available Fields

```python
cash_flow = provider.get_cash_flow('AAPL')
latest = cash_flow.iloc[0]

# Operating Activities
latest['operatingCashflow']       # Operating cash flow
latest['netIncome']              # Net income

# Investing Activities
latest['capitalExpenditures']     # CapEx (usually negative)

# Free Cash Flow (⚠️ Check both spellings!)
fcf = latest.get('freeCashflow') or latest.get('freeCashFlow')

# Financing Activities
latest['dividendPayout']          # Dividends paid
latest['repurchaseOfStock']       # Stock buybacks
latest['issuanceOfStock']         # Stock issuance

# Other
latest['changeInCash']           # Change in cash
```

---

## Historical Prices

**Method:** `provider.get_historical_prices(symbols, period='1y')`  
**Type:** `Dict[str, pd.DataFrame]` with `FMPHistoricalPrice` rows

### ⚠️ CRITICAL: Column Names are CAPITALIZED

```python
prices = provider.get_historical_prices(['AAPL'], period='1y')
df = prices['AAPL']

# Correct (Capitalized)
df['Close']    # ✅
df['High']     # ✅
df['Low']      # ✅
df['Open']     # ✅
df['Volume']   # ✅

# Wrong (lowercase) - These will fail!
df['close']    # ❌
df['high']     # ❌
df['low']      # ❌
df['open']     # ❌
df['volume']   # ❌

# Usage Example
current_price = df['Close'].iloc[-1]
max_high = df['High'].max()
min_low = df['Low'].min()
```

---

## Common Mistakes

### ❌ Wrong → ✅ Correct

```python
# Income Statement
data.get('revenue')                    # ❌
data.get('totalRevenue')               # ✅

# Balance Sheet
data.get('totalStockholdersEquity')    # ❌
data.get('totalEquity')                # ✅
data.get('totalShareholderEquity')     # ✅ (alternative)

# Price History
df['close']                            # ❌
df['Close']                            # ✅

df['high']                             # ❌
df['High']                             # ✅

# Cash Flow (check both!)
data.get('freeCashflow')               # ✅ (might exist)
data.get('freeCashFlow')               # ✅ (might exist)
# Better:
fcf = data.get('freeCashflow') or data.get('freeCashFlow')

# Current Ratio (not in overview!)
overview.get('CurrentRatio')           # ❌ Returns None
# Calculate from balance sheet:
balance.iloc[0]['totalCurrentAssets'] / balance.iloc[0]['totalCurrentLiabilities']  # ✅

# ROE is decimal, not percentage
roe = overview['ReturnOnEquityTTM']    # 0.2964
roe_percent = roe * 100                # 29.64%
```

---

## Type Hints Usage

```python
from data_providers.fmp_types import FMPCompanyOverview, FMPBalanceSheet
import data_providers

provider = data_providers.get_provider('financial_modeling_prep')

# IDE will now autocomplete fields
overview: FMPCompanyOverview = provider.get_company_overview('AAPL')
sector = overview['Sector']  # Type-safe!

# For DataFrames, access rows as typed dicts
balance = provider.get_balance_sheet('AAPL')
latest_bs: FMPBalanceSheet = balance.iloc[0].to_dict()
equity = latest_bs['totalEquity']  # Type-safe!
```

---

## See Also

- **Complete type definitions:** [fmp_types.py](../data_providers/fmp_types.py)
- **Provider implementation:** [financial_modeling_prep.py](../data_providers/financial_modeling_prep.py)
- **Usage examples:** [composite_score.py](../screeners/composite_score.py)
