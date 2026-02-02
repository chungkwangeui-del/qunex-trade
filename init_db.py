#!/usr/bin/env python3
"""
Database initialization script for production deployment
Creates all database tables if they don't exist
"""

import os
import sys

# Add web directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "web"))

from web.app import app, db
import logging

logger = logging.getLogger(__name__)



def init_database():
    """Initialize database tables"""
    with app.app_context():
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("✅ Database tables created successfully!")

        # Verify tables were created
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        logger.info(f"📊 Created {len(tables)} tables: {', '.join(tables)}")


if __name__ == "__main__":
    init_database()
