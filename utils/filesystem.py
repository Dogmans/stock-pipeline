"""
filesystem.py - File system utility functions for the stock screening pipeline.

This module provides utilities for handling file system operations
like ensuring directories exist.
"""

from pathlib import Path
import logging

import config

# Get logger for this module
logger = logging.getLogger(__name__)

def ensure_directories_exist():
    """
    Ensure all required directories for the application exist.
    
    Creates data and results directories if they don't exist.
    """
    Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    logger.debug("Ensured required directories exist")
