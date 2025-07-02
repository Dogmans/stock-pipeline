"""
Common imports and utilities shared by all screeners.
"""

import pandas as pd
import numpy as np
import datetime
import logging
from tqdm import tqdm
from pathlib import Path
import os
import sys

# Add parent directory to path to import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.logger import get_logger
from universe import get_stock_universe
from cache_config import cache
import data_providers

# Get logger for this module
logger = get_logger(__name__)

# Ensure results directory exists
Path(config.RESULTS_DIR).mkdir(parents=True, exist_ok=True)
