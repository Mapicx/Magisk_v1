import logging
from datetime import datetime
import sys
import os

# ============================================================================
# Configure LLM Operations Logger
# ============================================================================

# Get or create logger
logger = logging.getLogger("LLM_Operations")

def log_event(source: str, message: str):
    """
    Simple unified logger for agent events.
    Appends timestamped logs to ./agent_logs/runtime.log
    """
    timestamp = datetime.now().isoformat()
    log_dir = "./agent_logs"
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "runtime.log"), "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{source}] {message}\n")

# Only configure if not already configured
if not logger.handlers:
    logger.setLevel(logging.INFO)
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler("llm_operations.log", encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console handler for terminal output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Don't propagate to avoid duplicates
    logger.propagate = False
    
    # Force flush to ensure immediate output
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.flush()

def log_llm_operation(operation: str, details: dict, success: bool = True):
    """
    Helper function to log LLM operations to both file and terminal
    """
    # Clean operation name (remove emojis for cleaner logs)
    operation_clean = (operation
        .replace("✅", "[SUCCESS]")
        .replace("❌", "[ERROR]")
        .replace("ℹ️", "[INFO]")
    )
    
    # Convert details dict to clean string, handling large content
    details_clean = {}
    for key, value in details.items():
        if isinstance(value, str):
            # Remove emojis from string values
            value = (value
                .replace("✅", "[SUCCESS]")
                .replace("❌", "[ERROR]")
                .replace("ℹ️", "[INFO]")
            )
            # For very long content, we'll keep it as is since we want to see the full input
        elif isinstance(value, dict):
            # Recursively clean nested dictionaries
            cleaned_nested = {}
            for nested_key, nested_value in value.items():
                if isinstance(nested_value, str):
                    cleaned_nested[nested_key] = (nested_value
                        .replace("✅", "[SUCCESS]")
                        .replace("❌", "[ERROR]")
                        .replace("ℹ️", "[INFO]")
                    )
                else:
                    cleaned_nested[nested_key] = nested_value
            value = cleaned_nested
        details_clean[key] = value
    
    details_str = str(details_clean)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation_clean,
        "success": success,
        "details": details_str
    }
    
    # Build log message
    log_message = f"{operation_clean}: {details_str}"
    
    # Log based on success
    if success:
        logger.info(log_message)
    else:
        logger.error(log_message)
    
    # Force flush to ensure immediate terminal output
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.flush()
    
    # Also flush stdout/stderr
    sys.stdout.flush()
    sys.stderr.flush()
    
    return log_entry