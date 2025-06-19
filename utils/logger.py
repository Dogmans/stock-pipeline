"""
logger.py - Logging functionality for the stock screening pipeline.

This module provides logging setup functionality for the application.
"""

import logging

def setup_logging():
    """
    Set up logging configuration for the application.
    
    Creates a logger with both file and console handlers.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("stock_pipeline.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize a logger for this module
logger = logging.getLogger(__name__)
