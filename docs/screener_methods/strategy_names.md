# Pipeline Strategy Names

The stock screening pipeline supports multiple screening strategies. Each strategy corresponds to a specific screener function in the `screeners` package.

## Available Strategies

To see the list of available strategies:

```python
from screeners import get_available_screeners
print(get_available_screeners())
```

Current available strategies:

- `pe_ratio`: Low price-to-earnings ratio screener
- `price_to_book`: Low price-to-book ratio screener
- `52_week_lows`: Stocks near their 52-week lows
- `fallen_ipos`: Recently IPO'd stocks that have dropped significantly
- `turnaround_candidates`: Companies showing signs of financial turnaround
- `peg_ratio`: Low PEG ratio screener
- `sector_corrections`: Stocks in sectors experiencing market corrections
- `combined`: Runs multiple screeners and combines results

## Using Strategies in the Pipeline

To run the pipeline with specific strategies:

```powershell
# Run with a single strategy
python main.py --universe sp500 --strategies pe_ratio

# Run with multiple strategies
python main.py --universe sp500 --strategies pe_ratio,price_to_book,peg_ratio

# Run all strategies
python main.py --universe sp500 --strategies all
```

## Strategy Aliases

Note that some strategy aliases may exist for backward compatibility. For example:

- `value` was previously used for `pe_ratio`
- `book_value` was previously used for `price_to_book`
- `52_week_low` (singular) may be used for `52_week_lows` (plural)

If you encounter issues with strategy names, check the current list of available strategies using `get_available_screeners()`.

## Adding New Strategies

To add a new strategy:

1. Create a new module in the `screeners` package (e.g., `screeners/my_strategy.py`)
2. Implement the `screen_for_my_strategy()` function
3. Update `__init__.py` to import and expose the new function
4. Add the module to the list in `utils.py`

The strategy will then be automatically available through `get_available_screeners()` and can be used with the `--strategies` command line argument.
