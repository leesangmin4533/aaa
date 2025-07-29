import logging
import json
from pathlib import Path
import sys

def setup_logging(base_dir: Path, config_filename: str = "config.json") -> logging.Logger:
    """
    Configures the logging system for the application.

    Args:
        base_dir: The base directory of the application (e.g., SCRIPT_DIR).
        config_filename: The name of the configuration file.

    Returns:
        A configured logging.Logger instance.
    """
    config_path = base_dir / config_filename
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: config.json not found at {config_path}. Using default logging settings.")
        config = {} # Fallback to empty config

    log_file_relative_path = config.get("log_file", "logs/automation.log")
    log_file_path = base_dir / log_file_relative_path

    # Create log directory if it doesn't exist
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Get the root logger
    logger = logging.getLogger("bgf_automation") # Use a specific name for the application logger
    logger.setLevel(logging.INFO) # Default log level

    # Prevent adding multiple handlers if setup_logging is called multiple times
    if not logger.handlers:
        # Formatter for log messages
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # File Handler
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console Handler (for immediate feedback)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
