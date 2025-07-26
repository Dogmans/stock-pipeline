from data_providers import get_provider

provider = get_provider('financial_modeling_prep')
print('Testing FCF data retrieval...')

symbol = 'AAPL'
print(f'Testing {symbol}...')

cash_flow = provider.get_cash_flow(symbol)
company_data = provider.get_company_overview(symbol)

print(f'Cash flow type: {type(cash_flow)}')
print(f'Company data type: {type(company_data)}')

if hasattr(cash_flow, 'empty') and not cash_flow.empty:
    print(f'Cash flow columns: {list(cash_flow.columns)}')
    latest = cash_flow.iloc[0]
    print(f'Free cash flow: {latest.get("freeCashFlow", "Missing")}')

if company_data:
    print(f'Market cap: {company_data.get("MarketCapitalization", "Missing")}')
