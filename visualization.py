"""
Visualization module for stock screening pipeline.
Provides visualizations of screening results and market conditions.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
import os
from pathlib import Path

import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure results directory exists
Path(config.RESULTS_DIR).mkdir(parents=True, exist_ok=True)

def plot_52_week_lows(df):
    """
    Plot stocks near 52-week lows
    
    Args:
        df (DataFrame): DataFrame with 52-week low screening results
        
    Returns:
        plotly.Figure: Interactive plot of stocks near 52-week lows
    """
    if df is None or df.empty:
        logger.warning("No data to plot for 52-week lows")
        return None
    
    # Create a scatter plot of percentage off high vs percentage above low
    fig = px.scatter(
        df,
        x='pct_above_low',
        y='pct_off_high',
        color='sector',
        size='market_cap',
        hover_name='company_name',
        text='symbol',
        log_x=True,
        size_max=60,
        title='Stocks Near 52-Week Lows'
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title='% Above 52-Week Low (log scale)',
        yaxis_title='% Off 52-Week High',
        hovermode='closest'
    )
    
    # Add a diagonal line to represent stocks that are exactly at their 52-week low
    fig.add_shape(
        type='line',
        x0=0,
        y0=0,
        x1=100,
        y1=100,
        line=dict(
            color='gray',
            dash='dash',
        )
    )
    
    # Save the figure
    filepath = os.path.join(config.RESULTS_DIR, "52_week_lows.html")
    fig.write_html(filepath)
    logger.info(f"Saved 52-week lows plot to {filepath}")
    
    return fig

def plot_pe_ratios(df):
    """
    Plot stocks with low P/E ratios
    
    Args:
        df (DataFrame): DataFrame with P/E ratio screening results
        
    Returns:
        plotly.Figure: Interactive plot of stocks with low P/E ratios
    """
    if df is None or df.empty:
        logger.warning("No data to plot for P/E ratios")
        return None
    
    # Create a scatter plot of P/E ratio vs market cap
    fig = px.scatter(
        df,
        x='pe_ratio',
        y='market_cap',
        color='sector',
        hover_name='company_name',
        text='symbol',
        log_y=True,
        title='Stocks with Low P/E Ratios'
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title='P/E Ratio',
        yaxis_title='Market Cap (log scale)',
        hovermode='closest'
    )
    
    # Add a vertical line at the Graham/Buffett threshold
    fig.add_vline(
        x=10,
        line_dash='dash',
        line_color='green',
        annotation_text='Graham/Buffett Threshold'
    )
    
    # Save the figure
    filepath = os.path.join(config.RESULTS_DIR, "pe_ratios.html")
    fig.write_html(filepath)
    logger.info(f"Saved P/E ratios plot to {filepath}")
    
    return fig

def plot_price_to_book(df):
    """
    Plot stocks trading near book value
    
    Args:
        df (DataFrame): DataFrame with price-to-book screening results
        
    Returns:
        plotly.Figure: Interactive plot of stocks trading near book value
    """
    if df is None or df.empty:
        logger.warning("No data to plot for price-to-book ratios")
        return None
    
    # Create a scatter plot of price-to-book ratio vs market cap
    fig = px.scatter(
        df,
        x='price_to_book',
        y='market_cap',
        color='sector',
        hover_name='company_name',
        text='symbol',
        log_y=True,
        title='Stocks Trading Near Book Value'
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title='Price-to-Book Ratio',
        yaxis_title='Market Cap (log scale)',
        hovermode='closest'
    )
    
    # Add a vertical line at price-to-book = 1
    fig.add_vline(
        x=1.0,
        line_dash='dash',
        line_color='red',
        annotation_text='Book Value'
    )
    
    # Save the figure
    filepath = os.path.join(config.RESULTS_DIR, "price_to_book.html")
    fig.write_html(filepath)
    logger.info(f"Saved price-to-book plot to {filepath}")
    
    return fig

def plot_cash_rich_biotech(df):
    """
    Plot biotech stocks with high cash-to-market-cap ratios
    
    Args:
        df (DataFrame): DataFrame with cash-rich biotech screening results
        
    Returns:
        plotly.Figure: Interactive plot of cash-rich biotech stocks
    """
    if df is None or df.empty:
        logger.warning("No data to plot for cash-rich biotech stocks")
        return None
    
    # Create a scatter plot of cash-to-market-cap ratio vs cash runway
    fig = px.scatter(
        df,
        x='cash_to_mc_ratio',
        y='cash_runway_months',
        size='market_cap',
        hover_name='company_name',
        text='symbol',
        log_y=True,
        size_max=60,
        title='Cash-Rich Biotech Stocks'
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title='Cash-to-Market-Cap Ratio',
        yaxis_title='Cash Runway (Months, log scale)',
        hovermode='closest'
    )
    
    # Add a horizontal line at 18 months (minimum safe runway)
    fig.add_hline(
        y=18,
        line_dash='dash',
        line_color='orange',
        annotation_text='Minimum Safe Runway'
    )
    
    # Add a vertical line at cash-to-market-cap = 1
    fig.add_vline(
        x=1.0,
        line_dash='dash',
        line_color='green',
        annotation_text='Cash = Market Cap'
    )
    
    # Save the figure
    filepath = os.path.join(config.RESULTS_DIR, "cash_rich_biotech.html")
    fig.write_html(filepath)
    logger.info(f"Saved cash-rich biotech plot to {filepath}")
    
    return fig

def plot_sector_performance(df):
    """
    Plot sector performance
    
    Args:
        df (DataFrame): DataFrame with sector performance data
        
    Returns:
        plotly.Figure: Interactive plot of sector performance
    """
    if df is None or df.empty:
        logger.warning("No data to plot for sector performance")
        return None
    
    # Create a bar chart of 1-month sector performance
    fig = px.bar(
        df,
        y='sector',
        x='1_month_change',
        color='1_month_change',
        color_continuous_scale='RdYlGn',
        title='Sector Performance (1-Month Change)'
    )
    
    # Update layout
    fig.update_layout(
        yaxis_title='Sector',
        xaxis_title='1-Month Change (%)',
        hovermode='closest'
    )
    
    # Add vertical lines at -20% (bear market) and -10% (correction)
    fig.add_vline(
        x=-20,
        line_dash='dash',
        line_color='red',
        annotation_text='Bear Market'
    )
    
    fig.add_vline(
        x=-10,
        line_dash='dash',
        line_color='orange',
        annotation_text='Correction'
    )
    
    # Save the figure
    filepath = os.path.join(config.RESULTS_DIR, "sector_performance.html")
    fig.write_html(filepath)
    logger.info(f"Saved sector performance plot to {filepath}")
    
    return fig

def plot_combined_results(df):
    """
    Plot combined screening results
    
    Args:
        df (DataFrame): DataFrame with combined screening results
        
    Returns:
        plotly.Figure: Interactive plot of combined screening results
    """
    if df is None or df.empty:
        logger.warning("No data to plot for combined results")
        return None
    
    # Filter to only stocks with score > 0
    df_filtered = df[df['score'] > 0].sort_values('score', ascending=False)
    
    if df_filtered.empty:
        logger.warning("No stocks with score > 0")
        return None
    
    # Create a bar chart of stock scores
    fig = px.bar(
        df_filtered.head(20),  # Show top 20 stocks
        y='symbol',
        x='score',
        color='score',
        hover_name='company_name',
        color_continuous_scale='Viridis',
        title='Top Stocks Meeting Multiple Criteria'
    )
    
    # Update layout
    fig.update_layout(
        yaxis_title='Stock',
        xaxis_title='Score (Criteria Met)',
        hovermode='closest'
    )
    
    # Save the figure
    filepath = os.path.join(config.RESULTS_DIR, "combined_results.html")
    fig.write_html(filepath)
    logger.info(f"Saved combined results plot to {filepath}")
    
    return fig

def plot_market_vix_history(market_data):
    """
    Plot VIX history to visualize market fear
    
    Args:
        market_data (dict): Dictionary with market data including VIX
        
    Returns:
        plotly.Figure: Interactive plot of VIX history
    """
    if not market_data or 'VIX' not in market_data or market_data['VIX'] is None or market_data['VIX'].empty:
        logger.warning("No VIX data to plot")
        return None
    
    vix_data = market_data['VIX']
    
    # Create a line chart of VIX history
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=vix_data.index,
        y=vix_data['Close'],
        mode='lines',
        name='VIX'
    ))
    
    # Add horizontal lines at VIX thresholds
    fig.add_hline(
        y=config.VIX_BLACK_SWAN_THRESHOLD,
        line_dash='dash',
        line_color='red',
        annotation_text='Black Swan Event'
    )
    
    fig.add_hline(
        y=config.VIX_CORRECTION_THRESHOLD,
        line_dash='dash',
        line_color='orange',
        annotation_text='Market Correction'
    )
    
    # Update layout
    fig.update_layout(
        title='VIX History (Market Fear Gauge)',
        xaxis_title='Date',
        yaxis_title='VIX',
        hovermode='closest'
    )
    
    # Save the figure
    filepath = os.path.join(config.RESULTS_DIR, "vix_history.html")
    fig.write_html(filepath)
    logger.info(f"Saved VIX history plot to {filepath}")
    
    return fig

def create_stock_detail_chart(symbol, price_data):
    """
    Create detailed chart for a specific stock
    
    Args:
        symbol (str): Stock symbol
        price_data (DataFrame): Historical price data for the stock
        
    Returns:
        plotly.Figure: Interactive chart of stock price and key indicators
    """
    if price_data is None or price_data.empty:
        logger.warning(f"No price data for {symbol}")
        return None
    
    # Create a subplot with price, volume, and RSI
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(f"{symbol} Price", "Volume", "RSI"),
        row_heights=[0.6, 0.2, 0.2]
    )
    
    # Price chart with OHLC
    fig.add_trace(go.Candlestick(
        x=price_data.index,
        open=price_data['Open'],
        high=price_data['High'],
        low=price_data['Low'],
        close=price_data['Close'],
        name='Price'
    ), row=1, col=1)
    
    # Add moving averages if available
    if 'sma_50' in price_data.columns:
        fig.add_trace(go.Scatter(
            x=price_data.index,
            y=price_data['sma_50'],
            line=dict(color='blue', width=1),
            name='50-Day MA'
        ), row=1, col=1)
    
    if 'sma_200' in price_data.columns:
        fig.add_trace(go.Scatter(
            x=price_data.index,
            y=price_data['sma_200'],
            line=dict(color='red', width=1),
            name='200-Day MA'
        ), row=1, col=1)
    
    # Volume chart
    fig.add_trace(go.Bar(
        x=price_data.index,
        y=price_data['Volume'],
        marker_color='blue',
        opacity=0.5,
        name='Volume'
    ), row=2, col=1)
    
    # RSI chart if available
    if 'rsi' in price_data.columns:
        fig.add_trace(go.Scatter(
            x=price_data.index,
            y=price_data['rsi'],
            line=dict(color='purple'),
            name='RSI'
        ), row=3, col=1)
        
        # Add horizontal lines at RSI 30 and 70
        fig.add_hline(
            y=30,
            line_dash='dash',
            line_color='green',
            row=3,
            col=1
        )
        
        fig.add_hline(
            y=70,
            line_dash='dash',
            line_color='red',
            row=3,
            col=1
        )
    
    # Update layout
    fig.update_layout(
        title=f"{symbol} Technical Analysis",
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        height=800
    )
    
    # Save the figure
    filepath = os.path.join(config.RESULTS_DIR, f"{symbol}_chart.html")
    fig.write_html(filepath)
    logger.info(f"Saved {symbol} chart to {filepath}")
    
    return fig

def create_dashboard(screening_results):
    """
    Create a comprehensive dashboard of screening results
    
    Args:
        screening_results (dict): Dictionary with results from various screeners
        
    Returns:
        str: Path to the HTML dashboard file
    """
    # Create an HTML file with all the visualizations
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stock Screening Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            .header { background-color: #f5f5f5; padding: 20px; margin-bottom: 20px; border-bottom: 1px solid #ddd; }
            .section { margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            h1 { color: #333; }
            h2 { color: #666; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); grid-gap: 20px; }
            .card { background-color: white; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); padding: 15px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f5f5f5; }
            tr:hover { background-color: #f5f5f5; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Stock Screening Dashboard</h1>
            <p>Based on the "15 Tools for Stock Picking" strategies</p>
            <p>Generated on: """ + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
        </div>
    """
    
    # Add market status section
    html_content += """
        <div class="section">
            <h2>Market Status</h2>
    """
    
    # Add VIX chart if available
    vix_chart_path = os.path.join(config.RESULTS_DIR, "vix_history.html")
    if os.path.exists(vix_chart_path):
        html_content += """
            <iframe src="vix_history.html" width="100%" height="400px" frameborder="0"></iframe>
        """
    
    # Add sector performance chart if available
    sector_chart_path = os.path.join(config.RESULTS_DIR, "sector_performance.html")
    if os.path.exists(sector_chart_path):
        html_content += """
            <iframe src="sector_performance.html" width="100%" height="500px" frameborder="0"></iframe>
        """
    
    html_content += """
        </div>
    """
    
    # Add top combined results section
    html_content += """
        <div class="section">
            <h2>Top Stock Picks (Combined Criteria)</h2>
    """
    
    combined_chart_path = os.path.join(config.RESULTS_DIR, "combined_results.html")
    if os.path.exists(combined_chart_path):
        html_content += """
            <iframe src="combined_results.html" width="100%" height="600px" frameborder="0"></iframe>
        """
    
    # Add table of top combined results
    if 'combined_results' in screening_results and not screening_results['combined_results'].empty:
        df = screening_results['combined_results']
        top_picks = df.sort_values('score', ascending=False).head(10)
        
        html_content += """
            <h3>Top 10 Stock Picks</h3>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Company</th>
                    <th>Price</th>
                    <th>Score</th>
                    <th>Criteria Met</th>
                </tr>
        """
        
        for _, row in top_picks.iterrows():
            criteria = []
            if row.get('meets_book_value_criteria', False):
                criteria.append("Book Value")
            if row.get('meets_pe_ratio_criteria', False):
                criteria.append("Low P/E")
            if row.get('meets_52week_low_criteria', False):
                criteria.append("52-Week Low")
            if row.get('is_fallen_ipo', False):
                criteria.append("Fallen IPO")
            if row.get('is_cash_rich_biotech', False):
                criteria.append("Cash-Rich Biotech")
                
            html_content += f"""
                <tr>
                    <td>{row['symbol']}</td>
                    <td>{row.get('company_name', row['symbol'])}</td>
                    <td>${row.get('current_price', 'N/A'):.2f}</td>
                    <td>{row['score']}</td>
                    <td>{', '.join(criteria)}</td>
                </tr>
            """
        
        html_content += """
            </table>
        """
    
    html_content += """
        </div>
    """
    
    # Add individual screener sections
    screener_sections = [
        {
            'title': 'Stocks Trading Near Book Value',
            'key': 'book_value_stocks',
            'chart': 'price_to_book.html'
        },
        {
            'title': 'Stocks with Low P/E Ratios',
            'key': 'low_pe_stocks',
            'chart': 'pe_ratios.html'
        },
        {
            'title': 'Stocks Near 52-Week Lows',
            'key': '52week_low_stocks',
            'chart': '52_week_lows.html'
        },
        {
            'title': 'Cash-Rich Biotech Stocks',
            'key': 'cash_rich_biotech',
            'chart': 'cash_rich_biotech.html'
        }
    ]
    
    for section in screener_sections:
        html_content += f"""
            <div class="section">
                <h2>{section['title']}</h2>
        """
        
        chart_path = os.path.join(config.RESULTS_DIR, section['chart'])
        if os.path.exists(chart_path):
            html_content += f"""
                <iframe src="{section['chart']}" width="100%" height="500px" frameborder="0"></iframe>
            """
        
        if section['key'] in screening_results and not screening_results[section['key']].empty:
            df = screening_results[section['key']]
            top_picks = df.head(5)
            
            html_content += f"""
                <h3>Top 5 {section['title']}</h3>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Company</th>
                        <th>Price</th>
            """
            
            # Add custom columns based on screener type
            if section['key'] == 'book_value_stocks':
                html_content += """
                        <th>Book Value</th>
                        <th>P/B Ratio</th>
                """
            elif section['key'] == 'low_pe_stocks':
                html_content += """
                        <th>P/E Ratio</th>
                        <th>Forward P/E</th>
                """
            elif section['key'] == '52week_low_stocks':
                html_content += """
                        <th>% Off High</th>
                        <th>% Above Low</th>
                """
            elif section['key'] == 'cash_rich_biotech':
                html_content += """
                        <th>Cash/MC Ratio</th>
                        <th>Cash Runway</th>
                """
            
            html_content += """
                    </tr>
            """
            
            for _, row in top_picks.iterrows():
                html_content += f"""
                    <tr>
                        <td>{row['symbol']}</td>
                """
                
                # Handle different column names for company name
                if 'company_name' in row:
                    html_content += f"""
                        <td>{row['company_name']}</td>
                    """
                elif 'name' in row:
                    html_content += f"""
                        <td>{row['name']}</td>
                    """
                else:
                    html_content += """
                        <td>N/A</td>
                    """
                
                # Handle different column names for price
                if 'current_price' in row:
                    html_content += f"""
                        <td>${row['current_price']:.2f}</td>
                    """
                elif 'price' in row:
                    html_content += f"""
                        <td>${row['price']:.2f}</td>
                    """
                else:
                    html_content += """
                        <td>N/A</td>
                    """
                
                # Add custom columns based on screener type
                if section['key'] == 'book_value_stocks':
                    html_content += f"""
                        <td>${row.get('book_value_per_share', 0):.2f}</td>
                        <td>{row.get('price_to_book', 0):.2f}</td>
                    """
                elif section['key'] == 'low_pe_stocks':
                    html_content += f"""
                        <td>{row.get('pe_ratio', 0):.2f}</td>
                        <td>{row.get('forward_pe', 0):.2f}</td>
                    """
                elif section['key'] == '52week_low_stocks':
                    html_content += f"""
                        <td>{row.get('pct_off_high', 0):.2f}%</td>
                        <td>{row.get('pct_above_low', 0):.2f}%</td>
                    """
                elif section['key'] == 'cash_rich_biotech':
                    html_content += f"""
                        <td>{row.get('cash_to_mc_ratio', 0):.2f}</td>
                        <td>{row.get('cash_runway_months', 0):.1f} months</td>
                    """
                
                html_content += """
                    </tr>
                """
            
            html_content += """
                </table>
            """
        
        html_content += """
            </div>
        """
    
    # Close the HTML
    html_content += """
    </body>
    </html>
    """
    
    # Save the dashboard to a file
    filepath = os.path.join(config.RESULTS_DIR, "dashboard.html")
    with open(filepath, 'w') as f:
        f.write(html_content)
    
    logger.info(f"Created dashboard at {filepath}")
    
    return filepath

if __name__ == "__main__":
    logger.info("Testing visualization module...")
    
    # Test with sample data
    import yfinance as yf
    
    # Test stock chart
    aapl_data = yf.download("AAPL", period="1y")
    if not aapl_data.empty:
        create_stock_detail_chart("AAPL", aapl_data)
        
    # Test VIX history
    vix_data = yf.download("^VIX", period="1y")
    if not vix_data.empty:
        plot_market_vix_history({'VIX': vix_data})
        
    logger.info("Visualization module test complete")
