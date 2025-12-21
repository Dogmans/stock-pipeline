"""
Type definitions for Financial Modeling Prep API responses.

This module provides TypedDict definitions for all data structures returned by
the FMP provider, making it easier to understand what fields are available and
their expected types.

Usage in code:
    from data_providers.fmp_types import FMPCompanyOverview, FMPIncomeStatement
    
    overview: FMPCompanyOverview = provider.get_company_overview('AAPL')
    # IDE will now autocomplete available fields
    sector = overview['Sector']
    pe_ratio = overview['PERatio']
"""

from typing import TypedDict, Optional, List
from typing_extensions import NotRequired


class FMPCompanyOverview(TypedDict):
    """
    Company overview data returned by get_company_overview().
    
    This is an aggregated view from multiple FMP endpoints:
    - /profile/{symbol} - Basic company info
    - /quote/{symbol} - Latest market data
    - /key-metrics/{symbol} - Financial metrics
    - /ratios/{symbol} - Financial ratios
    
    Example:
        {
            'Symbol': 'AAPL',
            'Name': 'Apple Inc',
            'Sector': 'Technology',
            'Industry': 'Consumer Electronics',
            'MarketCapitalization': 3019983978000,
            'PERatio': 31.4,
            'PriceToBookRatio': 49.7,
            'ReturnOnEquityTTM': 0.2964,  # Note: decimal format (0.2964 = 29.64%)
            ...
        }
    """
    # Basic Company Information
    Symbol: str
    Name: str
    Description: str
    Exchange: str
    Sector: str
    Industry: str
    
    # Market Data
    MarketCapitalization: float  # Market cap in dollars
    SharesOutstanding: float
    Beta: NotRequired[float]
    
    # Valuation Ratios
    PERatio: NotRequired[float]  # Price to Earnings ratio
    EPS: NotRequired[float]  # Earnings per share
    PriceToBookRatio: NotRequired[float]  # P/B ratio
    PriceToSalesRatio: NotRequired[float]  # P/S ratio
    EVToEBITDA: NotRequired[float]  # Enterprise Value to EBITDA
    DebtToEquityRatio: NotRequired[float]  # Debt/Equity ratio
    
    # Profitability Metrics (Note: These are in DECIMAL format, not percentage)
    # E.g., 0.2964 = 29.64%, NOT 29.64 = 2964%
    ReturnOnEquityTTM: NotRequired[float]  # ROE (decimal: 0.30 = 30%)
    ReturnOnAssetsTTM: NotRequired[float]  # ROA (decimal: 0.22 = 22%)
    ProfitMargin: NotRequired[float]  # Profit margin (decimal: 0.246 = 24.6%)
    OperatingMarginTTM: NotRequired[float]  # Operating margin (decimal: 0.30 = 30%)
    RevenueGrowth: NotRequired[float]  # Revenue growth (decimal: 0.08 = 8%)
    
    # NOTE: Price range fields use non-standard keys starting with numbers
    # Access them using dictionary syntax: overview['52WeekHigh']
    # They cannot be defined in TypedDict due to Python naming restrictions
    
    # Other
    LastDividendDate: NotRequired[str]
    DataCompleteness: str  # 'partial', 'good', or 'excellent'
    
    # NOTE: CurrentRatio is NOT available in overview
    # You must calculate it from balance sheet:
    # current_ratio = totalCurrentAssets / totalCurrentLiabilities


class FMPIncomeStatement(TypedDict):
    """
    Income statement row returned in DataFrame from get_income_statement().
    
    DataFrame columns (sample - there are more):
        fiscalDateEnding, symbol, reportedCurrency, cik, fillingDate,
        acceptedDate, calendarYear, period, totalRevenue, costOfRevenue,
        grossProfit, operatingIncome, netIncome, operatingExpenses, etc.
    
    Key Fields to Use:
        totalRevenue: NOT 'revenue' 
        operatingIncome: Operating income
        netIncome: Net income
        costOfRevenue: Cost of revenue
        grossProfit: Gross profit
        operatingExpenses: Operating expenses
    
    Example row:
        {
            'fiscalDateEnding': '2024-09-30',
            'symbol': 'AAPL',
            'calendarYear': '2024',
            'period': 'FY',
            'totalRevenue': 394328000000,  # Use this, NOT 'revenue'
            'operatingIncome': 119800000000,
            'netIncome': 99803000000,
            'costOfRevenue': 223546000000,
            'grossProfit': 170782000000,
            ...
        }
    """
    fiscalDateEnding: str
    symbol: str
    reportedCurrency: str
    cik: str
    fillingDate: str
    acceptedDate: str
    calendarYear: str
    period: str  # 'FY' or 'Q1', 'Q2', 'Q3', 'Q4'
    
    # Revenue and Cost
    totalRevenue: float  # ⚠️ Use this, NOT 'revenue'
    costOfRevenue: float
    grossProfit: float
    grossProfitMargin: NotRequired[float]
    
    # Operating Metrics
    operatingExpenses: float
    operatingIncome: float
    
    # Expenses
    researchAndDevelopmentExpenses: NotRequired[float]
    sellingGeneralAndAdministrativeExpenses: NotRequired[float]
    
    # Income
    netIncome: float
    ebitda: NotRequired[float]
    
    # Per Share
    eps: NotRequired[float]
    epsDiluted: NotRequired[float]


class FMPBalanceSheet(TypedDict):
    """
    Balance sheet row returned in DataFrame from get_balance_sheet().
    
    DataFrame columns (sample - there are more):
        fiscalDateEnding, symbol, reportedCurrency, cik, fillingDate,
        acceptedDate, calendarYear, period, cash, totalCurrentAssets,
        totalAssets, totalCurrentLiabilities, totalLiabilities,
        totalEquity, totalShareholderEquity, totalDebt, etc.
    
    Key Fields to Use:
        totalEquity or totalShareholderEquity: NOT 'totalStockholdersEquity'
        totalCurrentAssets: For current ratio calculation
        totalCurrentLiabilities: For current ratio calculation
        totalDebt: Total debt
        cash: Cash position
    
    Example row:
        {
            'fiscalDateEnding': '2024-09-30',
            'symbol': 'AAPL',
            'calendarYear': '2024',
            'period': 'FY',
            'cash': 23646000000,
            'totalCurrentAssets': 135405000000,
            'totalCurrentLiabilities': 153982000000,
            'totalAssets': 352755000000,
            'totalLiabilities': 302083000000,
            'totalEquity': 50672000000,  # ⚠️ Use this
            'totalShareholderEquity': 50672000000,  # ⚠️ Or this
            'totalDebt': 60588000000,
            ...
        }
        
    Calculate Current Ratio:
        current_ratio = totalCurrentAssets / totalCurrentLiabilities
    """
    fiscalDateEnding: str
    symbol: str
    reportedCurrency: str
    cik: str
    fillingDate: str
    acceptedDate: str
    calendarYear: str
    period: str
    
    # Assets
    cash: float
    shortTermInvestments: NotRequired[float]
    cashAndShortTermInvestments: NotRequired[float]
    totalCurrentAssets: float  # ⚠️ For current ratio
    totalAssets: float
    
    # Liabilities
    totalCurrentLiabilities: float  # ⚠️ For current ratio
    totalLiabilities: float
    totalDebt: float
    longTermDebt: NotRequired[float]
    shortTermDebt: NotRequired[float]
    
    # Equity (⚠️ Use one of these, NOT 'totalStockholdersEquity')
    totalEquity: float
    totalShareholderEquity: NotRequired[float]
    
    # Other
    retainedEarnings: NotRequired[float]
    propertyPlantEquipmentNet: NotRequired[float]
    goodwill: NotRequired[float]
    intangibleAssets: NotRequired[float]


class FMPCashFlow(TypedDict):
    """
    Cash flow row returned in DataFrame from get_cash_flow().
    
    DataFrame columns (sample):
        fiscalDateEnding, symbol, reportedCurrency, cik, fillingDate,
        acceptedDate, calendarYear, period, operatingCashflow,
        capitalExpenditures, freeCashflow, dividendPayout,
        repurchaseOfStock, etc.
    
    Key Fields:
        freeCashflow or freeCashFlow: Free cash flow (watch capitalization)
        operatingCashflow: Operating cash flow
        capitalExpenditures: CapEx
    
    Example row:
        {
            'fiscalDateEnding': '2024-09-30',
            'symbol': 'AAPL',
            'calendarYear': '2024',
            'period': 'FY',
            'operatingCashflow': 122151000000,
            'capitalExpenditures': -11085000000,
            'freeCashflow': 111066000000,  # ⚠️ Check capitalization
            'dividendPayout': 14841000000,
            'repurchaseOfStock': 89402000000,
            ...
        }
    """
    fiscalDateEnding: str
    symbol: str
    reportedCurrency: str
    cik: str
    fillingDate: str
    acceptedDate: str
    calendarYear: str
    period: str
    
    # Operating Activities
    netIncome: float
    operatingCashflow: float
    
    # Investing Activities
    capitalExpenditures: float  # Usually negative
    
    # Free Cash Flow (⚠️ Check both spellings)
    freeCashflow: NotRequired[float]
    freeCashFlow: NotRequired[float]
    
    # Financing Activities
    dividendPayout: NotRequired[float]
    repurchaseOfStock: NotRequired[float]
    issuanceOfStock: NotRequired[float]
    
    # Other
    changeInCash: NotRequired[float]


class FMPHistoricalPrice(TypedDict):
    """
    Single row in historical price DataFrame from get_historical_prices().
    
    DataFrame columns (FMP uses CAPITALIZED names):
        Date, Open, High, Low, Close, Volume
    
    ⚠️ IMPORTANT: Column names are CAPITALIZED
        - Use 'Close' NOT 'close'
        - Use 'High' NOT 'high'
        - Use 'Low' NOT 'low'
        - Use 'Open' NOT 'open'
        - Use 'Volume' NOT 'volume'
    
    Example row:
        {
            'Date': '2024-12-20',
            'Open': 223.12,
            'High': 225.30,
            'Low': 222.45,
            'Close': 224.50,
            'Volume': 45123456
        }
    """
    Date: str  # or pd.Timestamp if index
    Open: float
    High: float  # ⚠️ Capitalized
    Low: float  # ⚠️ Capitalized
    Close: float  # ⚠️ Capitalized
    Volume: int


class FMPPriceTarget(TypedDict):
    """
    Price target consensus returned by get_price_target_consensus().
    
    May return empty dict {} if no analyst data available.
    
    Example (if available):
        {
            'targetConsensus': 185.50,
            'targetHigh': 220.00,
            'targetLow': 150.00,
            'targetMedian': 185.00,
            'numberOfAnalysts': 42
        }
    """
    targetConsensus: NotRequired[float]
    targetHigh: NotRequired[float]
    targetLow: NotRequired[float]
    targetMedian: NotRequired[float]
    numberOfAnalysts: NotRequired[int]


class FMPAnalystGrades(TypedDict):
    """
    Analyst grades/recommendations returned by get_analyst_grades_consensus().
    
    May return empty dict {} if no analyst data available.
    
    Example (if available):
        {
            'strongBuy': 15,
            'buy': 20,
            'hold': 5,
            'sell': 1,
            'strongSell': 0
        }
    """
    strongBuy: NotRequired[int]
    buy: NotRequired[int]
    hold: NotRequired[int]
    sell: NotRequired[int]
    strongSell: NotRequired[int]


# Quick Reference Guide
"""
COMMON FIELD NAME MISTAKES TO AVOID:

❌ WRONG                          ✅ CORRECT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Income Statement:
  data.get('revenue')       →     data.get('totalRevenue')

Balance Sheet:
  data.get('totalStockholdersEquity')  →  data.get('totalEquity')
                                          or data.get('totalShareholderEquity')

Price History DataFrame:
  df['close']               →     df['Close']
  df['high']                →     df['High']
  df['low']                 →     df['Low']
  df['open']                →     df['Open']

Cash Flow:
  May be either 'freeCashflow' or 'freeCashFlow' - check both!

Current Ratio:
  data.get('CurrentRatio')  →     Calculate it yourself:
                                  totalCurrentAssets / totalCurrentLiabilities

Percentages in Overview:
  ReturnOnEquityTTM: 0.2964  =   29.64% (it's a decimal, not percentage)
  RevenueGrowth: 0.08        =   8% (it's a decimal, not percentage)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
