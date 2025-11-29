"""
Analyst Sentiment Momentum Screener

This screener identifies stocks with improving analyst sentiment momentum by analyzing:
1. Rating changes and upgrades/downgrades
2. Estimate revisions and earnings sentiment
3. Price target momentum and consensus changes
4. Analyst coverage changes
5. Overall sentiment score momentum

The screener combines multiple analyst data sources to create a comprehensive
momentum score that captures improving analyst sentiment across ratings,
estimates, and price targets.
"""

import pandas as pd
import logging
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
from .base_screener import BaseScreener
import config

logger = logging.getLogger(__name__)


class AnalystSentimentMomentumScreener(BaseScreener):
    """Analyst sentiment momentum screener."""
    
    def __init__(self, lookback_days=180):
        """
        Initialize with configurable lookback period.
        
        Args:
            lookback_days: Days to look back for historical sentiment analysis
        """
        self.lookback_days = lookback_days
    
    def get_strategy_name(self) -> str:
        """Return the strategy name for this screener."""
        return "Analyst Sentiment Momentum"
    
    def get_strategy_description(self) -> str:
        """Return the strategy description for this screener."""
        return (
            "Identifies stocks with improving analyst sentiment momentum. "
            "Scores based on rating changes (30 pts), price target momentum (25 pts), "
            "estimate revisions (20 pts), consensus strength (15 pts), and coverage changes (10 pts). "
            "Higher scores indicate stronger positive analyst sentiment momentum."
        )
    
    def calculate_score(self, symbol: str, company_data: dict, analyst_data: dict = None) -> float:
        """
        Calculate analyst sentiment momentum score (0-100).
        
        Args:
            symbol: Stock symbol
            company_data: Company overview data
            analyst_data: Preloaded analyst data (optional)
            
        Returns:
            Score between 0-100
        """
        try:
            # If analyst data not provided, we can't calculate score
            if not analyst_data:
                return 0.0
            
            # Extract individual components
            grades_data = analyst_data.get('grades', pd.DataFrame())
            consensus_data = analyst_data.get('consensus', {})
            estimates_data = analyst_data.get('estimates', pd.DataFrame())
            price_targets = analyst_data.get('price_targets', {})
            historical_ratings = analyst_data.get('historical_ratings', pd.DataFrame())
            
            # Component scores
            rating_score = self._calculate_rating_momentum_score(grades_data, consensus_data)
            target_score = self._calculate_price_target_score(price_targets, company_data)
            estimate_score = self._calculate_estimate_revision_score(estimates_data)
            consensus_score = self._calculate_consensus_strength_score(consensus_data)
            coverage_score = self._calculate_coverage_change_score(historical_ratings)
            
            # Weighted final score
            final_score = (
                rating_score * 0.30 +      # Rating changes: 30%
                target_score * 0.25 +      # Price target momentum: 25% 
                estimate_score * 0.20 +    # Estimate revisions: 20%
                consensus_score * 0.15 +   # Consensus strength: 15%
                coverage_score * 0.10      # Coverage changes: 10%
            )
            
            logger.debug(f"Analyst momentum scores for {symbol}: "
                        f"Rating={rating_score:.1f}, Target={target_score:.1f}, "
                        f"Estimate={estimate_score:.1f}, Consensus={consensus_score:.1f}, "
                        f"Coverage={coverage_score:.1f}, Final={final_score:.1f}")
            
            return min(100.0, max(0.0, final_score))
            
        except Exception as e:
            logger.error(f"Error calculating analyst sentiment score for {symbol}: {e}")
            return 0.0
    
    def _calculate_rating_momentum_score(self, grades_df: pd.DataFrame, consensus: dict) -> float:
        """Calculate score based on recent rating changes (0-100)."""
        try:
            if grades_df.empty:
                return 0.0
            
            score = 0.0
            
            # Analyze grade data for sentiment momentum using available columns
            if 'newGrade' in grades_df.columns and 'previousGrade' in grades_df.columns:
                recent_date = datetime.now() - timedelta(days=90)
                recent_grades = grades_df[grades_df['date'] >= recent_date] if 'date' in grades_df.columns else grades_df.head(20)
                
                if not recent_grades.empty:
                    # Count positive vs negative grade changes
                    positive_changes = 0
                    negative_changes = 0
                    maintained = 0
                    
                    # Define grade hierarchy for comparison
                    grade_values = {
                        'strong sell': 1, 'sell': 2, 'underweight': 2, 'underperform': 2,
                        'hold': 3, 'neutral': 3, 'equal weight': 3,
                        'buy': 4, 'overweight': 4, 'outperform': 4,
                        'strong buy': 5
                    }
                    
                    for _, row in recent_grades.iterrows():
                        new_grade = str(row.get('newGrade', '')).lower()
                        prev_grade = str(row.get('previousGrade', '')).lower()
                        
                        # Get numerical values for comparison
                        new_val = grade_values.get(new_grade, 3)
                        prev_val = grade_values.get(prev_grade, 3)
                        
                        if new_val > prev_val:
                            positive_changes += 1
                        elif new_val < prev_val:
                            negative_changes += 1
                        else:
                            maintained += 1
                    
                    # Calculate score based on recent changes
                    total_changes = positive_changes + negative_changes
                    if total_changes > 0:
                        upgrade_ratio = positive_changes / total_changes
                        score += upgrade_ratio * 80  # Up to 80 points for upgrades
                        
                        # Bonus for net positive changes
                        net_changes = positive_changes - negative_changes
                        if net_changes > 0:
                            score += min(20.0, net_changes * 5)  # Up to 20 bonus points
                    
                    # Add points for recent analyst activity (coverage)
                    total_activity = len(recent_grades)
                    score += min(20.0, total_activity * 1)  # Up to 20 points for activity
            
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating rating momentum score: {e}")
            return 0.0

    def _calculate_price_target_score(self, targets: dict, company_data: dict) -> float:
        """Calculate score based on price target momentum (0-100)."""
        try:
            if not targets or not company_data:
                return 0.0
            
            current_price = company_data.get('price', 0)
            if current_price <= 0:
                return 0.0
            
            score = 0.0
            
            # Price target vs current price upside
            target_consensus = targets.get('targetConsensus', 0)
            if target_consensus > 0:
                upside = ((target_consensus - current_price) / current_price) * 100
                
                if upside > 20:  # >20% upside
                    score += 50
                elif upside > 10:  # 10-20% upside
                    score += 30
                elif upside > 5:   # 5-10% upside
                    score += 15
                elif upside < -10:  # >10% downside
                    score -= 25
            
            # Target momentum (recent vs historical)
            last_month_target = targets.get('lastMonthAvgPriceTarget', 0)
            last_quarter_target = targets.get('lastQuarterAvgPriceTarget', 0)
            
            if last_month_target > 0 and last_quarter_target > 0:
                target_momentum = ((last_month_target - last_quarter_target) / last_quarter_target) * 100
                
                if target_momentum > 5:  # Rising targets
                    score += min(30, target_momentum * 3)
                elif target_momentum < -5:  # Falling targets
                    score += max(-20, target_momentum * 2)
            
            # Analyst coverage in targets
            coverage_count = targets.get('lastMonthCount', 0)
            if coverage_count >= 5:
                score += 20  # Good coverage
            elif coverage_count >= 3:
                score += 10  # Moderate coverage
            
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating price target score: {e}")
            return 0.0
    
    def _calculate_estimate_revision_score(self, estimates_df: pd.DataFrame) -> float:
        """Calculate score based on earnings estimate revisions (0-100)."""
        try:
            if estimates_df.empty:
                return 0.0
            
            score = 0.0
            
            # Look at recent estimate changes
            if len(estimates_df) > 1:
                estimates_sorted = estimates_df.sort_values('date') if 'date' in estimates_df.columns else estimates_df
                
                # Compare recent vs older estimates
                recent_estimate = estimates_sorted.iloc[-1]
                previous_estimate = estimates_sorted.iloc[-2] if len(estimates_sorted) > 1 else None
                
                if previous_estimate is not None:
                    # EPS estimate revision
                    recent_eps = recent_estimate.get('epsAvg', 0)
                    previous_eps = previous_estimate.get('epsAvg', 0)
                    
                    if previous_eps != 0:
                        eps_revision = ((recent_eps - previous_eps) / abs(previous_eps)) * 100
                        
                        if eps_revision > 5:  # Positive revision >5%
                            score += min(40, eps_revision * 4)
                        elif eps_revision < -5:  # Negative revision
                            score += max(-25, eps_revision * 2)
                    
                    # Revenue estimate revision
                    recent_revenue = recent_estimate.get('revenueAvg', 0)
                    previous_revenue = previous_estimate.get('revenueAvg', 0)
                    
                    if previous_revenue != 0:
                        revenue_revision = ((recent_revenue - previous_revenue) / abs(previous_revenue)) * 100
                        
                        if revenue_revision > 3:  # Positive revision >3%
                            score += min(30, revenue_revision * 5)
                        elif revenue_revision < -3:  # Negative revision
                            score += max(-20, revenue_revision * 3)
            
            # Number of analysts providing estimates
            num_analysts = estimates_df.iloc[-1].get('numAnalystsEps', 0) if not estimates_df.empty else 0
            if num_analysts >= 5:
                score += 30  # Good coverage
            elif num_analysts >= 3:
                score += 15  # Moderate coverage
            
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating estimate revision score: {e}")
            return 0.0
    
    def _calculate_consensus_strength_score(self, consensus: dict) -> float:
        """Calculate score based on consensus strength (0-100)."""
        try:
            if not consensus:
                return 0.0
            
            total = consensus.get('strongBuy', 0) + consensus.get('buy', 0) + consensus.get('hold', 0) + consensus.get('sell', 0) + consensus.get('strongSell', 0)
            
            if total == 0:
                return 0.0
            
            # Calculate sentiment ratios
            strong_buy_ratio = consensus.get('strongBuy', 0) / total
            buy_ratio = consensus.get('buy', 0) / total
            hold_ratio = consensus.get('hold', 0) / total
            sell_ratio = consensus.get('sell', 0) / total
            strong_sell_ratio = consensus.get('strongSell', 0) / total
            
            # Score based on distribution
            score = (
                strong_buy_ratio * 100 +    # Strong Buy: full points
                buy_ratio * 70 +            # Buy: 70 points
                hold_ratio * 30 +           # Hold: 30 points
                sell_ratio * 10 +           # Sell: 10 points  
                strong_sell_ratio * 0       # Strong Sell: 0 points
            )
            
            # Bonus for strong consensus
            bullish_ratio = strong_buy_ratio + buy_ratio
            if bullish_ratio > 0.7:  # >70% buy/strong buy
                score += 20
            elif bullish_ratio > 0.5:  # >50% buy/strong buy
                score += 10
            
            return min(100.0, score)
            
        except Exception as e:
            logger.error(f"Error calculating consensus strength score: {e}")
            return 0.0
    
    def _calculate_coverage_change_score(self, historical_df: pd.DataFrame) -> float:
        """Calculate score based on analyst coverage changes (0-100)."""
        try:
            if historical_df.empty or len(historical_df) < 2:
                return 50.0  # Neutral score if no data
            
            # Look at coverage trend
            historical_sorted = historical_df.sort_values('date') if 'date' in historical_df.columns else historical_df
            
            recent_total = 0
            older_total = 0
            
            for _, row in historical_sorted.tail(3).iterrows():  # Recent data
                recent_total += (row.get('analystRatingsBuy', 0) + row.get('analystRatingsHold', 0) + 
                               row.get('analystRatingsSell', 0) + row.get('analystRatingsStrongSell', 0))
            
            for _, row in historical_sorted.head(3).iterrows():  # Older data  
                older_total += (row.get('analystRatingsBuy', 0) + row.get('analystRatingsHold', 0) + 
                              row.get('analystRatingsSell', 0) + row.get('analystRatingsStrongSell', 0))
            
            recent_avg = recent_total / 3 if recent_total > 0 else 0
            older_avg = older_total / 3 if older_total > 0 else 0
            
            if older_avg > 0:
                coverage_change = ((recent_avg - older_avg) / older_avg) * 100
                
                if coverage_change > 10:  # Increasing coverage
                    return min(100.0, 50 + coverage_change * 2)
                elif coverage_change < -10:  # Decreasing coverage
                    return max(0.0, 50 + coverage_change)
            
            return 50.0  # Neutral score
            
        except Exception as e:
            logger.error(f"Error calculating coverage change score: {e}")
            return 50.0
    
    def meets_threshold(self, symbol: str, company_data: dict, score: float, analyst_data: dict = None) -> bool:
        """
        Determine if stock meets threshold for inclusion.
        
        Args:
            symbol: Stock symbol
            company_data: Company data
            score: Calculated score
            analyst_data: Analyst data
            
        Returns:
            True if stock meets threshold
        """
        # Basic threshold: score > 1 and some analyst coverage - lowered for testing
        if score < 1:
            return False
        
        # Temporarily disabled strict coverage requirement for testing
        # Will re-enable once consensus API is working properly
        # if analyst_data:
        #     consensus = analyst_data.get('consensus', {})
        #     total_analysts = (consensus.get('strongBuy', 0) + consensus.get('buy', 0) + 
        #                     consensus.get('hold', 0) + consensus.get('sell', 0) + consensus.get('strongSell', 0))
        #     
        #     if total_analysts < 3:  # Minimum coverage requirement
        #         return False
        
        return True
    
    def screen_stocks(self, universe_df, provider=None) -> pd.DataFrame:
        """
        Screen stocks for analyst sentiment momentum.
        
        Args:
            universe_df: DataFrame with stock universe
            provider: Data provider instance
            
        Returns:
            DataFrame with screening results
        """
        if provider is None:
            provider = FinancialModelingPrepProvider()
        
        logger.info(f"Screening for analyst sentiment momentum...")
        
        symbols = universe_df['symbol'].tolist()
        logger.info(f"Analyzing {len(symbols)} symbols for analyst sentiment...")
        
        results = []
        
        for symbol in tqdm(symbols, desc="Analyzing analyst sentiment", unit="symbol"):
            try:
                # Get company overview
                company_data = provider.get_company_overview(symbol)
                if not company_data:
                    continue
                
                # Collect all analyst data
                analyst_data = {}
                
                # Get analyst grades (recent changes)
                analyst_data['grades'] = provider.get_analyst_grades(symbol, limit=50)
                
                # Get consensus ratings
                analyst_data['consensus'] = provider.get_analyst_grades_consensus(symbol)
                
                # Get estimates
                analyst_data['estimates'] = provider.get_analyst_estimates(symbol, period="annual")
                
                # Get price targets
                analyst_data['price_targets'] = provider.get_price_target_summary(symbol)
                
                # Get historical ratings
                analyst_data['historical_ratings'] = provider.get_analyst_grades_historical(symbol, limit=20)
                
                # Calculate score
                score = self.calculate_score(symbol, company_data, analyst_data)
                meets_threshold = self.meets_threshold(symbol, company_data, score, analyst_data)
                
                if meets_threshold:
                    result = {
                        'symbol': symbol,
                        'company_name': company_data.get('companyName', 'Unknown'),
                        'price': company_data.get('price', 0),
                        'market_cap': company_data.get('mktCap', 0),
                        'sector': company_data.get('sector', 'Unknown'),
                        'score': score,
                        'reasoning': self._generate_reasoning(symbol, analyst_data, score)
                    }
                    results.append(result)
                    
                    logger.info(f"Found {symbol}: Analyst Sentiment Momentum (Score: {score:.1f})")
                
            except Exception as e:
                logger.error(f"Error screening {symbol}: {e}")
                continue
        
        if results:
            results_df = pd.DataFrame(results)
            results_df = results_df.sort_values('score', ascending=False)
            logger.info(f"Analyst Sentiment Momentum screener found {len(results)} stocks")
            return results_df
        else:
            logger.warning("No stocks found with significant analyst sentiment momentum")
            return pd.DataFrame()
    
    def _generate_reasoning(self, symbol: str, analyst_data: dict, score: float) -> str:
        """Generate human-readable reasoning for the score."""
        try:
            reasons = []
            
            # Check for recent upgrades
            grades_df = analyst_data.get('grades', pd.DataFrame())
            if not grades_df.empty:
                recent_upgrades = grades_df[grades_df['action'].str.contains('upgrade', case=False, na=False)]
                if len(recent_upgrades) > 0:
                    reasons.append(f"{len(recent_upgrades)} recent analyst upgrade(s)")
            
            # Check consensus
            consensus = analyst_data.get('consensus', {})
            total_analysts = (consensus.get('strongBuy', 0) + consensus.get('buy', 0) + 
                            consensus.get('hold', 0) + consensus.get('sell', 0) + consensus.get('strongSell', 0))
            
            if total_analysts > 0:
                bullish_ratio = (consensus.get('strongBuy', 0) + consensus.get('buy', 0)) / total_analysts
                if bullish_ratio > 0.6:
                    reasons.append(f"{bullish_ratio:.0%} bullish consensus ({total_analysts} analysts)")
            
            # Check price targets
            targets = analyst_data.get('price_targets', {})
            if targets.get('targetConsensus', 0) > 0:
                reasons.append(f"Avg target: ${targets.get('targetConsensus', 0):.2f}")
            
            return "; ".join(reasons) if reasons else f"Score: {score:.1f}"
            
        except Exception as e:
            logger.error(f"Error generating reasoning for {symbol}: {e}")
            return f"Score: {score:.1f}"