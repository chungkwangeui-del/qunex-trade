#!/usr/bin/env python3
"""
Database Migration: Add Multi-Timeframe AI Scores

Adds columns for short-term and long-term AI scores to support
multi-timeframe trading strategy analysis.

Columns added:
- short_term_score: 5-day forward return predictions (1 week)
- long_term_score: 60-day forward return predictions (3 months)
- Keeps existing ai_score as medium-term (20-day)
"""

import os
import sys
import logging
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_migration():
    """Add short_term_score and long_term_score columns to ai_scores table"""
    try:
        from web.app import app, db
        from web.database import AIScore

        with app.app_context():
            logger.info("=" * 80)
            logger.info("DATABASE MIGRATION: Add Multi-Timeframe AI Scores")
            logger.info("=" * 80)

            # Check if columns already exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col["name"] for col in inspector.get_columns("ai_scores")]

            columns_to_add = []
            if "short_term_score" not in columns:
                columns_to_add.append("short_term_score")
            if "long_term_score" not in columns:
                columns_to_add.append("long_term_score")
            if "short_term_rating" not in columns:
                columns_to_add.append("short_term_rating")
            if "long_term_rating" not in columns:
                columns_to_add.append("long_term_rating")

            if not columns_to_add:
                logger.info("✓ Columns already exist - no migration needed")
                logger.info("  - short_term_score: EXISTS")
                logger.info("  - short_term_rating: EXISTS")
                logger.info("  - long_term_score: EXISTS")
                logger.info("  - long_term_rating: EXISTS")
                return True

            logger.info(f"Adding columns: {', '.join(columns_to_add)}")

            # Add columns using raw SQL (SQLite doesn't support IF NOT EXISTS, so we check first)
            with db.engine.connect() as conn:
                if "short_term_score" in columns_to_add:
                    logger.info("Adding short_term_score column (INTEGER)...")
                    conn.execute(db.text(
                        "ALTER TABLE ai_scores ADD COLUMN short_term_score INTEGER"
                    ))
                    conn.commit()
                    logger.info("✓ short_term_score column added")

                if "short_term_rating" in columns_to_add:
                    logger.info("Adding short_term_rating column (VARCHAR)...")
                    conn.execute(db.text(
                        "ALTER TABLE ai_scores ADD COLUMN short_term_rating VARCHAR(20)"
                    ))
                    conn.commit()
                    logger.info("✓ short_term_rating column added")

                if "long_term_score" in columns_to_add:
                    logger.info("Adding long_term_score column (INTEGER)...")
                    conn.execute(db.text(
                        "ALTER TABLE ai_scores ADD COLUMN long_term_score INTEGER"
                    ))
                    conn.commit()
                    logger.info("✓ long_term_score column added")

                if "long_term_rating" in columns_to_add:
                    logger.info("Adding long_term_rating column (VARCHAR)...")
                    conn.execute(db.text(
                        "ALTER TABLE ai_scores ADD COLUMN long_term_rating VARCHAR(20)"
                    ))
                    conn.commit()
                    logger.info("✓ long_term_rating column added")

            # Verify columns were added
            inspector = inspect(db.engine)
            columns_after = [col["name"] for col in inspector.get_columns("ai_scores")]

            logger.info("\n" + "=" * 80)
            logger.info("MIGRATION VERIFICATION")
            logger.info("=" * 80)
            logger.info(f"✓ short_term_score: {'EXISTS' if 'short_term_score' in columns_after else 'MISSING'}")
            logger.info(f"✓ short_term_rating: {'EXISTS' if 'short_term_rating' in columns_after else 'MISSING'}")
            logger.info(f"✓ score (medium-term): {'EXISTS' if 'score' in columns_after else 'MISSING'}")
            logger.info(f"✓ rating (medium-term): {'EXISTS' if 'rating' in columns_after else 'MISSING'}")
            logger.info(f"✓ long_term_score: {'EXISTS' if 'long_term_score' in columns_after else 'MISSING'}")
            logger.info(f"✓ long_term_rating: {'EXISTS' if 'long_term_rating' in columns_after else 'MISSING'}")

            # Check if all expected columns exist
            all_exist = all(col in columns_after for col in ["short_term_score", "short_term_rating", "long_term_score", "long_term_rating", "score", "rating"])

            if all_exist:
                logger.info("\n✓ SUCCESS: All multi-timeframe score columns ready")
                logger.info("=" * 80)
                return True
            else:
                logger.error("\n✗ FAILED: Some columns missing after migration")
                logger.info("=" * 80)
                return False

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
