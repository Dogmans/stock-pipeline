"""
P/E Ratio Screener module.
Screens for stocks with low Price to Earnings ratios.
"""

from .common import *

def screen_for_pe_ratio(universe_df, max_pe=None):
    """
    Screen for stocks with low P/E ratios.
    Based on Strategy #2: "Never Lose Sight of P/E Multiples!"
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        max_pe (float): Maximum P/E ratio to include
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    if max_pe is None:
        max_pe = config.ScreeningThresholds.MAX_PE_RATIO
    
    logger.info(f"Screening for stocks with P/E ratio <= {max_pe}...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Use universe_df directly
    symbols = universe_df['symbol'].tolist()
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Process each symbol individually
    for symbol in tqdm(symbols, desc="Screening for low P/E ratio", unit="symbol"):
        try:
            # Get company overview data
            company_data = fmp_provider.get_company_overview(symbol)
            
            # Skip if we couldn't get company data
            if not company_data:
                continue
            
            # Check if P/E ratio is available and below threshold
            pe_ratio = company_data.get('PERatio')
            if pe_ratio is None or pe_ratio == '':
                continue
            
            # Convert to float if it's a string
            if isinstance(pe_ratio, str):
                pe_ratio = float(pe_ratio)
            
            # Handle negative PE ratios - typically excluded
            if pe_ratio <= 0:
                continue
                
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
            
            # All stocks are included for ranking, but mark whether they meet the threshold
            meets_threshold = pe_ratio <= max_pe
                
            # Calculate forward PE if available
            eps = company_data.get('EPS')
            forward_pe = None
            if eps and eps != '' and float(eps) > 0:
                forward_pe = current_price / float(eps)
            
            # Add to results (all stocks with valid P/E ratios)
            reason = f"Low P/E ratio (P/E = {pe_ratio:.2f})" if meets_threshold else f"P/E ratio: {pe_ratio:.2f}"
            
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'current_price': current_price,
                'pe_ratio': pe_ratio,
                'forward_pe': forward_pe,
                'market_cap': market_cap,
                'meets_threshold': meets_threshold,
                'reason': reason
            })
            
            if meets_threshold:
                logger.info(f"Found {symbol} with low P/E ratio: {pe_ratio:.2f}")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for P/E screening: {e}")
            # If provider fails to return data, stop execution
            raise Exception(f"Data provider failed for symbol {symbol}: {e}")
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by P/E ratio (lowest first)
        df = df.sort_values('pe_ratio')
        return df
    else:
        return pd.DataFrame()
