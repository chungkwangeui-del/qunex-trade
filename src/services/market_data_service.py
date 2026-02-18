from datetime import datetime, timezone, timedelta
import os
import requests
import logging
from web.database import db, NewsArticle, EconomicEvent

logger = logging.getLogger(__name__)

class MarketDataService:
    @staticmethod
    def refresh_news(limit=50):
        """Collect fresh news from Polygon API and save to database"""
        try:
            from src.news_collector import NewsCollector
            from src.news_analyzer import NewsAnalyzer

            collector = NewsCollector()
            news_items = collector.collect_all_news(limit=limit)

            if not news_items:
                return {"success": False, "message": "No news collected from API"}

            # Initialize AI analyzer if key is present
            gemini_key = os.environ.get("GEMINI_API_KEY")
            analyzer = None
            analyzer_available = False
            analyzer_error = None

            if gemini_key:
                try:
                    analyzer = NewsAnalyzer()
                    analyzer_available = True
                except Exception as e:
                    analyzer_error = str(e)
                    logger.error(f"Failed to initialize NewsAnalyzer: {e}")
            else:
                analyzer_error = "GEMINI_API_KEY not set in environment"

            saved_count = 0
            analyzed_count = 0
            filtered_count = 0

            for item in news_items:
                try:
                    # Check if article already exists
                    existing = NewsArticle.query.filter_by(url=item["url"]).first()
                    if existing:
                        continue

                    # Parse published date
                    published_at = None
                    if item.get("published_at"):
                        try:
                            published_at = datetime.fromisoformat(
                                item["published_at"].replace("Z", "+00:00")
                            )
                        except Exception:
                            published_at = datetime.now(timezone.utc)
                    else:
                        published_at = datetime.now(timezone.utc)

                    # Run AI analysis when available
                    analysis = None
                    if analyzer_available and analyzer:
                        try:
                            analysis = analyzer.analyze_single_news(item)
                            if analysis:
                                analyzed_count += 1
                            else:
                                # News was filtered (importance < 4 or credibility < 3)
                                filtered_count += 1
                        except Exception as e:
                            logger.warning(
                                f"AI analysis failed for '{item.get('title', '')[:50]}': {e}"
                            )

                    # Set default analysis if not analyzed
                    if not analysis:
                        # Determine the reason for no analysis
                        if not analyzer_available:
                            reason = f"Gemini API error: {analyzer_error}"
                        else:
                            reason = "Filtered: Low importance or credibility"

                        analysis = {
                            "importance": 3,
                            "impact_summary": reason,
                            "sentiment": "neutral",
                        }

                    # Create new article
                    article = NewsArticle(
                        title=item["title"][:500],
                        description=(
                            item.get("description", "")[:2000]
                            if item.get("description")
                            else None
                        ),
                        url=item["url"][:1000],
                        source=item.get("source", "Unknown")[:100],
                        published_at=published_at,
                        ai_rating=analysis.get("importance", 3),
                        ai_analysis=analysis.get("impact_summary", ""),
                        sentiment=analysis.get("sentiment", "neutral"),
                    )
                    db.session.add(article)
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Error saving news article: {e}")
                    continue

            db.session.commit()
            logger.info(
                f"Saved {saved_count} new articles (AI analyzed: {analyzed_count}, filtered: {filtered_count})"
            )

            return {
                "success": True,
                "ai_status": {
                    "enabled": analyzer_available,
                    "analyzed": analyzed_count,
                    "filtered": filtered_count,
                    "error": analyzer_error,
                },
                "count": saved_count,
                "total_collected": len(news_items),
                "message": f"Collected {len(news_items)} articles, saved {saved_count} new",
            }

        except ImportError as e:
            logger.error(f"Import error: {e}")
            return {"success": False, "message": "News collector module not available"}
        except Exception as e:
            logger.error(f"Error refreshing news: {e}", exc_info=True)
            db.session.rollback()
            return {"success": False, "message": str(e)}

    @staticmethod
    def refresh_calendar():
        """Fetch real economic calendar data from Finnhub API"""
        try:
            finnhub_api_key = os.environ.get("FINNHUB_API_KEY")

            if not finnhub_api_key:
                logger.warning("FINNHUB_API_KEY not configured, using fallback data")
                return MarketDataService._refresh_calendar_fallback()

            # Fetch next 60 days of economic events from Finnhub
            today = datetime.now(timezone.utc).date()
            end_date = today + timedelta(days=60)

            url = "https://finnhub.io/api/v1/calendar/economic"
            params = {
                "from": today.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
                "token": finnhub_api_key,
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "economicCalendar" not in data:
                logger.error(f"Unexpected Finnhub response: {data}")
                return {"success": False, "message": "Invalid response from Finnhub"}

            events = data["economicCalendar"]
            saved_count = 0

            # Clear old events first
            EconomicEvent.query.filter(
                EconomicEvent.date
                >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
            ).delete()

            # Map Finnhub impact to our importance levels
            impact_map = {
                3: "high",  # High impact
                2: "medium",  # Medium impact
                1: "low",  # Low impact
            }

            for event_data in events:
                # Filter for US events (USD) - most relevant for stock traders
                country = event_data.get("country", "")
                if country != "US":
                    continue

                event_date_str = event_data.get("date", "")
                if not event_date_str:
                    continue

                try:
                    event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
                    event_date = event_date.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

                # Get impact level (1-3)
                impact = event_data.get("impact", 1)
                importance = impact_map.get(impact, "low")

                # Get actual/estimate/previous values
                actual = event_data.get("actual", "")
                estimate = event_data.get("estimate", "")
                prev = event_data.get("prev", "")

                event = EconomicEvent(
                    title=event_data.get("event", "Unknown Event"),
                    description=f"{event_data.get('event', '')} - {country}",
                    date=event_date,
                    time=event_data.get("time", "TBD"),
                    country="USD",
                    importance=importance,
                    forecast=str(estimate) if estimate else "TBD",
                    previous=str(prev) if prev else "TBD",
                    source="Finnhub",
                )
                db.session.add(event)
                saved_count += 1

            db.session.commit()
            logger.info(f"Fetched {saved_count} US economic events from Finnhub")

            return {
                "success": True,
                "count": saved_count,
                "message": f"Added {saved_count} US economic events from Finnhub",
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Finnhub API request failed: {e}")
            return {"success": False, "message": f"API request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Error refreshing calendar: {e}", exc_info=True)
            db.session.rollback()
            return {"success": False, "message": str(e)}

    @staticmethod
    def _refresh_calendar_fallback():
        """Fallback: Generate placeholder events when Finnhub API is not available"""
        try:
            event_templates = [
                {
                    "title": "FOMC Meeting Minutes",
                    "importance": "high",
                    "time": "2:00 PM EST",
                },
                {"title": "Non-Farm Payrolls", "importance": "high", "time": "8:30 AM EST"},
                {
                    "title": "CPI (Consumer Price Index)",
                    "importance": "high",
                    "time": "8:30 AM EST",
                },
                {
                    "title": "PPI (Producer Price Index)",
                    "importance": "medium",
                    "time": "8:30 AM EST",
                },
                {"title": "Retail Sales", "importance": "medium", "time": "8:30 AM EST"},
                {"title": "GDP (Quarterly)", "importance": "high", "time": "8:30 AM EST"},
                {"title": "Jobless Claims", "importance": "medium", "time": "8:30 AM EST"},
                {
                    "title": "ISM Manufacturing PMI",
                    "importance": "medium",
                    "time": "10:00 AM EST",
                },
            ]

            today = datetime.now(timezone.utc).date()
            saved_count = 0

            for i in range(60):
                event_date = today + timedelta(days=i)
                if event_date.weekday() >= 5:
                    continue

                template = event_templates[i % len(event_templates)]

                existing = EconomicEvent.query.filter_by(
                    title=template["title"],
                    date=datetime.combine(event_date, datetime.min.time()).replace(
                        tzinfo=timezone.utc
                    ),
                ).first()

                if existing:
                    continue

                event = EconomicEvent(
                    title=template["title"],
                    description=f"US Economic Indicator: {template['title']} (Placeholder)",
                    date=datetime.combine(event_date, datetime.min.time()).replace(
                        tzinfo=timezone.utc
                    ),
                    time=template["time"],
                    country="USD",
                    importance=template["importance"],
                    forecast="TBD",
                    previous="TBD",
                    source="Placeholder",
                )
                db.session.add(event)
                saved_count += 1

            db.session.commit()
            return {
                "success": True,
                "count": saved_count,
                "message": f"Added {saved_count} placeholder events (Configure FINNHUB_API_KEY for real data)",
            }

        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": str(e)}
