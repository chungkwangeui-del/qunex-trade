#!/usr/bin/env python3
"""
Initialize Database Schema

Creates all tables in PostgreSQL database.
Run this once after deploying to Render.com.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import app
from web.database import db

def init_db():
    """Initialize database tables"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully!")

        # List all tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        print(f"\nCreated tables ({len(tables)}):")
        for table in tables:
            print(f"  - {table}")

if __name__ == '__main__':
    init_db()
