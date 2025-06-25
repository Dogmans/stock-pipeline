# Financial Modeling Prep API Provider Guide

This guide covers best practices and implementation details for working with the Financial Modeling Prep API.

## API Provider Overview

Financial Modeling Prep (FMP) is our primary data provider for financial statements and market data. The provider implementation follows these key principles:

- Comprehensive caching to minimize API calls
- Consistent error handling and reporting
- Standardized data formats matching our internal conventions
- Rate limiting to stay within API constraints

## API Request Pattern

All API requests should use the centralized helper method:

```python
def _make_api_request(self, endpoint, symbol, params=None, rate_limit=True):
    """
    Make an API request to Financial Modeling Prep.
    
    Args:
        endpoint (str): API endpoint path (without base URL)
        symbol (str): Stock symbol to query
        params (dict, optional): Additional query parameters
        rate_limit (bool): Whether to apply rate limiting
        
    Returns:
        tuple: (success (bool), data (dict/list), error_msg (str or None))
    """
    url = f"{self.base_url}/{endpoint}/{symbol}"
    
    # Initialize params dictionary if None
    if params is None:
        params = {}
    
    # Always include API key
    params["apikey"] = self.api_key
    
    try:
        # Apply rate limiting if requested
        if rate_limit:
            fmp_rate_limiter.wait_if_needed()
            
        # Make the request
        response = requests.get(url, params=params)
        
        # Check if response is successful
        if response.status_code == 200:
            data = response.json()
            
            # Check if data is valid (list with content for most endpoints)
            if isinstance(data, list) and len(data) > 0:
                return True, data, None
            elif not isinstance(data, list) and isinstance(data, dict):
                # Some endpoints return direct dictionaries
                return True, data, None
            else:
                error_msg = f"Empty or invalid response: {data}"
                logger.error(f"API error for {url}: {error_msg}")
                return False, None, error_msg
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            logger.error(f"API error for {url}: {error_msg}")
            return False, None, error_msg
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Exception during API call to {url}: {error_msg}")
        return False, None, error_msg
```

## Financial Statement Processing Pattern

All financial statement processing should use the common helper:

```python
def _process_financial_statement(self, data, column_mapping=None):
    """
    Process financial statement data into standardized DataFrame.
    
    Args:
        data (list): Raw financial statement data from API
        column_mapping (dict, optional): Column name mapping
        
    Returns:
        pd.DataFrame: Processed financial statement data
    """
    if not data:
        return pd.DataFrame()
        
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Rename date column to match our standard format
    df = df.rename(columns={"date": "fiscalDateEnding"})
    
    # Convert date to datetime
    df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
    
    # Sort by date
    df = df.sort_values("fiscalDateEnding", ascending=False)
    
    # Rename columns if mapping provided
    if column_mapping:
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    return df
```

## Field Mapping Reference

### Income Statement

```python
column_mapping = {
    "revenue": "totalRevenue",
    "costOfRevenue": "costOfRevenue",
    "grossProfit": "grossProfit",
    "grossProfitRatio": "grossProfitMargin",
    "operatingExpenses": "operatingExpenses",
    "operatingIncome": "operatingIncome",
    "netIncome": "netIncome",
    "ebitda": "ebitda"
}
```

### Balance Sheet

```python
column_mapping = {
    "totalAssets": "totalAssets",
    "totalCurrentAssets": "totalCurrentAssets",
    "totalLiabilities": "totalLiabilities",
    "totalCurrentLiabilities": "totalCurrentLiabilities",
    "totalStockholdersEquity": "totalShareholderEquity",
    "cashAndCashEquivalents": "cash",
    "shortTermInvestments": "shortTermInvestments",
    "longTermDebt": "longTermDebt",
    "commonStock": "commonStock"
}
```

### Cash Flow Statement

```python
column_mapping = {
    "netCashProvidedByOperatingActivities": "operatingCashflow",
    "capitalExpenditure": "capitalExpenditures",
    "freeCashFlow": "freeCashflow",
    "dividendsPaid": "dividendPayout",
    "netChangeInCash": "changeInCash",
    "stockRepurchased": "repurchaseOfStock",
    "commonStockIssued": "issuanceOfStock"
}
```

## Cache Management

Each method includes a force_refresh parameter to handle cache invalidation:

```python
@cache.memoize(expire=168*3600)  # Cache for 1 week (168 hours)
def get_income_statement(self, symbol: str, 
                        annual: bool = True,
                        force_refresh: bool = False) -> pd.DataFrame:
    """Get income statement data"""
    if force_refresh:
        cache.delete(self.get_income_statement, symbol, annual)
        
    # Make API request using helper...
```

## Response Examples

The provider returns standardized responses:

### Income Statement

```python
# DataFrame with columns:
# fiscalDateEnding, symbol, reportedCurrency, totalRevenue, costOfRevenue, grossProfit, 
# operatingExpenses, operatingIncome, netIncome, ebitda, etc.
```

### Balance Sheet

```python
# DataFrame with columns:
# fiscalDateEnding, symbol, reportedCurrency, totalAssets, totalCurrentAssets,
# totalLiabilities, totalCurrentLiabilities, totalShareholderEquity, cash, etc.
```

### Cash Flow Statement

```python
# DataFrame with columns:
# fiscalDateEnding, symbol, reportedCurrency, operatingCashflow, capitalExpenditures,
# freeCashflow, dividendPayout, changeInCash, repurchaseOfStock, issuanceOfStock, etc.
```

### Historical Prices

```python
# DataFrame with columns:
# Date (index), Open, High, Low, Close, Volume
```

### Company Overview

```python
# Dictionary with keys:
# Symbol, Name, Description, Exchange, Sector, Industry, MarketCapitalization,
# PERatio, EPS, Beta, 52WeekHigh, 52WeekLow, etc.
```

## Best Practices

1. **Always handle missing data**: Check for empty DataFrames or missing fields
2. **Respect rate limits**: Use the _make_api_request helper which handles rate limiting
3. **Use caching**: Don't bypass caching unless absolutely necessary
4. **Handle errors**: Check for success before processing data
5. **Field naming**: Maintain consistent column names with our internal conventions
