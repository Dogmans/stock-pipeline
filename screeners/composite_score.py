"""
Composite Score Screener - Multi-Factor Valuation Analysis

This screener calculates a comprehensive composite score by analyzing stocks
across multiple dimensions and weighting them based on their importance:
- Value (25%): P/E, P/B, FCF Yield, EV/EBITDA
- Quality (25%): ROE, Profit Margins, Balance Sheet Strength
- Growth (15%): Revenue and Earnings Growth
- Momentum (15%): Price Momentum and Relative Strength
- Analyst (10%): Analyst Consensus and Price Targets
- Technical (10%): Position vs 52-week highs/lows

Each factor is scored 0-100, then weighted to create a final composite score.
This approach finds stocks that are strong across multiple dimensions rather
than just excellent on a single metric.
"""

from .base_screener import BaseScreener
import pandas as pd
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)


class CompositeScoreScreener(BaseScreener):
    """
    Multi-factor composite scoring screener that evaluates stocks across
    all available fundamental, technical, and sentiment dimensions.
    """
    
    def __init__(self):
        super().__init__()
        
        # Define factor weights (must sum to 1.0)
        self.weights = {
            'value': 0.25,      # Value metrics
            'quality': 0.25,    # Quality/profitability metrics
            'growth': 0.15,     # Growth metrics
            'momentum': 0.15,   # Price momentum
            'analyst': 0.10,    # Analyst sentiment
            'technical': 0.10,  # Technical positioning
        }
        
        # Minimum data requirements
        self.min_factors_required = 3  # Need at least 3 factor scores to include stock
    
    def get_strategy_name(self):
        return "Composite Score"
    
    def get_strategy_description(self):
        return ("Multi-factor composite scoring that weights value, quality, growth, "
                "momentum, analyst sentiment, and technical factors to find stocks "
                "with strong overall investment characteristics.")
    
    def get_data_for_symbol(self, symbol):
        """Fetch all data needed for composite scoring."""
        try:
            # Get all available data
            overview = self.provider.get_company_overview(symbol)
            if not overview:
                return None
                
            cash_flow = self.provider.get_cash_flow(symbol)
            income_statement = self.provider.get_income_statement(symbol)
            balance_sheet = self.provider.get_balance_sheet(symbol)
            price_history = self.provider.get_historical_prices([symbol], period="1y")  # 1 year
            # Extract the dataframe for this symbol if returned as dict
            if isinstance(price_history, dict) and symbol in price_history:
                price_history = price_history[symbol]
            price_target = self.provider.get_price_target_consensus(symbol)
            analyst_grades = self.provider.get_analyst_grades_consensus(symbol)
            
            # Flatten structure - put overview fields at top level for BaseScreener compatibility
            # while nesting detailed financials
            result = {
                **overview,  # Unpack overview fields (includes Sector, Name, MarketCapitalization, etc.)
                'symbol': symbol,
                'cash_flow': cash_flow,
                'income_statement': income_statement,
                'balance_sheet': balance_sheet,
                'price_history': price_history,
                'price_target': price_target,
                'analyst_grades': analyst_grades
            }
            
            return result
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_score(self, data):
        """
        Calculate composite score (0-100) across all factors.
        Returns the weighted composite score.
        """
        
        # Calculate individual factor scores
        value_score = self._calculate_value_score(data)
        quality_score = self._calculate_quality_score(data)
        growth_score = self._calculate_growth_score(data)
        momentum_score = self._calculate_momentum_score(data)
        analyst_score = self._calculate_analyst_score(data)
        technical_score = self._calculate_technical_score(data)
        
        # Track which factors have valid scores
        factor_scores = {
            'value': value_score,
            'quality': quality_score,
            'growth': growth_score,
            'momentum': momentum_score,
            'analyst': analyst_score,
            'technical': technical_score
        }
        
        # Count valid factors
        valid_factors = [k for k, v in factor_scores.items() if v is not None]
        
        if len(valid_factors) < self.min_factors_required:
            logger.debug(f"{data['symbol']}: Insufficient data ({len(valid_factors)} factors)")
            return None
        
        # Calculate weighted composite (only for valid factors, normalized)
        total_weight = sum(self.weights[f] for f in valid_factors)
        
        composite = sum(
            factor_scores[factor] * self.weights[factor] 
            for factor in valid_factors
        ) / total_weight
        
        return composite
    
    def _calculate_value_score(self, data):
        """Calculate value score (0-100) based on valuation metrics."""
        cash_flow = data.get('cash_flow')
        
        scores = []
        
        # P/E Ratio Score (lower is better, inverted scale)
        pe = self.safe_float(data.get('PERatio'))
        if pe and 0 < pe < 100:
            # Score: 100 at P/E=5, 50 at P/E=15, 0 at P/E=50+
            pe_score = max(0, min(100, 100 - (pe - 5) * 2.22))
            scores.append(pe_score)
        
        # P/B Ratio Score (lower is better)
        pb = self.safe_float(data.get('PriceToBookRatio'))
        if pb and 0 < pb < 20:
            # Score: 100 at P/B=0.5, 50 at P/B=2, 0 at P/B=5+
            pb_score = max(0, min(100, 100 - (pb - 0.5) * 22.22))
            scores.append(pb_score)
        
        # FCF Yield Score (higher is better)
        if cash_flow is not None and len(cash_flow) > 0:
            latest_cf = cash_flow.iloc[0]
            fcf = self.safe_float(latest_cf.get('freeCashflow') or latest_cf.get('freeCashFlow'))
            market_cap = self.safe_float(data.get('MarketCapitalization'))
            
            if fcf and market_cap and fcf > 0:
                fcf_yield = (fcf / market_cap) * 100
                # Score: 0 at 0%, 50 at 5%, 100 at 10%+
                fcf_score = min(100, fcf_yield * 10)
                scores.append(fcf_score)
        
        # EV/EBITDA Score (lower is better)
        ev_ebitda = self.safe_float(data.get('EVToEBITDA'))
        if ev_ebitda and 0 < ev_ebitda < 50:
            # Score: 100 at EV/EBITDA=3, 50 at EV/EBITDA=10, 0 at EV/EBITDA=20+
            ev_ebitda_score = max(0, min(100, 100 - (ev_ebitda - 3) * 5.88))
            scores.append(ev_ebitda_score)
        
        return np.mean(scores) if scores else None
    
    def _calculate_quality_score(self, data):
        """Calculate quality score (0-100) based on profitability and balance sheet."""
        balance_sheet = data.get('balance_sheet')
        income_statement = data.get('income_statement')
        
        scores = []
        
        # ROE Score (higher is better)
        roe = self.safe_float(data.get('ReturnOnEquityTTM'))
        if roe:
            # Score: 0 at 0%, 50 at 15%, 100 at 30%+
            roe_score = min(100, max(0, roe * 3.33))
            scores.append(roe_score)
        
        # Operating Margin Score (higher is better)
        if income_statement is not None and len(income_statement) > 0:
            latest_is = income_statement.iloc[0]
            operating_income = self.safe_float(latest_is.get('operatingIncome'))
            revenue = self.safe_float(latest_is.get('totalRevenue'))
            
            if operating_income and revenue and revenue > 0:
                op_margin = (operating_income / revenue) * 100
                # Score: 0 at 0%, 50 at 10%, 100 at 20%+
                margin_score = min(100, max(0, op_margin * 5))
                scores.append(margin_score)
        
        # Debt-to-Equity Score (lower is better)
        if balance_sheet is not None and len(balance_sheet) > 0:
            latest_bs = balance_sheet.iloc[0]
            total_debt = self.safe_float(latest_bs.get('totalDebt', 0))
            equity = self.safe_float(latest_bs.get('totalEquity') or latest_bs.get('totalShareholderEquity'))
            
            if equity and equity > 0:
                debt_to_equity = total_debt / equity
                # Score: 100 at D/E=0, 50 at D/E=0.5, 0 at D/E=2+
                de_score = max(0, min(100, 100 - debt_to_equity * 50))
                scores.append(de_score)
        
        # Current Ratio Score (sweet spot around 2.0)
        # Calculate from balance sheet if not in overview
        current_ratio = self.safe_float(data.get('CurrentRatio'))
        if not current_ratio and balance_sheet is not None and len(balance_sheet) > 0:
            latest_bs = balance_sheet.iloc[0]
            current_assets = self.safe_float(latest_bs.get('totalCurrentAssets'))
            current_liabilities = self.safe_float(latest_bs.get('totalCurrentLiabilities'))
            if current_assets and current_liabilities and current_liabilities > 0:
                current_ratio = current_assets / current_liabilities
        
        if current_ratio and current_ratio > 0:
            # Score: Peak at 2.0, declining on either side
            if current_ratio < 2.0:
                cr_score = current_ratio * 50  # 0 at 0, 100 at 2.0
            else:
                cr_score = max(0, 100 - (current_ratio - 2.0) * 20)  # Declining after 2.0
            scores.append(cr_score)
        
        return np.mean(scores) if scores else None
    
    def _calculate_growth_score(self, data):
        """Calculate growth score (0-100) based on revenue and earnings growth."""
        income_statement = data.get('income_statement')
        
        scores = []
        
        # Revenue Growth Score
        revenue_growth = self.safe_float(data.get('RevenueGrowth'))
        if revenue_growth is not None:
            # Convert to percentage
            revenue_growth_pct = revenue_growth * 100
            # Score: 0 at -10%, 50 at 10%, 100 at 30%+
            rev_score = min(100, max(0, 50 + revenue_growth_pct * 1.67))
            scores.append(rev_score)
        
        # Earnings Growth Score (calculate from income statements)
        if income_statement is not None and len(income_statement) >= 2:
            current_earnings = self.safe_float(income_statement.iloc[0].get('netIncome'))
            prior_earnings = self.safe_float(income_statement.iloc[1].get('netIncome'))
            
            if current_earnings and prior_earnings and prior_earnings != 0:
                earnings_growth = ((current_earnings - prior_earnings) / abs(prior_earnings)) * 100
                # Score: 0 at -10%, 50 at 10%, 100 at 30%+
                earn_score = min(100, max(0, 50 + earnings_growth * 1.67))
                scores.append(earn_score)
        
        return np.mean(scores) if scores else None
    
    def _calculate_momentum_score(self, data):
        """Calculate momentum score (0-100) based on price trends."""
        price_history = data.get('price_history')
        
        if price_history is None or len(price_history) < 60:
            return None
        
        scores = []
        
        try:
            # Get closing prices (FMP uses capitalized column names)
            prices = price_history['Close'].values
            current_price = prices[-1]
            
            # 6-month momentum (higher is better)
            if len(prices) >= 126:  # ~6 months
                six_month_return = ((current_price - prices[-126]) / prices[-126]) * 100
                # Score: 0 at -20%, 50 at 0%, 100 at 20%+
                mom_6m_score = min(100, max(0, 50 + six_month_return * 2.5))
                scores.append(mom_6m_score)
            
            # 3-month momentum
            if len(prices) >= 63:  # ~3 months
                three_month_return = ((current_price - prices[-63]) / prices[-63]) * 100
                mom_3m_score = min(100, max(0, 50 + three_month_return * 2.5))
                scores.append(mom_3m_score)
            
            # Relative strength (% of days price increased in last 60 days)
            if len(prices) >= 60:
                recent_prices = prices[-60:]
                up_days = np.sum(np.diff(recent_prices) > 0)
                rs_pct = (up_days / 59) * 100  # 59 because diff reduces length by 1
                # Score directly as percentage
                scores.append(rs_pct)
        
        except Exception as e:
            logger.debug(f"Error calculating momentum for {data['symbol']}: {e}")
            return None
        
        return np.mean(scores) if scores else None
    
    def _calculate_analyst_score(self, data):
        """Calculate analyst score (0-100) based on consensus and targets."""
        price_target = data.get('price_target', {})
        analyst_grades = data.get('analyst_grades', {})
        
        scores = []
        
        # Price Target Upside Score
        target_price = self.safe_float(price_target.get('targetConsensus'))
        current_price = self.safe_float(data.get('Price'))
        
        if target_price and current_price and current_price > 0:
            upside = ((target_price - current_price) / current_price) * 100
            # Score: 0 at -20% downside, 50 at 0%, 100 at 30%+ upside
            upside_score = min(100, max(0, 50 + upside * 1.67))
            scores.append(upside_score)
        
        # Analyst Rating Score
        if analyst_grades:
            strong_buy = self.safe_float(analyst_grades.get('strongBuy', 0))
            buy = self.safe_float(analyst_grades.get('buy', 0))
            hold = self.safe_float(analyst_grades.get('hold', 0))
            sell = self.safe_float(analyst_grades.get('sell', 0))
            strong_sell = self.safe_float(analyst_grades.get('strongSell', 0))
            
            total = strong_buy + buy + hold + sell + strong_sell
            
            if total > 0:
                # Weighted score: StrongBuy=100, Buy=75, Hold=50, Sell=25, StrongSell=0
                weighted_rating = (
                    strong_buy * 100 + 
                    buy * 75 + 
                    hold * 50 + 
                    sell * 25 + 
                    strong_sell * 0
                ) / total
                scores.append(weighted_rating)
        
        return np.mean(scores) if scores else None
    
    def _calculate_technical_score(self, data):
        """Calculate technical score (0-100) based on price positioning."""
        price_history = data.get('price_history')
        
        if price_history is None or len(price_history) < 252:
            return None
        
        scores = []
        
        try:
            # Get price data (FMP uses capitalized column names)
            high_prices = price_history['High'].values
            low_prices = price_history['Low'].values
            current_price = self.safe_float(data.get('Price'))
            
            if not current_price:
                current_price = price_history['Close'].values[-1]
            
            # 52-week high/low positioning
            week_52_high = np.max(high_prices[-252:])
            week_52_low = np.min(low_prices[-252:])
            
            if week_52_high > week_52_low:
                # Position in range (0% = at low, 100% = at high)
                position_score = ((current_price - week_52_low) / 
                                (week_52_high - week_52_low)) * 100
                
                # Prefer stocks in the middle to upper range (40-80% is sweet spot)
                if position_score < 40:
                    # Too close to lows - risky
                    range_score = position_score * 1.25  # 0-50
                elif position_score <= 80:
                    # Sweet spot
                    range_score = 50 + (position_score - 40) * 1.25  # 50-100
                else:
                    # Near highs - less upside
                    range_score = 100 - (position_score - 80) * 2.5  # 100-50
                
                scores.append(range_score)
        
        except Exception as e:
            logger.debug(f"Error calculating technical score for {data['symbol']}: {e}")
            return None
        
        return np.mean(scores) if scores else None
    
    def meets_threshold(self, score):
        """
        A stock meets the threshold if composite score >= 60.
        This indicates above-average performance across multiple factors.
        
        Args:
            score: Composite score (0-100)
            
        Returns:
            True if score >= 60
        """
        return score is not None and score >= 60.0
    
    def get_additional_data(self, symbol, data, current_price):
        """Add factor breakdown to the results."""
        # Calculate individual factor scores for display
        value_score = self._calculate_value_score(data)
        quality_score = self._calculate_quality_score(data)
        growth_score = self._calculate_growth_score(data)
        momentum_score = self._calculate_momentum_score(data)
        analyst_score = self._calculate_analyst_score(data)
        technical_score = self._calculate_technical_score(data)
        
        # Get composite score
        composite = self.calculate_score(data)
        
        # Format factor scores
        factor_breakdown = []
        if value_score is not None:
            factor_breakdown.append(f"Value: {value_score:.0f}")
        if quality_score is not None:
            factor_breakdown.append(f"Quality: {quality_score:.0f}")
        if growth_score is not None:
            factor_breakdown.append(f"Growth: {growth_score:.0f}")
        if momentum_score is not None:
            factor_breakdown.append(f"Momentum: {momentum_score:.0f}")
        if analyst_score is not None:
            factor_breakdown.append(f"Analyst: {analyst_score:.0f}")
        if technical_score is not None:
            factor_breakdown.append(f"Technical: {technical_score:.0f}")
        
        # Build reason string
        pe = self.safe_float(data.get('PERatio'))
        roe = self.safe_float(data.get('ReturnOnEquityTTM'))
        
        reason_parts = [f"Composite score: {composite:.1f}/100"]
        if pe:
            reason_parts.append(f"P/E: {pe:.1f}")
        if roe:
            reason_parts.append(f"ROE: {roe:.1f}%")
        
        return {
            'composite_score': round(composite, 1) if composite else None,
            'value_score': round(value_score, 0) if value_score else None,
            'quality_score': round(quality_score, 0) if quality_score else None,
            'growth_score': round(growth_score, 0) if growth_score else None,
            'momentum_score': round(momentum_score, 0) if momentum_score else None,
            'analyst_score': round(analyst_score, 0) if analyst_score else None,
            'technical_score': round(technical_score, 0) if technical_score else None,
            'factor_breakdown': ' | '.join(factor_breakdown),
            'reason': ' | '.join(reason_parts)
        }
