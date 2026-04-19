#!/usr/bin/env python3
"""
Database initialization script
Run this to create the database tables and apply migrations
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.logging_config import setup_logging

logger = setup_logging()

def init_database():
    """Initialize database tables"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
