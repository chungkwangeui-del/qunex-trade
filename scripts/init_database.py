#!/usr/bin/env python3
"""
Initialize Database Schema

Creates all tables in PostgreSQL database.
Run this once after deploying to Render.com.

Usage:
    python scripts/init_database.py

    Or from Render Shell:
    cd /opt/render/project/src && python scripts/init_database.py
"""

import os
import sys

# Add web directory to Python path
web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
sys.path.insert(0, web_dir)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def init_db():
    """Initialize database tables without importing full Flask app"""
    try:
        # Import Flask and SQLAlchemy directly
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy

        # Get DATABASE_URL from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ ERROR: DATABASE_URL environment variable not set!")
            print("Set it in Render Dashboard or .env file")
            return False

        # Fix psycopg2 driver issue - use psycopg instead
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://")
        elif database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://")

        print(f"Connecting to database...")
        print(f"Database: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")

        # Create minimal Flask app
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        # Initialize SQLAlchemy
        db = SQLAlchemy(app)

        # Import all models to register them with SQLAlchemy
        print("\nImporting database models...")
        from database import User, Watchlist, NewsArticle, EconomicEvent, AIScore

        # Create all tables
        with app.app_context():
            print("\nCreating database tables...")
            db.create_all()
            print("✅ Database tables created successfully!")

            # List all tables
            from sqlalchemy import inspect

            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            print(f"\n📊 Created tables ({len(tables)}):")
            for table in sorted(tables):
                print(f"  ✓ {table}")

            # Verify AIScore table specifically
            if "ai_scores" in tables:
                print("\n🎯 SUCCESS: ai_scores table is ready for AI Score cron job!")
            else:
                print("\n⚠️  WARNING: ai_scores table not found!")

            return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE INITIALIZATION")
    print("=" * 60)

    success = init_db()

    if success:
        print("\n" + "=" * 60)
        print("✅ INITIALIZATION COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Verify AI Score cron job is running daily")
        print("2. Test the platform: qunextrade.onrender.com")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ INITIALIZATION FAILED")
        print("=" * 60)
        sys.exit(1)
