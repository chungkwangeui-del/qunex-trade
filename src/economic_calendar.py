"""
Economic Calendar - Track critical economic events
- Fed meetings (FOMC)
- Economic indicators (CPI, GDP, Unemployment, etc.)
- Earnings reports
- Automatically prioritize high-impact events
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from dotenv import load_dotenv

load_dotenv()


class EconomicCalendar:
    """Economic Calendar for tracking market-moving events"""

    def __init__(self):
        # FMP API (Free tier: 250 calls/day)
        self.fmp_api_key = os.getenv('FMP_API_KEY', '')

        # High-impact event keywords
        self.critical_events = [
            'FOMC', 'Federal Reserve', 'Fed Meeting', 'Interest Rate Decision',
            'Jerome Powell', 'Fed Chair', 'NFP', 'Nonfarm Payrolls',
            'CPI', 'Consumer Price Index', 'Inflation',
            'GDP', 'Gross Domestic Product',
            'Unemployment Rate', 'Jobs Report',
            'PCE', 'Personal Consumption',
            'Retail Sales', 'ISM Manufacturing',
            'Fed Minutes', 'FOMC Minutes', 'Fed Speech'
        ]

        self.high_impact_events = [
            'PPI', 'Producer Price Index',
            'Housing Starts', 'Building Permits',
            'Consumer Confidence', 'Consumer Sentiment',
            'Durable Goods', 'Trade Balance',
            'Industrial Production', 'Capacity Utilization',
            'Initial Claims', 'Continuing Claims'
        ]

    def get_economic_calendar(self, days_ahead: int = 30) -> List[Dict]:
        """
        Get upcoming economic events from FMP API
        """
        if not self.fmp_api_key:
            print("[WARNING] FMP_API_KEY not configured. Using fallback calendar.")
            return self._get_fallback_calendar()

        from_date = datetime.now().strftime('%Y-%m-%d')
        to_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

        url = f'https://financialmodelingprep.com/api/v3/economic_calendar'
        params = {
            'apikey': self.fmp_api_key,
            'from': from_date,
            'to': to_date
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            events = response.json()

            # Filter and prioritize US events
            us_events = [e for e in events if e.get('country') == 'US']

            # Add importance rating
            rated_events = []
            for event in us_events:
                event_with_rating = self._rate_event_importance(event)
                if event_with_rating['importance'] >= 3:  # Only show medium+ importance
                    rated_events.append(event_with_rating)

            # Sort by date and importance
            rated_events.sort(key=lambda x: (x['date'], -x['importance']))

            print(f"[Economic Calendar] Found {len(rated_events)} high-impact events")
            return rated_events

        except Exception as e:
            print(f"[ERROR] Failed to fetch economic calendar: {e}")
            return self._get_fallback_calendar()

    def _rate_event_importance(self, event: Dict) -> Dict:
        """
        Rate event importance (1-5 stars)
        """
        event_name = event.get('event', '').lower()
        impact = event.get('impact', '').lower()

        # Start with API's impact rating
        importance = 1
        if impact == 'high':
            importance = 3
        elif impact == 'medium':
            importance = 2

        # Override based on our critical keywords
        for keyword in self.critical_events:
            if keyword.lower() in event_name:
                importance = 5
                break

        # Check high-impact keywords if not already critical
        if importance < 5:
            for keyword in self.high_impact_events:
                if keyword.lower() in event_name:
                    importance = max(importance, 4)
                    break

        event['importance'] = importance
        event['emoji'] = self._get_event_emoji(event_name)
        event['category'] = self._categorize_event(event_name)

        return event

    def _get_event_emoji(self, event_name: str) -> str:
        """Get emoji based on event type"""
        event_lower = event_name.lower()

        if any(k in event_lower for k in ['fomc', 'fed', 'powell', 'interest rate']):
            return '🏦'
        elif any(k in event_lower for k in ['cpi', 'inflation', 'ppi']):
            return '📊'
        elif any(k in event_lower for k in ['gdp', 'economic growth']):
            return '📈'
        elif any(k in event_lower for k in ['unemployment', 'jobs', 'nonfarm', 'payroll']):
            return '👔'
        elif any(k in event_lower for k in ['retail', 'consumer', 'spending']):
            return '🛒'
        elif any(k in event_lower for k in ['housing', 'building']):
            return '🏠'
        elif any(k in event_lower for k in ['manufacturing', 'industrial']):
            return '🏭'
        else:
            return '📋'

    def _categorize_event(self, event_name: str) -> str:
        """Categorize event type"""
        event_lower = event_name.lower()

        if any(k in event_lower for k in ['fomc', 'fed meeting', 'powell']):
            return 'Fed Policy'
        elif any(k in event_lower for k in ['cpi', 'ppi', 'inflation']):
            return 'Inflation'
        elif 'gdp' in event_lower:
            return 'Growth'
        elif any(k in event_lower for k in ['employment', 'jobs', 'unemployment', 'payroll']):
            return 'Employment'
        elif any(k in event_lower for k in ['retail', 'consumer']):
            return 'Consumer'
        elif 'housing' in event_lower or 'building' in event_lower:
            return 'Housing'
        elif 'manufacturing' in event_lower or 'ism' in event_lower:
            return 'Manufacturing'
        else:
            return 'Other'

    def _get_fallback_calendar(self) -> List[Dict]:
        """
        Fallback calendar with known recurring events
        """
        today = datetime.now()
        events = []

        # CPI - typically 2nd week of month at 8:30 AM ET
        next_cpi = self._get_next_nth_weekday(today, 1, 2, 10)  # 2nd Tuesday
        events.append({
            'date': next_cpi.strftime('%Y-%m-%d'),
            'time': '08:30',
            'event': 'Consumer Price Index (CPI)',
            'country': 'US',
            'importance': 5,
            'emoji': '📊',
            'category': 'Inflation',
            'estimate': 'TBD',
            'previous': 'TBD'
        })

        # FOMC Meeting - 8 times per year (roughly every 6 weeks)
        fomc_dates = [
            '2025-11-06', '2025-12-17',  # Nov, Dec 2025
            '2026-01-28', '2026-03-18', '2026-05-06', '2026-06-17',  # 2026
            '2026-07-29', '2026-09-16', '2026-11-04', '2026-12-15'
        ]
        for fomc_date in fomc_dates:
            fomc_dt = datetime.strptime(fomc_date, '%Y-%m-%d')
            if fomc_dt > today and fomc_dt < today + timedelta(days=90):
                events.append({
                    'date': fomc_date,
                    'time': '14:00',
                    'event': 'FOMC Meeting - Interest Rate Decision',
                    'country': 'US',
                    'importance': 5,
                    'emoji': '🏦',
                    'category': 'Fed Policy',
                    'estimate': 'TBD',
                    'previous': 'TBD'
                })

        # Nonfarm Payrolls - First Friday of month at 8:30 AM ET
        next_nfp = self._get_next_nth_weekday(today, 4, 1, 1)  # 1st Friday
        events.append({
            'date': next_nfp.strftime('%Y-%m-%d'),
            'time': '08:30',
            'event': 'Nonfarm Payrolls (NFP)',
            'country': 'US',
            'importance': 5,
            'emoji': '👔',
            'category': 'Employment',
            'estimate': 'TBD',
            'previous': 'TBD'
        })

        # GDP - End of each quarter
        events.append({
            'date': '2025-10-30',
            'time': '08:30',
            'event': 'GDP (Q3 2025 Advance)',
            'country': 'US',
            'importance': 5,
            'emoji': '📈',
            'category': 'Growth',
            'estimate': 'TBD',
            'previous': 'TBD'
        })

        events.sort(key=lambda x: x['date'])
        return events

    def _get_next_nth_weekday(self, start_date: datetime, weekday: int, nth: int, month_offset: int = 0) -> datetime:
        """
        Get the nth occurrence of a weekday in a month
        weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
        nth: 1=first, 2=second, etc.
        """
        target_month = start_date.month + month_offset
        target_year = start_date.year

        if target_month > 12:
            target_year += target_month // 12
            target_month = target_month % 12

        # First day of target month
        first_day = datetime(target_year, target_month, 1)

        # Find first occurrence of weekday
        days_ahead = weekday - first_day.weekday()
        if days_ahead < 0:
            days_ahead += 7

        first_occurrence = first_day + timedelta(days=days_ahead)
        nth_occurrence = first_occurrence + timedelta(weeks=nth-1)

        return nth_occurrence

    def save_calendar(self, events: List[Dict], filepath: str = 'data/economic_calendar.json'):
        """Save calendar events to JSON"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)

        print(f"Calendar saved: {filepath} ({len(events)} events)")

    def get_events_by_importance(self, events: List[Dict], min_importance: int = 4) -> List[Dict]:
        """Filter events by importance level"""
        return [e for e in events if e.get('importance', 0) >= min_importance]

    def get_upcoming_week(self, events: List[Dict]) -> List[Dict]:
        """Get events in next 7 days"""
        today = datetime.now()
        week_later = today + timedelta(days=7)

        upcoming = []
        for event in events:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            if today <= event_date <= week_later:
                # Add days_until field
                days_until = (event_date - today).days
                event['days_until'] = days_until
                upcoming.append(event)

        return upcoming


if __name__ == '__main__':
    # Test
    calendar = EconomicCalendar()

    print("Fetching economic calendar...")
    events = calendar.get_economic_calendar(days_ahead=30)

    print(f"\nFound {len(events)} events")

    # Show critical events (5 stars)
    critical = calendar.get_events_by_importance(events, min_importance=5)
    print(f"\nCritical events (5 stars): {len(critical)}")
    for event in critical[:5]:
        print(f"  {event['date']} - {event['event'][:50]}")

    # Save calendar
    calendar.save_calendar(events)

    print("\nCalendar created successfully!")
