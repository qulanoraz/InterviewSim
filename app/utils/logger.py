# Logging utilities will be defined here 

import logging
import sys

# Basic configuration for console logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def get_logger(name):
    """Returns a configured logger instance."""
    return logging.getLogger(name)

# Example of how to use it in other modules:
# from app.utils.logger import get_logger
# logger = get_logger(__name__)
# logger.info("This is an info message.")
# logger.error("This is an error message.") 