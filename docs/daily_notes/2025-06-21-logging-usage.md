# Logging Usage Audit - 2025-06-21

## Logger Usage Analysis

Today I audited the codebase to ensure all uses of `get_logger()` are properly passing `__name__` as an argument. This is important to maintain accurate module identification in logs.

### Results

✅ **All instances of `get_logger()` correctly pass `__name__` as an argument.**

The audit found:
- 11 modules using `get_logger()` 
- All modules correctly pass `__name__` as the argument
- No instances of `get_logger()` being called without an argument
- No instances of `get_logger()` being called with a hardcoded string

### Implementation Pattern

The consistent pattern throughout the codebase is:

```python
from utils.logger import get_logger

# Module-level logger instance
logger = get_logger(__name__)
```

Special case in `main.py` where the logger is initialized inside the `main()` function:

```python
def main():
    # Setup logging - only here in main.py since this is the entry point
    setup_logging()
    
    # Get a logger for this module
    logger = get_logger(__name__)
    logger.info("Starting stock screening pipeline")
    # ...
```

### Benefits of This Approach

1. **Accurate Module Identification**: Each log message includes the correct module name in the output
2. **Hierarchical Logging Control**: Logging levels can be adjusted for specific modules or packages
3. **Consistent Log Format**: All logs follow the same format with correct module attribution
4. **Initialization Management**: The `get_logger()` function handles initialization of the logging system

### Best Practice Reminder

Always initialize loggers at module level, outside of any function or class, unless there's a specific reason to do otherwise (as in `main.py`). This ensures that the logger is available throughout the module without being repeatedly created.

```python
# At module level, outside of any function
from utils.logger import get_logger
logger = get_logger(__name__)

def some_function():
    logger.info("Function running")  # Uses the module-level logger
```
