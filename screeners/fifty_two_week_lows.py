"""
52-Week Lows Screener module.
Screens for stocks trading near their 52-week low price.
"""

import pandas as pd
import logging
from tqdm import tqdm
from .base_screener import BaseScreener
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
from market_data import is_market_in_correction
import config

logger = logging.getLogger(__name__)


class FiftyTwoWeekLowsScreener(BaseScreener):
    """Screener for stocks trading near their 52-week lows."""
    
    def get_strategy_name(self) -> str:
        """Return the strategy name for this screener."""
        return "52-Week Lows"
    
    def get_strategy_description(self) -> str:
        """Return the strategy description for this screener."""
        return ("Finds quality stocks trading near their 52-week lows, potentially indicating "
                "temporary undervaluation or buying opportunities during market downturns.")
    
    def screen_stocks(self, universe_df, provider=None) -> pd.DataFrame:
        """
        Override base screen_stocks to handle historical price data requirements.
        
        Args:
            universe_df: DataFrame with stock universe
            provider: Data provider instance
            
        Returns:
            DataFrame with screening results
        """
        if provider is None:
            provider = FinancialModelingPrepProvider()
        
        logger.info("Screening for stocks near 52-week lows...")
        
        # Check market status
        try:
            in_correction, status = is_market_in_correction()
            logger.info(f"Market status: {status}")
        except Exception as e:
            logger.error(f"Error checking market correction status: {e}")
        
        # Extract symbols from universe  
        symbols = universe_df['symbol'].tolist()
        results = []
        
        # Process each symbol individually
        for symbol in tqdm(symbols, desc="Screening for stocks near 52-week lows", unit="symbol"):
            try:
                # Get historical price data for the last year
                price_data = provider.get_historical_prices(symbol, period="1y")
                
                # Skip if we couldn't get price data
                if symbol not in price_data or price_data[symbol] is None or price_data[symbol].empty:
                    continue
                
                data = price_data[symbol]
                company_data = provider.get_company_overview(symbol)
                
                # Calculate score using standard interface
                score = self.calculate_score(symbol, company_data, price_data=data)
                meets_threshold = self.meets_threshold(symbol, company_data, score, price_data=data)
                
                # Get detailed metrics
                detailed_metrics = self.get_detailed_metrics(symbol, company_data, score, price_data=data)
                
                # Extract company info
                company_name = company_data.get('Name', symbol) if company_data else symbol
                sector = company_data.get('Sector', 'Unknown') if company_data else 'Unknown'
                
                result = {
                    'symbol': symbol,
                    'company_name': company_name,
                    'sector': sector,
                    'score': score,
                    'meets_threshold': meets_threshold,
                    'reason': self._create_reason_string(symbol, company_data, score, detailed_metrics),
                    **detailed_metrics
                }
                
                results.append(result)
                
                if meets_threshold:
                    logger.debug(f"Found {symbol} near 52-week low: {detailed_metrics['pct_above_low']:.2f}% above low")
                    
            except Exception as e:
                logger.error(f"Error processing {symbol} for 52-week low screening: {e}")
                continue
        
        # Convert to DataFrame and sort by percentage above low (lowest first)
        if results:
            df = pd.DataFrame(results)
            df = df.sort_values('pct_above_low')
            logger.info(f"52-week low screening completed. Found {len(df[df['meets_threshold']])} stocks meeting criteria")
            return df
        else:
            logger.warning("No results from 52-week low screening")
            return pd.DataFrame()
    
    def calculate_score(self, symbol: str, company_data: dict, price_data=None) -> float:
        """
        Calculate 52-week low score based on proximity to annual low.
        
        Args:
            symbol: Stock symbol
            company_data: Company data dictionary
            price_data: Historical price data DataFrame
            
        Returns:
            Score based on percentage above 52-week low (lower is better, inverted for scoring)
        """
        if price_data is None or price_data.empty:
            return 0.0
        
        try:
            # Calculate 52-week high, low, and current price
            high_52week = price_data['High'].max()
            low_52week = price_data['Low'].min()
            current_price = price_data['Close'].iloc[-1]
            
            # Calculate percentage above 52-week low
            pct_above_low = ((current_price - low_52week) / low_52week) * 100
            
            # Convert to score (lower percentage above low = higher score)
            # Score range 0-100, where stocks at 52-week low get 100, stocks 50% above low get 0
            if pct_above_low <= 0:
                return 100.0
            elif pct_above_low >= 50:
                return 0.0
            else:
                # Linear scale: 0% above low = 100 points, 50% above low = 0 points
                return 100 - (pct_above_low * 2)
                
        except Exception as e:
            logger.error(f"Error calculating 52-week low score for {symbol}: {e}")
            return 0.0
    
    def meets_threshold(self, symbol: str, company_data: dict, score: float, price_data=None) -> bool:
        """
        Check if stock meets 52-week low threshold.
        
        Args:
            symbol: Stock symbol
            company_data: Company data dictionary
            score: Calculated score
            price_data: Historical price data DataFrame
            
        Returns:
            True if stock is close enough to 52-week low
        """
        if price_data is None or price_data.empty:
            return False
        
        try:
            # Calculate percentage above 52-week low
            low_52week = price_data['Low'].min()
            current_price = price_data['Close'].iloc[-1]
            pct_above_low = ((current_price - low_52week) / low_52week) * 100
            
            # Use config threshold or default
            max_pct_above_low = getattr(config.ScreeningThresholds, 'MAX_PERCENT_OFF_52_WEEK_LOW', 20.0)
            
            return pct_above_low <= max_pct_above_low
            
        except Exception:
            return False
    
    def get_detailed_metrics(self, symbol: str, company_data: dict, score: float, price_data=None) -> dict:
        """Get detailed 52-week low metrics for a stock."""
        if price_data is None or price_data.empty:
            return {
                'current_price': 0,
                '52_week_high': 0,
                '52_week_low': 0,
                'pct_off_high': 0,
                'pct_above_low': 0,
                'ytd_change': None
            }
        
        try:
            # Calculate 52-week high, low, and current price
            high_52week = price_data['High'].max()
            low_52week = price_data['Low'].min()
            current_price = price_data['Close'].iloc[-1]
            
            # Calculate percentage metrics
            pct_off_high = ((high_52week - current_price) / high_52week) * 100
            pct_above_low = ((current_price - low_52week) / low_52week) * 100
            
            # Calculate YTD change
            ytd_change = None
            try:
                start_year_data = price_data[price_data.index.year == price_data.index[0].year].iloc[0]
                ytd_change = ((current_price / start_year_data['Close']) - 1) * 100
            except Exception:
                pass
            
            return {
                'current_price': current_price,
                '52_week_high': high_52week,
                '52_week_low': low_52week,
                'pct_off_high': pct_off_high,
                'pct_above_low': pct_above_low,
                'ytd_change': ytd_change,
                'market_cap': company_data.get('MarketCapitalization', 0) if company_data else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting detailed metrics for {symbol}: {e}")
            return {
                'current_price': 0,
                '52_week_high': 0,
                '52_week_low': 0,
                'pct_off_high': 0,
                'pct_above_low': 0,
                'ytd_change': None,
                'market_cap': 0
            }
    
    def _create_reason_string(self, symbol: str, company_data: dict, score: float, metrics: dict) -> str:
        """Create descriptive reason string for the screening result."""
        pct_above_low = metrics.get('pct_above_low', 0)
        
        if self.meets_threshold(symbol, company_data, score):
            return f"Near 52-week low ({pct_above_low:.2f}% above low)"
        else:
            return f"52-week low status: {pct_above_low:.2f}% above low"
