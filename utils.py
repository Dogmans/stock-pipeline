"""
utils.py - Common utilities for the stock screening pipeline.

This module provides shared utility functions used across the stock screening pipeline,
including logging setup, directory creation, and common helper functions.

Functions:
    setup_logging(): Set up the logging configuration
    ensure_directories_exist(): Ensure required directories exist
"""

import os
import logging
from pathlib import Path

import config

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

def ensure_directories_exist():
    """
    Ensure all required directories for the application exist.
    
    Creates data and results directories if they don't exist.
    """
    Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    
# Set up logger for this module
logger = setup_logging()

# Ensure directories exist when module is imported
ensure_directories_exist()

if __name__ == "__main__":
    logger.info("Utils module initialized successfully")
