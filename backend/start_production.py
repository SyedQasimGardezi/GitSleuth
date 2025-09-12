#!/usr/bin/env python3
"""Production startup script for GitSleuth API"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from config import config
from utils.logger import get_logger

def main():
    """Main production startup function"""
    logger = get_logger(__name__)
    
    try:
        # Validate configuration
        logger.info("Starting GitSleuth API in production mode")
        logger.info(f"Configuration loaded: {config.get_all()}")
        
        # Create necessary directories
        os.makedirs("logs", exist_ok=True)
        os.makedirs("cache", exist_ok=True)
        os.makedirs(config.get('CHROMA_DB_PATH'), exist_ok=True)
        
        # Start the server
        uvicorn.run(
            "main:app",
            host=config.get('API_HOST', '0.0.0.0'),
            port=config.get('API_PORT', 8000),
            workers=config.get('API_WORKERS', 1),
            reload=config.get('API_RELOAD', False),
            log_level=config.get('LOG_LEVEL', 'info').lower(),
            access_log=True,
            server_header=False,
            date_header=False
        )
        
    except Exception as e:
        logger.error(f"Failed to start production server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
