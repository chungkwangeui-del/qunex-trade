#!/usr/bin/env python3
"""
System Health Check - 시스템 전체 상태 점검

자동으로 시스템의 모든 구성요소를 점검하고 문제를 진단합니다:
- 데이터베이스 연결 및 테이블 상태
- ML 모델 파일 존재 및 로딩
- API 키 설정
- 뉴스 데이터 수집 상태
- AI Score 업데이트 상태
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, "ml"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SystemHealthChecker:
    """시스템 전체 상태 점검 클래스"""

    def __init__(self):
        self.issues = []
        self.warnings = []
        self.successes = []

    def check_all(self) -> Dict:
        """모든 시스템 구성요소 점검"""
        logger.info("=" * 80)
        logger.info("SYSTEM HEALTH CHECK STARTED")
        logger.info("=" * 80)

        results = {
            "database": self.check_database(),
            "ml_models": self.check_ml_models(),
            "api_keys": self.check_api_keys(),
            "news_data": self.check_news_data(),
            "ai_scores": self.check_ai_scores(),
            "github_actions": self.check_github_actions(),
        }

        self.print_summary(results)
        return results

    def check_database(self) -> Dict:
        """데이터베이스 연결 및 테이블 점검"""
        logger.info("\n[1/6] Checking Database Connection...")
        result = {"status": "unknown", "details": []}

        try:
            from web.app import app, db
            from web.database import AIScore, NewsArticle, Watchlist
            from sqlalchemy import inspect

            with app.app_context():
                # Check connection
                db.session.execute(db.text("SELECT 1"))
                result["details"].append("✅ Database connection: OK")

                # Check tables
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()

                required_tables = ["ai_scores", "news_articles", "watchlist", "users"]
                for table in required_tables:
                    if table in tables:
                        result["details"].append(f"✅ Table '{table}': EXISTS")
                    else:
                        result["details"].append(f"❌ Table '{table}': MISSING")
                        self.issues.append(f"Missing table: {table}")

                # Check ai_scores columns for multi-timeframe
                columns = [col["name"] for col in inspector.get_columns("ai_scores")]
                multi_frame_cols = ["short_term_score", "short_term_rating", "long_term_score", "long_term_rating"]

                all_cols_exist = all(col in columns for col in multi_frame_cols)
                if all_cols_exist:
                    result["details"].append("✅ Multi-timeframe columns: ALL PRESENT")
                else:
                    missing = [col for col in multi_frame_cols if col not in columns]
                    result["details"].append(f"⚠️ Missing columns: {missing}")
                    self.warnings.append(f"Run migration: python scripts/migrate_add_multiframe_scores.py")

                # Count records
                ai_score_count = db.session.query(AIScore).count()
                news_count = db.session.query(NewsArticle).count()
                watchlist_count = db.session.query(Watchlist).count()

                result["details"].append(f"📊 AI Scores: {ai_score_count} stocks")
                result["details"].append(f"📰 News Articles: {news_count} articles")
                result["details"].append(f"⭐ Watchlist Items: {watchlist_count} items")

                if ai_score_count == 0:
                    self.warnings.append("No AI scores in database - run cron job")
                if news_count == 0:
                    self.warnings.append("No news articles - run data refresh")

                result["status"] = "healthy"
                self.successes.append("Database connection and schema")

        except Exception as e:
            result["status"] = "error"
            result["details"].append(f"❌ Error: {e}")
            self.issues.append(f"Database error: {e}")

        return result

    def check_ml_models(self) -> Dict:
        """ML 모델 파일 존재 및 로딩 점검"""
        logger.info("\n[2/6] Checking ML Models...")
        result = {"status": "unknown", "details": []}

        try:
            model_dir = os.path.join(parent_dir, "ml", "models")
            model_files = {
                "Short-term (5d)": "ai_score_model_5d.pkl",
                "Medium-term (20d)": "ai_score_model_20d.pkl",
                "Long-term (60d)": "ai_score_model_60d.pkl",
            }

            # Check file existence
            all_exist = True
            for name, filename in model_files.items():
                path = os.path.join(model_dir, filename)
                if os.path.exists(path):
                    size_mb = os.path.getsize(path) / (1024 * 1024)
                    result["details"].append(f"✅ {name}: EXISTS ({size_mb:.2f} MB)")
                else:
                    result["details"].append(f"❌ {name}: MISSING")
                    all_exist = False
                    self.issues.append(f"Missing model: {filename}")

            # Try loading models
            if all_exist:
                from ai_score_system import MultiTimeframeAIScoreModel

                multi_model = MultiTimeframeAIScoreModel(model_dir=model_dir)
                if multi_model.load_all_models():
                    result["details"].append("✅ All models loaded successfully")

                    # Test prediction
                    test_features = {name: 0.0 for name in multi_model.short_term_model.feature_names}
                    scores = multi_model.predict_all_timeframes(test_features)

                    result["details"].append(f"✅ Test prediction: Short={scores['short_term_score']}, Medium={scores['medium_term_score']}, Long={scores['long_term_score']}")
                    result["status"] = "healthy"
                    self.successes.append("All ML models loaded and tested")
                else:
                    result["details"].append("⚠️ Some models failed to load")
                    result["status"] = "warning"
                    self.warnings.append("Model loading failed - retrain models")
            else:
                result["status"] = "error"
                self.issues.append("Run: python scripts/train_multiframe_models.py")

        except Exception as e:
            result["status"] = "error"
            result["details"].append(f"❌ Error: {e}")
            self.issues.append(f"ML model error: {e}")

        return result

    def check_api_keys(self) -> Dict:
        """API 키 설정 점검"""
        logger.info("\n[3/6] Checking API Keys...")
        result = {"status": "unknown", "details": []}

        api_keys = {
            "Polygon API": "POLYGON_API_KEY",
            "Alpha Vantage": "ALPHA_VANTAGE_API_KEY",
            "Anthropic Claude": "ANTHROPIC_API_KEY",
            "Finnhub": "FINNHUB_API_KEY",
            "Database": "DATABASE_URL",
        }

        all_set = True
        for name, env_var in api_keys.items():
            value = os.getenv(env_var)
            if value and value.strip():
                masked = value[:8] + "..." if len(value) > 8 else "***"
                result["details"].append(f"✅ {name}: SET ({masked})")
            else:
                result["details"].append(f"❌ {name}: NOT SET")
                all_set = False
                self.issues.append(f"Missing API key: {env_var}")

        if all_set:
            result["status"] = "healthy"
            self.successes.append("All API keys configured")
        else:
            result["status"] = "error"
            self.issues.append("Set missing API keys in .env file")

        return result

    def check_news_data(self) -> Dict:
        """뉴스 데이터 수집 상태 점검"""
        logger.info("\n[4/6] Checking News Data...")
        result = {"status": "unknown", "details": []}

        try:
            from web.app import app, db
            from web.database import NewsArticle

            with app.app_context():
                # Check recent news (last 24 hours)
                cutoff = datetime.utcnow() - timedelta(hours=24)
                recent_count = NewsArticle.query.filter(NewsArticle.published_at >= cutoff).count()

                total_count = db.session.query(NewsArticle).count()

                result["details"].append(f"📰 Total news articles: {total_count}")
                result["details"].append(f"📰 Last 24h: {recent_count} articles")

                if recent_count > 0:
                    result["details"].append("✅ News collection: ACTIVE")
                    result["status"] = "healthy"
                    self.successes.append("News collection working")
                else:
                    result["details"].append("⚠️ No news in last 24h")
                    result["status"] = "warning"
                    self.warnings.append("Check GitHub Actions: Data Refresh workflow")

                # Check sentiment distribution
                sentiment_counts = {}
                for sentiment in ["positive", "negative", "neutral"]:
                    count = NewsArticle.query.filter_by(sentiment=sentiment).count()
                    sentiment_counts[sentiment] = count

                result["details"].append(f"📊 Sentiment: Positive={sentiment_counts.get('positive', 0)}, Neutral={sentiment_counts.get('neutral', 0)}, Negative={sentiment_counts.get('negative', 0)}")

        except Exception as e:
            result["status"] = "error"
            result["details"].append(f"❌ Error: {e}")
            self.issues.append(f"News data error: {e}")

        return result

    def check_ai_scores(self) -> Dict:
        """AI Score 업데이트 상태 점검"""
        logger.info("\n[5/6] Checking AI Scores...")
        result = {"status": "unknown", "details": []}

        try:
            from web.app import app, db
            from web.database import AIScore

            with app.app_context():
                # Check total scores
                total_scores = db.session.query(AIScore).count()
                result["details"].append(f"📊 Total AI Scores: {total_scores} stocks")

                if total_scores == 0:
                    result["details"].append("❌ No AI scores in database")
                    result["status"] = "error"
                    self.issues.append("Run: python scripts/cron_update_ai_scores.py")
                    return result

                # Check multi-timeframe coverage
                with_short = AIScore.query.filter(AIScore.short_term_score.isnot(None)).count()
                with_long = AIScore.query.filter(AIScore.long_term_score.isnot(None)).count()

                result["details"].append(f"📊 With short-term scores: {with_short}/{total_scores}")
                result["details"].append(f"📊 With long-term scores: {with_long}/{total_scores}")

                coverage = min(with_short, with_long) / total_scores * 100 if total_scores > 0 else 0
                result["details"].append(f"📊 Multi-timeframe coverage: {coverage:.1f}%")

                # Check recent updates
                cutoff = datetime.utcnow() - timedelta(hours=48)
                recent_updates = AIScore.query.filter(AIScore.updated_at >= cutoff).count()

                result["details"].append(f"🔄 Updated last 48h: {recent_updates} stocks")

                if recent_updates > 0:
                    result["details"].append("✅ AI Score updates: ACTIVE")
                    result["status"] = "healthy"
                    self.successes.append("AI Scores being updated")
                else:
                    result["details"].append("⚠️ No updates in 48h")
                    result["status"] = "warning"
                    self.warnings.append("Check GitHub Actions: AI Score Update workflow")

                # Sample scores
                sample = AIScore.query.first()
                if sample and sample.short_term_score:
                    result["details"].append(f"📊 Sample ({sample.ticker}): Short={sample.short_term_score}, Medium={sample.score}, Long={sample.long_term_score}")

        except Exception as e:
            result["status"] = "error"
            result["details"].append(f"❌ Error: {e}")
            self.issues.append(f"AI Score error: {e}")

        return result

    def check_github_actions(self) -> Dict:
        """GitHub Actions 워크플로우 상태 점검"""
        logger.info("\n[6/6] Checking GitHub Actions...")
        result = {"status": "unknown", "details": []}

        workflow_files = {
            "AI Score Update": ".github/workflows/ai-score-update.yml",
            "Data Refresh": ".github/workflows/data-refresh.yml",
            "Backtest Processor": ".github/workflows/backtest-processor.yml",
        }

        all_exist = True
        for name, path in workflow_files.items():
            full_path = os.path.join(parent_dir, path)
            if os.path.exists(full_path):
                result["details"].append(f"✅ {name}: EXISTS")
            else:
                result["details"].append(f"❌ {name}: MISSING")
                all_exist = False
                self.issues.append(f"Missing workflow: {path}")

        if all_exist:
            result["status"] = "healthy"
            self.successes.append("All GitHub Actions workflows configured")
            result["details"].append("\n💡 Check workflow runs at: https://github.com/YOUR_USERNAME/YOUR_REPO/actions")
        else:
            result["status"] = "error"

        return result

    def print_summary(self, results: Dict):
        """점검 결과 요약 출력"""
        logger.info("\n" + "=" * 80)
        logger.info("HEALTH CHECK SUMMARY")
        logger.info("=" * 80)

        # Overall status
        all_healthy = all(r.get("status") == "healthy" for r in results.values())
        has_warnings = any(r.get("status") == "warning" for r in results.values())
        has_errors = any(r.get("status") == "error" for r in results.values())

        if all_healthy:
            logger.info("🎉 Overall Status: ALL SYSTEMS HEALTHY")
        elif has_errors:
            logger.info("❌ Overall Status: CRITICAL ISSUES FOUND")
        elif has_warnings:
            logger.info("⚠️ Overall Status: WARNINGS PRESENT")

        # Print each component
        for component, result in results.items():
            status_icon = "✅" if result["status"] == "healthy" else ("⚠️" if result["status"] == "warning" else "❌")
            logger.info(f"\n{status_icon} {component.upper()}: {result['status'].upper()}")
            for detail in result["details"]:
                logger.info(f"  {detail}")

        # Print action items
        if self.issues:
            logger.info("\n" + "=" * 80)
            logger.info("🚨 CRITICAL ISSUES TO FIX:")
            logger.info("=" * 80)
            for i, issue in enumerate(self.issues, 1):
                logger.info(f"{i}. {issue}")

        if self.warnings:
            logger.info("\n" + "=" * 80)
            logger.info("⚠️ WARNINGS:")
            logger.info("=" * 80)
            for i, warning in enumerate(self.warnings, 1):
                logger.info(f"{i}. {warning}")

        if self.successes:
            logger.info("\n" + "=" * 80)
            logger.info("✅ WORKING CORRECTLY:")
            logger.info("=" * 80)
            for i, success in enumerate(self.successes, 1):
                logger.info(f"{i}. {success}")

        logger.info("\n" + "=" * 80)


def main():
    """Run system health check"""
    checker = SystemHealthChecker()
    results = checker.check_all()

    # Exit with appropriate code
    has_errors = any(r.get("status") == "error" for r in results.values())
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
