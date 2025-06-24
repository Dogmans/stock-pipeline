"""
Technical indicators module for stock screening pipeline.
Contains functions for calculating technical indicators, price statistics, and market analysis.

Functions:
    calculate_technical_indicators(): Calculate technical indicators from price data
    calculate_price_statistics(): Calculate price statistics from historical data
    calculate_fundamental_ratios(): Calculate fundamental ratios for a single stock
    analyze_debt_and_cash(): Analyze debt and cash metrics for a single stock
    normalize_sector_metrics(): Calculate sector-relative metrics
"""

import pandas as pd
import numpy as np
from utils.logger import get_logger
from sklearn.preprocessing import StandardScaler

# Try to import TA-Lib, but provide fallback if not available
try:
    import talib
    HAS_TALIB = True
except ImportError:
    # Using the module logger instead of direct logging
    logger = get_logger(__name__)
    logger.warning("TA-Lib not available. Some technical indicators will be calculated using pandas instead.")
    HAS_TALIB = False

# Get logger for this module
logger = get_logger(__name__)

def calculate_technical_indicators(df):
    """
    Calculate technical indicators from price data
    
    Args:
        df (DataFrame): DataFrame with OHLCV price data
        
    Returns:
        DataFrame: Original DataFrame with additional technical indicator columns
    """
    if df.empty:
        return df
        
    # Make sure column names are standardized
    df.columns = [col.lower() for col in df.columns]
    
    # Basic moving averages
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()
    
    # Exponential moving averages
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # Calculate MACD using pandas (will be overwritten by TA-Lib if available)
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Use TA-Lib for advanced indicators if available
    if HAS_TALIB:
        try:
            # RSI using TA-Lib (more accurate)
            df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)
            
            # Bollinger Bands
            df['upper_band'], df['middle_band'], df['lower_band'] = talib.BBANDS(
                df['close'].values, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
            )
            
            # MACD using TA-Lib
            macd, signal, hist = talib.MACD(
                df['close'].values, fastperiod=12, slowperiod=26, signalperiod=9
            )
            df['macd'] = macd
            df['macd_signal'] = signal
            df['macd_hist'] = hist
            
            # Stochastic
            df['slowk'], df['slowd'] = talib.STOCH(
                df['high'].values, df['low'].values, df['close'].values,
                fastk_period=14, slowk_period=3, slowd_period=3
            )
            
            # Average Directional Index
            df['adx'] = talib.ADX(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
            
            # ATR - Average True Range (volatility indicator)
            df['atr'] = talib.ATR(df['high'].values, df['low'].values, 
                                  df['close'].values, timeperiod=14)
            
            # OBV - On Balance Volume
            close_values = df['close'].values.astype(float)
            volume_values = df['volume'].values.astype(float)
            df['obv'] = talib.OBV(close_values, volume_values)
            
            # CCI - Commodity Channel Index
            df['cci'] = talib.CCI(df['high'].values, df['low'].values,
                                  df['close'].values, timeperiod=20)
        except Exception as e:
            logger.error(f"Error calculating TA-Lib indicators: {e}")
    else:
        # Simplified Bollinger Bands calculation without TA-Lib
        df['middle_band'] = df['sma_20']
        rolling_std = df['close'].rolling(window=20).std()
        df['upper_band'] = df['middle_band'] + (rolling_std * 2)
        df['lower_band'] = df['middle_band'] - (rolling_std * 2)
        
        # Only calculate RSI with pandas if TA-Lib is not available
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
    
    # Volume indicators
    df['volume_ma'] = df['volume'].rolling(window=20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']
    
    return df

def calculate_rsi(prices, period=14):
    """
    Calculate Relative Strength Index for price series
    
    Args:
        prices: Series or array of prices
        period: RSI period (default 14)
        
    Returns:
        Series or array of RSI values
    """
    if HAS_TALIB:
        return talib.RSI(prices, timeperiod=period)
    else:
        prices_series = pd.Series(prices)
        delta = prices_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

def calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9):
    """
    Calculate MACD (Moving Average Convergence/Divergence) for price series
    
    Args:
        prices: Series or array of prices
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line period (default 9)
        
    Returns:
        Tuple of (macd, signal, histogram)
    """
    if HAS_TALIB:
        return talib.MACD(prices, fastperiod=fast_period, 
                         slowperiod=slow_period, signalperiod=signal_period)
    else:
        prices_series = pd.Series(prices)
        fast_ema = prices_series.ewm(span=fast_period, adjust=False).mean()
        slow_ema = prices_series.ewm(span=slow_period, adjust=False).mean()
        macd = fast_ema - slow_ema
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist

def calculate_bollinger_bands(prices, period=20, num_std=2):
    """
    Calculate Bollinger Bands for price series
    
    Args:
        prices: Series or array of prices
        period: SMA period (default 20)
        num_std: Number of standard deviations (default 2)
        
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    if HAS_TALIB:
        return talib.BBANDS(prices, timeperiod=period, nbdevup=num_std, nbdevdn=num_std, matype=0)
    else:
        prices_series = pd.Series(prices)
        middle_band = prices_series.rolling(window=period).mean()
        std_dev = prices_series.rolling(window=period).std()
        upper_band = middle_band + (std_dev * num_std)
        lower_band = middle_band - (std_dev * num_std)
        return upper_band, middle_band, lower_band

def calculate_price_statistics(df):
    """
    Calculate price statistics from historical data
    
    Args:
        df (DataFrame): DataFrame with historical price data
        
    Returns:
        DataFrame: Original DataFrame with additional statistic columns
    """
    if df.empty:
        return df
    
    # Daily returns
    df['daily_return'] = df['close'].pct_change()
    
    # Cumulative returns
    df['cumulative_return'] = (1 + df['daily_return']).cumprod() - 1
    
    # Volatility (rolling window)
    df['volatility'] = df['close'].rolling(window=21).std() * np.sqrt(252)
    
    # Sharpe ratio (assuming risk-free rate of 0)
    df['sharpe_ratio'] = df['daily_return'].rolling(window=252).mean() / df['daily_return'].rolling(window=252).std()
    
    return df

def calculate_fundamental_ratios(df):
    """
    Calculate fundamental ratios for a single stock
    
    Args:
        df (DataFrame): DataFrame with historical price and volume data
        
    Returns:
        Series: A series with calculated fundamental ratios
    """
    if df.empty:
        return pd.Series()
    
    # Price/Earnings ratio
    pe_ratio = df['close'][-1] / df['eps'][-1] if df['eps'][-1] != 0 else np.nan
    
    # Price/Book ratio
    pb_ratio = df['close'][-1] / df['book_value'][-1] if df['book_value'][-1] != 0 else np.nan
    
    # Dividend Yield
    dividend_yield = df['dividend'][-1] / df['close'][-1] if df['close'][-1] != 0 else np.nan
    
    # Return on Equity
    roe = df['net_income'][-1] / df['shareholder_equity'][-1] if df['shareholder_equity'][-1] != 0 else np.nan
    
    # Debt/Equity ratio
    debt_equity_ratio = df['total_debt'][-1] / df['shareholder_equity'][-1] if df['shareholder_equity'][-1] != 0 else np.nan
    
    ratios = pd.Series({
        'pe_ratio': pe_ratio,
        'pb_ratio': pb_ratio,
        'dividend_yield': dividend_yield,
        'roe': roe,
        'debt_equity_ratio': debt_equity_ratio
    })
    
    return ratios

def calculate_fundamental_ratios(ticker_data, fundamental_data):
    """
    Calculate fundamental ratios for a stock
    
    Args:
        ticker_data (dict): Yahoo Finance ticker info
        fundamental_data (dict): Alpha Vantage fundamental data
        
    Returns:
        dict: Dictionary with calculated fundamental ratios
    """
    ratios = {}
    
    # Basic valuation metrics (from Yahoo Finance)
    ratios['market_cap'] = ticker_data.get('marketCap', None)
    ratios['pe_ratio'] = ticker_data.get('trailingPE', None)
    ratios['forward_pe'] = ticker_data.get('forwardPE', None)
    ratios['price_to_book'] = ticker_data.get('priceToBook', None)
    ratios['price_to_sales'] = ticker_data.get('priceToSalesTrailing12Months', None)
    ratios['dividend_yield'] = ticker_data.get('dividendYield', 0) * 100 if ticker_data.get('dividendYield') else 0
    
    # If we have Alpha Vantage data, calculate more detailed ratios
    if 'overview' in fundamental_data:
        overview = fundamental_data['overview']
        
        # Return on equity
        try:
            ratios['return_on_equity'] = float(overview.get('ReturnOnEquityTTM', 0)) * 100
        except:
            ratios['return_on_equity'] = None
            
        # Return on assets
        try:
            ratios['return_on_assets'] = float(overview.get('ReturnOnAssetsTTM', 0)) * 100
        except:
            ratios['return_on_assets'] = None
            
        # Profit margin
        try:
            ratios['profit_margin'] = float(overview.get('ProfitMargin', 0)) * 100
        except:
            ratios['profit_margin'] = None
            
        # Operating margin
        try:
            ratios['operating_margin'] = float(overview.get('OperatingMarginTTM', 0)) * 100
        except:
            ratios['operating_margin'] = None
            
        # EV/EBITDA
        try:
            ratios['ev_to_ebitda'] = float(overview.get('EVToEBITDA', 0))
        except:
            ratios['ev_to_ebitda'] = None
    
    # Debt and liquidity ratios
    ratios['debt_to_equity'] = ticker_data.get('debtToEquity', None)
    if ratios['debt_to_equity']:
        ratios['debt_to_equity'] /= 100  # Convert from percentage to ratio
        
    ratios['current_ratio'] = ticker_data.get('currentRatio', None)
    ratios['quick_ratio'] = ticker_data.get('quickRatio', None)
    
    return ratios

def analyze_debt_and_cash(df):
    """
    Analyze debt and cash metrics for a single stock
    
    Args:
        df (DataFrame): DataFrame with historical balance sheet data
        
    Returns:
        Series: A series with calculated debt and cash metrics
    """
    if df.empty:
        return pd.Series()
    
    # Current Ratio
    current_ratio = df['current_assets'][-1] / df['current_liabilities'][-1] if df['current_liabilities'][-1] != 0 else np.nan
    
    # Quick Ratio
    quick_ratio = (df['current_assets'][-1] - df['inventory'][-1]) / df['current_liabilities'][-1] if df['current_liabilities'][-1] != 0 else np.nan
    
    # Cash Ratio
    cash_ratio = df['cash_and_cash_equivalents'][-1] / df['current_liabilities'][-1] if df['current_liabilities'][-1] != 0 else np.nan
    
    # Debt Ratio
    debt_ratio = df['total_debt'][-1] / df['total_assets'][-1] if df['total_assets'][-1] != 0 else np.nan
    
    # Equity Ratio
    equity_ratio = df['shareholder_equity'][-1] / df['total_assets'][-1] if df['total_assets'][-1] != 0 else np.nan
    
    metrics = pd.Series({
        'current_ratio': current_ratio,
        'quick_ratio': quick_ratio,
        'cash_ratio': cash_ratio,
        'debt_ratio': debt_ratio,
        'equity_ratio': equity_ratio
    })
    
    return metrics

def normalize_sector_metrics(stocks_df, sector_col='sector'):
    """
    Normalize metrics within sectors to find outperformers/underperformers
    
    Args:
        stocks_df (DataFrame): DataFrame with stock data including sector information
        sector_col (str): Name of the column containing sector information
        
    Returns:
        DataFrame: Original DataFrame with additional normalized columns
    """
    if stocks_df.empty or sector_col not in stocks_df.columns:
        return stocks_df
        
    # Metrics to normalize
    metrics_to_normalize = [
        'pe_ratio', 'forward_pe', 'price_to_book', 'price_to_sales',
        'debt_to_equity', 'return_on_equity', 'profit_margin'
    ]
    
    # Only normalize columns that exist in the dataframe
    metrics = [col for col in metrics_to_normalize if col in stocks_df.columns]
    
    # Create a copy to avoid modifying the original
    df = stocks_df.copy()
    
    # Group by sector and normalize within each sector
    for sector in df[sector_col].unique():
        sector_mask = df[sector_col] == sector
        
        if sum(sector_mask) <= 1:
            # Skip sectors with only one stock
            continue
            
        for metric in metrics:
            # Skip metrics with too many NaN values
            if df.loc[sector_mask, metric].isna().sum() > 0.5 * sum(sector_mask):
                continue
                
            # Create a scaler for each metric
            scaler = StandardScaler()
            
            # Replace NaNs with median for scaling purposes
            temp_values = df.loc[sector_mask, metric].fillna(df.loc[sector_mask, metric].median())
            
            # Scale and create new column for normalized values
            normalized_values = scaler.fit_transform(temp_values.values.reshape(-1, 1))
            df.loc[sector_mask, f'{metric}_normalized'] = normalized_values
            
            # Also calculate sector-relative metrics (ratio to sector average)
            sector_avg = temp_values.mean()
            if sector_avg != 0:  # Avoid division by zero
                df.loc[sector_mask, f'{metric}_sector_relative'] = df.loc[sector_mask, metric] / sector_avg
    
    return df

def calculate_cash_runway(cash, burn_rate):
    """
    Calculate how many months of cash runway a company has left
    
    Args:
        cash (float): Current cash and equivalents
        burn_rate (float): Monthly cash burn rate
        
    Returns:
        float: Number of months of runway left
    """
    if burn_rate <= 0:
        return float('inf')  # Infinite runway (company is profitable or no burn)
        
    runway = cash / burn_rate
    return runway

def analyze_debt_and_cash(ticker_data, fundamental_data=None):
    """
    Analyze a company's debt and cash position
    
    Args:
        ticker_data (dict): Yahoo Finance ticker info
        fundamental_data (dict): Alpha Vantage fundamental data
        
    Returns:
        dict: Dictionary with debt and cash analysis
    """
    results = {}
    
    # Extract basic metrics from ticker data
    results['total_debt'] = ticker_data.get('totalDebt', 0)
    results['total_cash'] = ticker_data.get('totalCash', 0)
    results['free_cash_flow'] = ticker_data.get('freeCashflow', 0)
    
    # Calculate net debt (debt minus cash)
    results['net_debt'] = results['total_debt'] - results['total_cash']
    
    # Calculate monthly burn rate (if negative free cash flow)
    annual_fcf = results['free_cash_flow']
    monthly_burn = abs(annual_fcf / 12) if annual_fcf < 0 else 0
    results['monthly_burn_rate'] = monthly_burn
    
    # Calculate cash runway
    if monthly_burn > 0:
        results['cash_runway_months'] = calculate_cash_runway(results['total_cash'], monthly_burn)
    else:
        results['cash_runway_months'] = float('inf')  # No burn rate or positive cash flow
    
    # Calculate debt to EBITDA
    ebitda = ticker_data.get('ebitda', 0)
    if ebitda > 0:
        results['debt_to_ebitda'] = results['total_debt'] / ebitda
    else:
        results['debt_to_ebitda'] = float('inf') if results['total_debt'] > 0 else 0
        
    # Calculate debt to equity
    total_stockholder_equity = ticker_data.get('totalStockholderEquity', 0)
    if total_stockholder_equity > 0:
        results['debt_to_equity'] = results['total_debt'] / total_stockholder_equity
    else:
        results['debt_to_equity'] = float('inf') if results['total_debt'] > 0 else 0
        
    # Calculate cash to market cap ratio (for biotech/unprofitable stocks)
    market_cap = ticker_data.get('marketCap', 0)
    if market_cap > 0:
        results['cash_to_market_cap'] = results['total_cash'] / market_cap
    else:
        results['cash_to_market_cap'] = 0
    
    return results

def process_stock_data(price_data, fundamental_data):
    """
    Process stock data by calculating technical indicators, price statistics, and combining with fundamentals
    
    Args:
        price_data (dict): Dictionary with price data for each symbol
        fundamental_data (dict): Dictionary with fundamental data for each symbol
        
    Returns:
        DataFrame: Processed DataFrame with combined price and fundamental data
    """
    logger.info("Processing stock data...")
    
    # Create empty list to hold processed data for each stock
    processed_stocks = []
    
    # Process each stock
    for symbol, df in price_data.items():
        if df.empty:
            continue
            
        # Calculate technical indicators
        df_with_indicators = calculate_technical_indicators(df)
        
        # Calculate price statistics
        df_with_stats = calculate_price_statistics(df_with_indicators)
        
        # Get the most recent data point
        latest_data = df_with_stats.iloc[-1].copy()
        latest_data['symbol'] = symbol
        
        # Add fundamental ratios if available
        if symbol in fundamental_data and fundamental_data[symbol]:
            ticker_data = fundamental_data[symbol]
            
            # Calculate fundamental ratios
            ratios = calculate_fundamental_ratios(ticker_data, fundamental_data.get(symbol))
            
            # Add debt and cash analysis
            cash_analysis = analyze_debt_and_cash(ticker_data, fundamental_data.get(symbol))
            
            # Combine all data
            combined_data = {**latest_data.to_dict(), **ratios, **cash_analysis}
            processed_stocks.append(combined_data)
        else:
            processed_stocks.append(latest_data.to_dict())
    
    # Convert to DataFrame
    if processed_stocks:
        result_df = pd.DataFrame(processed_stocks)
        
        # Calculate sector relative metrics
        if 'sector' in result_df.columns:
            result_df = normalize_sector_metrics(result_df)
        
        return result_df
    else:
        logger.warning("No stocks could be processed")
        return pd.DataFrame()

def calculate_financial_ratios(fundamental_data):
    """
    Calculate financial ratios for all stocks based on fundamental data
    
    Args:
        fundamental_data (dict): Dictionary with fundamental data for each symbol
        
    Returns:
        DataFrame: DataFrame with financial ratios for all stocks
    """
    logger.info("Calculating financial ratios...")
    
    # Create empty list to hold ratio data for each stock
    ratios_list = []
    
    # Calculate ratios for each stock
    for symbol, ticker_data in fundamental_data.items():
        if ticker_data is None:
            continue
            
        # Calculate fundamental ratios
        ratios = calculate_fundamental_ratios(ticker_data, fundamental_data.get(symbol))
        ratios['symbol'] = symbol
        
        # Add to list
        ratios_list.append(ratios)
    
    # Convert to DataFrame
    if ratios_list:
        ratios_df = pd.DataFrame(ratios_list)
        return ratios_df
    else:
        logger.warning("No financial ratios could be calculated")
        return pd.DataFrame()

if __name__ == "__main__":
    # Simple test for the module
    import numpy as np
    
    # Create test data
    np.random.seed(42)
    test_prices = np.cumsum(np.random.normal(0, 1, 100)) + 100
    
    # Test RSI calculation
    rsi = calculate_rsi(test_prices)
    print(f"RSI (last 5 values): {rsi[-5:]}")
    
    # Test MACD calculation
    macd, signal, hist = calculate_macd(test_prices)
    print(f"MACD (last value): {macd[-1]:.4f}")
    print(f"Signal (last value): {signal[-1]:.4f}")
    print(f"Histogram (last value): {hist[-1]:.4f}")
    
    # Test Bollinger Bands calculation
    upper, middle, lower = calculate_bollinger_bands(test_prices)
    print(f"Bollinger Bands (last values): Upper={upper[-1]:.4f}, Middle={middle[-1]:.4f}, Lower={lower[-1]:.4f}")
