"""
Sharpe Ratio Screener module.
Screens for stocks with high risk-adjusted returns (Sharpe ratio).
"""

from .common import *

def screen_for_sharpe_ratio(universe_df, min_sharpe_ratio=None, lookback_period="1y"):
    """
    Screen for stocks with high Sharpe ratios (risk-adjusted returns).
    
    The Sharpe ratio is calculated as:
    (annualized return - risk-free rate) / annualized volatility
    
    Args:
        universe_df (DataFrame): Stock universe being analyzed (required)
        min_sharpe_ratio (float): Minimum Sharpe ratio to include (default: 1.0)
        lookback_period (str): Period for calculating returns and volatility (default: "1y")
        
    Returns:
        DataFrame: Stocks meeting the criteria
    """
    if min_sharpe_ratio is None:
        min_sharpe_ratio = config.ScreeningThresholds.MIN_SHARPE_RATIO if hasattr(config.ScreeningThresholds, 'MIN_SHARPE_RATIO') else 1.0
    
    logger.info(f"Screening for stocks with Sharpe ratio >= {min_sharpe_ratio} over {lookback_period} period...")
    
    # Import the FMP provider
    from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
    
    # Use universe_df directly
    symbols = universe_df['symbol'].tolist()
    
    # Initialize the FMP provider
    fmp_provider = FinancialModelingPrepProvider()
    
    # Store results
    results = []
    
    # Risk-free rate assumption (10-year Treasury yield approximation)
    risk_free_rate = 0.04  # 4% annual
    
    # Process each symbol individually
    for symbol in tqdm(symbols, desc="Calculating Sharpe ratios", unit="symbol"):
        try:
            # Get historical price data
            price_data = fmp_provider.get_historical_prices(symbol, period=lookback_period)
            
            if symbol not in price_data or price_data[symbol] is None or price_data[symbol].empty:
                continue
                
            df = price_data[symbol]
            
            # Need at least 30 days of data for meaningful Sharpe ratio
            if len(df) < 30:
                continue
                
            # Calculate daily returns
            df['returns'] = df['Close'].pct_change()
            
            # Remove any NaN values
            returns = df['returns'].dropna()
            
            if len(returns) < 30:
                continue
            
            # Calculate annualized return and volatility
            # Assuming 252 trading days per year
            annual_return = returns.mean() * 252
            annual_volatility = returns.std() * np.sqrt(252)
            
            # Avoid division by zero
            if annual_volatility == 0:
                continue
                
            # Calculate Sharpe ratio
            sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility
            
            # Get company overview data for additional info
            company_data = fmp_provider.get_company_overview(symbol)
            
            # Extract company info
            company_name = company_data.get('Name', symbol) if company_data else symbol
            sector = company_data.get('Sector', 'Unknown') if company_data else 'Unknown'
            market_cap = company_data.get('MarketCapitalization', 0) if company_data else 0
            current_price = df['Close'].iloc[-1]
            
            # All stocks are included for ranking, but mark whether they meet the threshold
            meets_threshold = sharpe_ratio >= min_sharpe_ratio
            reason = f"High Sharpe ratio ({sharpe_ratio:.2f})" if meets_threshold else f"Sharpe ratio: {sharpe_ratio:.2f}"
            
            # Calculate additional metrics for context
            total_return = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
            max_drawdown = calculate_max_drawdown(df['Close'])
            
            # Add to results (all stocks with sufficient data)
            results.append({
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'current_price': current_price,
                'sharpe_ratio': sharpe_ratio,
                'annual_return': annual_return,
                'annual_volatility': annual_volatility,
                'total_return_pct': total_return,
                'max_drawdown_pct': max_drawdown,
                'market_cap': market_cap,
                'meets_threshold': meets_threshold,
                'reason': reason
            })
            
            if meets_threshold:
                logger.info(f"Found {symbol} with high Sharpe ratio: {sharpe_ratio:.2f}")
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for Sharpe ratio screening: {e}")
            continue
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        # Sort by Sharpe ratio (highest first)
        df = df.sort_values('sharpe_ratio', ascending=False)
        return df
    else:
        return pd.DataFrame()


def calculate_max_drawdown(price_series):
    """
    Calculate the maximum drawdown of a price series.
    
    Args:
        price_series (pd.Series): Time series of prices
        
    Returns:
        float: Maximum drawdown as a percentage
    """
    # Calculate running maximum
    rolling_max = price_series.expanding().max()
    
    # Calculate drawdown
    drawdown = (price_series - rolling_max) / rolling_max
    
    # Return maximum drawdown as positive percentage
    return abs(drawdown.min()) * 100
