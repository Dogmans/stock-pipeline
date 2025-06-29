import pandas as pd
from screeners import run_all_screeners, get_available_screeners
from universe import get_stock_universe

universe_df = get_stock_universe('sp500')
strategies = ['pe_ratio', 'price_to_book', 'peg_ratio']
results = run_all_screeners(universe_df, strategies=strategies)

# Count symbols in each screener
symbols_by_screener = {}
for strategy, df in results.items():
    symbols_by_screener[strategy] = set(df['symbol'].tolist())
    print(f"{strategy}: {len(symbols_by_screener[strategy])} stocks")

# Find symbols in all screeners
all_screeners = set.intersection(*symbols_by_screener.values())
print(f"\nStocks in all three screeners: {len(all_screeners)}")
if all_screeners:
    print(f"Symbols: {', '.join(sorted(all_screeners))}")
else:
    print("No stocks appear in all three screeners")

# Find stocks in pe_ratio and price_to_book
pe_and_pb = symbols_by_screener['pe_ratio'].intersection(symbols_by_screener['price_to_book'])
print(f"\nStocks in both pe_ratio and price_to_book: {len(pe_and_pb)}")
if len(pe_and_pb) <= 20:
    print(f"Symbols: {', '.join(sorted(pe_and_pb))}")
