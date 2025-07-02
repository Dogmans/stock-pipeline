"""
Price to Book Ratio Screener module.
Screens for stocks trading below or near book value.
"""

from .common import *

def screen_for_price_to_book(universe_df, max_pb_ratio=None):
    """
    Screen for stocks trading below or near book value.
    Based on Strategy #1: "Understanding Relationship Between Book Value and Share Price"
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        max_pb_ratio (float): Maximum price-to-book ratio to include
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    if max_pb_ratio is None:
        max_pb_ratio = config.ScreeningThresholds.MAX_PRICE_TO_BOOK_RATIO
    
    logger.info(f"Screening for stocks with P/B ratio <= {max_pb_ratio}...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Use universe_df directly
    symbols = universe_df['symbol'].tolist()
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Process each symbol individually
    for symbol in tqdm(symbols, desc="Screening for low price-to-book ratio", unit="symbol"):
        try:
            # Get company overview data
            company_data = fmp_provider.get_company_overview(symbol)
            
            # Skip if we couldn't get company data
            if not company_data:
                continue
            
            # Check if P/B ratio is available and below threshold
            pb_ratio = company_data.get('PriceToBookRatio')
            if pb_ratio is None or pb_ratio < 0 or np.isnan(float(pb_ratio)):
                continue
            
            # Convert to float if it's a string
            if isinstance(pb_ratio, str):
                pb_ratio = float(pb_ratio)
            
            # Get price data to get current price
            price_data = fmp_provider.get_historical_prices(symbol, period="5d")
            if symbol not in price_data or price_data[symbol] is None or price_data[symbol].empty:
                current_price = company_data.get('price', 0)
            else:
                current_price = price_data[symbol]['Close'].iloc[-1]
            
            # Extract other relevant info
            market_cap = company_data.get('MarketCapitalization', 0)
            company_name = company_data.get('Name', symbol)
            sector = company_data.get('Sector', 'Unknown')
            
            # Calculate book value per share based on available data
            book_value_per_share = current_price / pb_ratio if pb_ratio > 0 else None
            
            # All stocks are included for ranking, but mark whether they meet the threshold
            meets_threshold = pb_ratio <= max_pb_ratio
            reason = f"Low price to book ratio (P/B = {pb_ratio:.2f})" if meets_threshold else f"Price to book ratio: P/B = {pb_ratio:.2f}"
            
            # Add to results (all stocks with valid P/B ratios)
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'current_price': current_price,
                'book_value_per_share': book_value_per_share,
                'price_to_book': pb_ratio,
                'market_cap': market_cap,
                'meets_threshold': meets_threshold,
                'reason': reason
            })
            
            if meets_threshold:
                logger.info(f"Found {symbol} trading near book value: P/B={pb_ratio:.2f}")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for P/B screening: {e}")
            # If provider fails to return data, stop execution
            raise Exception(f"Data provider failed for symbol {symbol}: {e}")
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by P/B ratio (lowest first)
        df = df.sort_values('price_to_book')
        return df
    else:
        return pd.DataFrame()
