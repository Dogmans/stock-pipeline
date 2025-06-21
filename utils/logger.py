"""
logger.py - Logging functionality for the stock screening pipeline.

This module provides logging setup and retrieval functionality for the application.
Logging should be configured once at application startup, then loggers can be
retrieved throughout the application.
"""

import logging
import os
import config

# Track if logging has been initialized
_logging_initialized = False

def setup_logging():
    """
    Set up global logging configuration for the application.
    
    Creates handlers for both file and console logging.
    Should be called only once at application startup.
    
    Returns:
        logging.Logger: Root logger instance
    """
    global _logging_initialized
    
    if _logging_initialized:
        return logging.getLogger()
    
    # Set up logging
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(config.LOGLEVEL)
    
    # Clear any existing handlers (to prevent duplicates if called multiple times)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add a file handler
    file_handler = logging.FileHandler("stock_pipeline.log")
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)
    
    # Add a console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)
    
    _logging_initialized = True
    return root_logger

def get_logger(name=None):
    """
    Get a logger for the specified module.
    
    This should be used instead of calling setup_logging() in each module.
    Always call with __name__ to ensure proper module identification in logs:
    `logger = get_logger(__name__)`
    
    Args:
        name (str, optional): Name for the logger, usually __name__. Defaults to None.
        
    Returns:
        logging.Logger: Logger instance for the specified name
    """
    if not _logging_initialized:
        setup_logging()
    
    return logging.getLogger(name)

# Initialize a logger for this module
logger = get_logger(__name__)
