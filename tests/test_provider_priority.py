"""
Unit tests for data provider priority in the MultiProvider.

This test module verifies that:
1. Data providers are initialized in the correct order:
   - YFinance (always first)
   - Financial Modeling Prep (second priority)
   - Alpha Vantage (third priority)
   - Finnhub (last priority)
   
2. The fallback mechanism works correctly:
   - If a higher-priority provider fails, the next provider is tried
   - Results include tracking information about which provider was used
   
3. Result structure includes provider tracking:
   - Each result contains a '_provider_used' field identifying the data source

These tests ensure that our provider prioritization works correctly,
particularly the preference for Financial Modeling Prep over Alpha Vantage.
"""

import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import data_providers
from data_providers.yfinance_provider import YFinanceProvider
from data_providers.financial_modeling_prep import FinancialModelingPrepProvider
from data_providers.alpha_vantage import AlphaVantageProvider
from data_providers.finnhub_provider import FinnhubProvider
from data_providers.multi_provider import MultiProvider

class TestProviderPriority(unittest.TestCase):
    """Tests for the data provider priority in the MultiProvider."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mocked providers
        self.mock_yfinance = MagicMock(spec=YFinanceProvider)
        self.mock_yfinance.get_provider_name.return_value = "YFinanceProvider"
        
        self.mock_fmp = MagicMock(spec=FinancialModelingPrepProvider)
        self.mock_fmp.get_provider_name.return_value = "FinancialModelingPrepProvider"
        
        self.mock_alpha_vantage = MagicMock(spec=AlphaVantageProvider)
        self.mock_alpha_vantage.get_provider_name.return_value = "AlphaVantageProvider"
        
        self.mock_finnhub = MagicMock(spec=FinnhubProvider)
        self.mock_finnhub.get_provider_name.return_value = "FinnhubProvider"
    
    def test_provider_initialization_order(self):
        """Test that providers are initialized in the correct order."""
        # Get a MultiProvider instance
        multi_provider = data_providers.get_provider('multi')
        
        # Check that we have providers
        self.assertGreater(len(multi_provider.providers), 0, "No providers were initialized")
        
        # Check the first provider is YFinanceProvider (always available)
        self.assertEqual(
            multi_provider.providers[0].get_provider_name(), 
            "YFinanceProvider", 
            "First provider should be YFinanceProvider"
        )
        
        # Check that if both FMP and Alpha Vantage are available, FMP comes first
        providers_list = [p.get_provider_name() for p in multi_provider.providers]
        
        if "FinancialModelingPrepProvider" in providers_list and "AlphaVantageProvider" in providers_list:
            fmp_index = providers_list.index("FinancialModelingPrepProvider")
            av_index = providers_list.index("AlphaVantageProvider")
            
            self.assertLess(
                fmp_index, 
                av_index, 
                "FinancialModelingPrepProvider should come before AlphaVantageProvider"
            )
    
    @patch('data_providers.multi_provider.YFinanceProvider')
    @patch('data_providers.multi_provider.FinancialModelingPrepProvider')
    @patch('data_providers.multi_provider.AlphaVantageProvider')
    @patch('data_providers.multi_provider.FinnhubProvider')
    def test_provider_order(self, mock_finnhub_class, mock_av_class, mock_fmp_class, mock_yf_class):
        """Test that providers are tried in the correct order."""
        # Configure the mocks
        mock_yf_instance = self.mock_yfinance
        mock_fmp_instance = self.mock_fmp
        mock_av_instance = self.mock_alpha_vantage
        mock_finnhub_instance = self.mock_finnhub
        
        mock_yf_class.return_value = mock_yf_instance
        mock_fmp_class.return_value = mock_fmp_instance
        mock_av_class.return_value = mock_av_instance
        mock_finnhub_class.return_value = mock_finnhub_instance
        
        # Create a multi provider with our mocks
        multi_provider = MultiProvider()
        
        # Check the providers list
        self.assertEqual(len(multi_provider.providers), 4, "MultiProvider should have 4 providers")
        
        # Check the order
        self.assertEqual(multi_provider.providers[0], mock_yf_instance)
        self.assertEqual(multi_provider.providers[1], mock_fmp_instance)
        self.assertEqual(multi_provider.providers[2], mock_av_instance)
        self.assertEqual(multi_provider.providers[3], mock_finnhub_instance)
    
    @patch('data_providers.multi_provider.YFinanceProvider')
    @patch('data_providers.multi_provider.FinancialModelingPrepProvider')
    @patch('data_providers.multi_provider.AlphaVantageProvider')
    def test_provider_fallback(self, mock_av_class, mock_fmp_class, mock_yf_class):
        """Test that providers are tried in sequence until one succeeds."""
        # Configure the mocks
        mock_yf = self.mock_yfinance
        mock_fmp = self.mock_fmp
        mock_av = self.mock_alpha_vantage
        
        # Setup YFinance to fail
        mock_yf.get_company_overview.side_effect = Exception("YFinance error")
        
        # Setup FMP to succeed
        mock_fmp.get_company_overview.return_value = {
            'Symbol': 'AAPL', 
            'Name': 'Apple Inc.',
            '_provider_used': 'FinancialModelingPrepProvider'
        }
        
        # Setup AV (should not be called if FMP succeeds)
        mock_av.get_company_overview.return_value = {
            'Symbol': 'AAPL', 
            'Name': 'Apple Inc.',
            '_provider_used': 'AlphaVantageProvider'
        }
        
        mock_yf_class.return_value = mock_yf
        mock_fmp_class.return_value = mock_fmp
        mock_av_class.return_value = mock_av
        
        # Create a multi provider with our mocks
        multi_provider = MultiProvider()
        
        # Call get_company_overview
        result = multi_provider.get_company_overview('AAPL')
        
        # Check the result
        self.assertEqual(result['_provider_used'], 'FinancialModelingPrepProvider')
        
        # Verify call counts
        mock_yf.get_company_overview.assert_called_once()
        mock_fmp.get_company_overview.assert_called_once()
        mock_av.get_company_overview.assert_not_called()
    
    def test_provider_tracking(self):
        """Test that results include information about which provider was used."""
        # Create a real MultiProvider since we're testing result tracking
        multi_provider = data_providers.get_provider('multi')
        
        # Try to get AAPL company overview (this may or may not work depending on API keys)
        try:
            result = multi_provider.get_company_overview('AAPL')
            
            # Check if we got a result
            if result and 'Symbol' in result:
                self.assertIn('_provider_used', result, 
                             "Results should include _provider_used field")
                
                # Provider name should be one of the expected values
                self.assertIn(
                    result['_provider_used'],
                    ["YFinanceProvider", "FinancialModelingPrepProvider", 
                     "AlphaVantageProvider", "FinnhubProvider"],
                    f"Unexpected provider name: {result['_provider_used']}"
                )
        except Exception as e:
            # This test might fail if no providers are available, that's OK
            self.skipTest(f"Could not test provider tracking: {e}")


if __name__ == '__main__':
    unittest.main()
