#!/usr/bin/env python3
"""
Database Migration: Add explanation_json column to ai_scores table

This migration adds the explanation_json column to the ai_scores table
if it doesn't already exist. This column stores SHAP-like feature
contribution explanations for AI score calculations.
"""

import os
import sys
import logging
from sqlalchemy import text

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_dir = os.path.join(parent_dir, "web")
sys.path.insert(0, web_dir)
sys.path.insert(0, parent_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def migrate():
    """Add explanation_json column to ai_scores table if it doesn't exist"""
    try:
        from web.app import app
        from web.database import db

        logger.info("Starting migration: Add explanation_json column to ai_scores table")

        with app.app_context():
            # Check if column already exists
            result = db.session.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'ai_scores'
                    AND column_name = 'explanation_json'
                """
                )
            )

            if result.fetchone():
                logger.info(
                    "Column explanation_json already exists in ai_scores table. Skipping migration."
                )
                return True

            # Add the column
            logger.info("Adding explanation_json column to ai_scores table...")
            db.session.execute(text("ALTER TABLE ai_scores ADD COLUMN explanation_json TEXT"))
            db.session.commit()

            logger.info("Migration completed successfully!")
            return True

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("DATABASE MIGRATION: Add explanation_json to ai_scores")
    print("=" * 80)

    success = migrate()

    print("=" * 80)
    print(f"Migration Status: {'✓ SUCCESS' if success else '✗ FAILED'}")
    print("=" * 80)

    sys.exit(0 if success else 1)
