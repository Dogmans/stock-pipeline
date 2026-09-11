"""
Pre-Pump Insider Buying Screener
Flags stocks with recent spikes in insider buying activity combined with technical consolidation patterns.

This screener analyzes:
1. Insider buying acceleration (recent vs historical activity)
2. Technical consolidation patterns (price stability, volume analysis)
3. Buying activity strength (acquisitions vs dispositions)
4. Transaction volumes and frequency
5. Insider types and diversity (executives, directors, etc.)
6. Pre-pump technical setup (support levels, low volatility)
"""

import pandas as pd
import logging
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from tqdm import tqdm
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
from .base_screener import BaseScreener
import config

logger = logging.getLogger(__name__)


class InsiderBuyingScreener(BaseScreener):
    """Pre-pump insider buying screener with technical consolidation analysis."""
    
    def __init__(self, lookback_days=60):
        """Initialize with configurable lookback period."""
        self.lookback_days = lookback_days
    
    def get_strategy_name(self) -> str:
        """Return the strategy name for this screener."""
        return "Insider Buying"
    
    def get_strategy_description(self) -> str:
        """Return the strategy description for this screener."""
        return ("Detects pre-pump insider buying patterns combined with technical consolidation. "
                "Scores consider insider activity (40 pts), technical setup (35 pts), and acceleration patterns (25 pts). "
                "Only stocks with actual insider purchases receive non-zero scores.")
    
    def screen_stocks(self, universe_df, provider=None) -> pd.DataFrame:
        """
        Override base screen_stocks to handle special insider data collection.
        
        Args:
            universe_df: DataFrame with stock universe
            provider: Data provider instance
            
        Returns:
            DataFrame with screening results
        """
        if provider is None:
            provider = FinancialModelingPrepProvider()
        
        logger.info(f"Screening for pre-pump insider buying patterns (lookback: {self.lookback_days} days)...")
        
        # Extract symbols from universe  
        symbols = universe_df['symbol'].tolist()
        logger.info(f"Analyzing {len(symbols)} symbols for insider trading activity...")
        
        # Collect insider trading data for each symbol
        all_insider_data = []
        symbols_with_data = 0
        
        for symbol in tqdm(symbols, desc="Fetching insider trading data", unit="symbol"):
            try:
                symbol_trades = provider.get_insider_trading(symbol, self.lookback_days)
                logger.debug(f"Retrieved {len(symbol_trades) if symbol_trades else 0} trades for {symbol}")
                if symbol_trades:
                    all_insider_data.extend(symbol_trades)
                    symbols_with_data += 1
            except Exception as e:
                logger.error(f"Error fetching insider data for {symbol}: {e}")
                continue
        
        logger.info(f"Found {len(all_insider_data)} insider trades for {symbols_with_data} symbols in universe")
        
        if not all_insider_data:
            logger.warning("No insider trading data available for any symbols in universe")
            return pd.DataFrame()
        
        # Group trades by symbol
        symbol_trades = defaultdict(list)
        for trade in all_insider_data:
            symbol_trades[trade['symbol']].append(trade)
        
        # Process each symbol
        results = []
        
        for symbol in tqdm(symbol_trades.keys(), desc="Analyzing pre-pump patterns", unit="symbol"):
            try:
                trades = symbol_trades[symbol]
                company_data = provider.get_company_overview(symbol)
                
                # Calculate score using standard interface
                detailed_metrics = self.get_detailed_metrics(symbol, company_data, None, trades, provider)
                score = self._total_score(detailed_metrics)
                meets_threshold = self.meets_threshold(symbol, company_data, score, trades)
                
                
                # Get company info from universe and provider data
                company_info = universe_df[universe_df['symbol'] == symbol]
                company_name = company_info['security'].iloc[0] if not company_info.empty else symbol
                # Use provider data for sector (consistent with BaseScreener)
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
                    logger.debug(f"Found {symbol} with high pre-pump score: {score:.1f}/100")
                    
            except Exception as e:
                logger.error(f"Error analyzing insider buying for {symbol}: {e}")
                continue
        
        # Convert to DataFrame and sort by score
        if results:
            df = pd.DataFrame(results)
            df = df.sort_values('score', ascending=False)
            logger.info(f"Pre-pump analysis completed. Found {len(df[df['meets_threshold']])} stocks above threshold")
            return df
        else:
            logger.warning("No pre-pump patterns found")
            return pd.DataFrame()
    
    def calculate_score(self, symbol: str, company_data: dict, trades=None) -> float:
        """
        Calculate pre-pump insider buying score.
        
        Args:
            symbol: Stock symbol
            company_data: Company data dictionary
            trades: List of insider trading data
            
        Returns:
            Pre-pump score (0-100)
        """
        metrics = self.get_detailed_metrics(symbol, company_data, None, trades)
        return self._total_score(metrics)

    @staticmethod
    def _total_score(metrics):
        return min(100.0, metrics['insider_activity_score'] +
                   metrics['acceleration_score'] + metrics['technical_score'])

    def meets_threshold(self, symbol: str, company_data: dict, score: float, trades=None) -> bool:
        """
        Check if stock meets insider buying threshold.
        
        Args:
            symbol: Stock symbol
            company_data: Company data dictionary  
            score: Calculated score
            trades: List of insider trading data
            
        Returns:
            True if score meets minimum threshold
        """
        min_score = getattr(config.ScreeningThresholds, 'MIN_INSIDER_BUYING_SCORE', 65.0)
        return score >= min_score
    
    def get_detailed_metrics(self, symbol: str, company_data: dict, score: float,
                             trades=None, provider=None) -> dict:
        """Return raw insider metrics and the exact contributions to the score."""
        insider = self._analyze_insider_activity(trades or [])
        metrics = {key: insider[key] for key in (
            'total_trades', 'buy_trades', 'sell_trades', 'net_shares',
            'buy_value', 'sell_value', 'unique_insiders')}
        eligible = insider['buy_trades'] > 0
        metrics.update(
            insider_activity_score=insider['activity_score'] if eligible else 0.0,
            acceleration_score=insider['acceleration_score'] if eligible else 0.0,
            **self._empty_technical_metrics('Not evaluated: no insider purchases'))
        if eligible:
            metrics.update(self._technical_metrics(symbol, provider))
        return metrics

    def _create_reason_string(self, symbol: str, company_data: dict, score: float, metrics: dict) -> str:
        """Create descriptive reason string for the screening result."""
        if metrics.get('buy_trades', 0) == 0:
            return "No insider buying activity detected"
        
        reason = f"Pre-pump score: {score:.1f}/100"
        if metrics.get('total_trades', 0) > 0:
            reason += f" - {metrics['buy_trades']} buy trades vs {metrics['sell_trades']} sells"
        reason += (f" - Activity {metrics['insider_activity_score']:.1f}/40"
                   f", acceleration {metrics['acceleration_score']:.1f}/25"
                   f", consolidation {metrics['consolidation_score']:.1f}/20"
                   f", volume {metrics['volume_score']:.1f}/15")
        if metrics['technical_status'] != 'Available':
            reason += f" - Technical data: {metrics['technical_status']}"
        
        return reason
    
    def _analyze_insider_activity(self, trades):
        """Analyze basic insider trading activity patterns."""
        buy_trades = []
        sell_trades = []
        unique_insiders = set()
        executive_trades = 0
        director_trades = 0
        
        for trade in trades:
            # Track unique insiders
            unique_insiders.add(trade.get('reportingName', ''))
            
            # Categorize by insider type
            owner_type = trade.get('typeOfOwner', '').lower()
            if 'officer' in owner_type or 'ceo' in owner_type or 'cfo' in owner_type:
                executive_trades += 1
            elif 'director' in owner_type:
                director_trades += 1
            
            # Categorize by transaction type - FIXED METHODOLOGY
            acquisition = trade.get('acquisitionOrDisposition', '').upper()
            transaction_type = trade.get('transactionType', '').upper()
            
            # Only consider ACTUAL PURCHASES with real money as buying signals:
            # - A-P-Purchase: Open market purchases with personal money
            # - Only transactions with price > 0 (exclude $0 option exercises)
            price = trade.get('price', 0)
            
            if (acquisition == 'A' and 
                ('PURCHASE' in transaction_type or 
                 'BUY' in transaction_type)):
                # Must have actual price paid (not $0 option exercises)
                if price > 0 and not ('AWARD' in transaction_type or 'GRANT' in transaction_type):
                    buy_trades.append(trade)
            elif (acquisition == 'D' and 
                  ('SALE' in transaction_type or 
                   'SELL' in transaction_type)):
                sell_trades.append(trade)
        
        # Calculate trade values
        buy_value = sum(trade.get('securitiesTransacted', 0) * trade.get('price', 0) for trade in buy_trades)
        sell_value = sum(trade.get('securitiesTransacted', 0) * trade.get('price', 0) for trade in sell_trades)
        net_shares = sum(trade.get('securitiesTransacted', 0) for trade in buy_trades) - sum(trade.get('securitiesTransacted', 0) for trade in sell_trades)
        
        total_trades = len(trades)
        avg_trade_size = (buy_value + sell_value) / total_trades if total_trades > 0 else 0
        
        # Calculate insider activity score (40 points max)
        activity_score = 0
        
        # Buy vs sell ratio (0-25 points)
        if total_trades > 0:
            buy_ratio = len(buy_trades) / total_trades
            activity_score += buy_ratio * 25
        
        # Net buying activity (0-10 points)
        if net_shares > 0:
            activity_score += min(10, net_shares / 10000)
        
        # Insider diversity (0-5 points)
        if len(unique_insiders) > 1:
            activity_score += min(5, len(unique_insiders))
        
        # Calculate acceleration score (25 points max)
        acceleration_score = self._analyze_buying_acceleration(trades)
        
        return {
            'total_trades': total_trades,
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'net_shares': net_shares,
            'buy_value': buy_value,
            'sell_value': sell_value,
            'unique_insiders': len(unique_insiders),
            'executive_trades': executive_trades,
            'director_trades': director_trades,
            'avg_trade_size': avg_trade_size,
            'activity_score': min(40, activity_score),
            'acceleration_score': acceleration_score
        }
    
    def _analyze_buying_acceleration(self, trades):
        """Analyze acceleration in buying activity (0-25 points)."""
        if not trades:
            return 0
        
        # Split trades into recent (30 days) vs older periods
        recent_cutoff = datetime.now() - timedelta(days=30)
        recent_trades = []
        older_trades = []
        
        for trade in trades:
            try:
                trade_date = datetime.strptime(trade['transactionDate'], '%Y-%m-%d')
                if trade_date >= recent_cutoff:
                    recent_trades.append(trade)
                else:
                    older_trades.append(trade)
            except:
                continue
        
        score = 0
        
        # Recent activity acceleration (0-15 points)
        if len(older_trades) > 0:
            acceleration_ratio = len(recent_trades) / len(older_trades)
            if acceleration_ratio > 1.5:  # 50% more recent activity
                score += min(15, acceleration_ratio * 5)
        elif len(recent_trades) >= 2:  # No historical data but recent activity
            score += 10
        
        # Recent volume surge (0-10 points)
        recent_buy_count = sum(1 for trade in recent_trades 
                              if trade.get('acquisitionOrDisposition', '').upper() == 'A')
        if recent_buy_count >= 2:
            score += min(10, recent_buy_count * 2)
        
        return min(25, score)
    
    @staticmethod
    def _empty_technical_metrics(status):
        return dict(technical_score=0.0, consolidation_score=0.0, volume_score=0.0,
                    consolidation_detected=None, annualized_volatility=None,
                    relative_volume=None, technical_status=status)

    def _calculate_technical_score(self, symbol, trades=None):
        return self._technical_metrics(symbol)['technical_score']

    def _technical_metrics(self, symbol, provider=None):
        """Use the provider's symbol-keyed, chronological OHLCV frames."""
        metrics = self._empty_technical_metrics('Unavailable: insufficient price history')
        try:
            provider = provider if provider is not None else FinancialModelingPrepProvider()
            history = provider.get_historical_prices(symbol, period='3mo', interval='1d')
            df = history.get(symbol)
            if df is None or len(df) < 30 or 'Close' not in df:
                return metrics
            df = df.sort_index()
            closes = pd.to_numeric(df['Close'], errors='coerce')
            if not np.isfinite(closes).all() or (closes <= 0).any():
                metrics['technical_status'] = 'Unavailable: invalid closing prices'
                return metrics
            volatility = closes.pct_change(fill_method=None).tail(30).std() * np.sqrt(252)
            consolidation = max(0.0, 20 - volatility * 100) if volatility < 0.15 else 0.0
            metrics.update(annualized_volatility=float(volatility),
                           consolidation_detected=bool(volatility < 0.15),
                           consolidation_score=float(consolidation),
                           technical_score=float(consolidation),
                           technical_status='Partial: volume unavailable')
            if 'Volume' not in df:
                return metrics
            volumes = pd.to_numeric(df['Volume'], errors='coerce')
            if not np.isfinite(volumes).all() or (volumes < 0).any() or volumes.mean() <= 0:
                return metrics
            ratio = volumes.tail(10).mean() / volumes.mean()
            volume_score = min(15.0, ratio * 5) if ratio > 1.2 else 0.0
            metrics.update(relative_volume=float(ratio), volume_score=float(volume_score),
                           technical_score=float(min(35, consolidation + volume_score)),
                           technical_status='Available')
            return metrics
        except Exception as exc:
            logger.debug(f"Technical analysis failed for {symbol}: {exc}")
            return self._empty_technical_metrics('Unavailable: price data error')
