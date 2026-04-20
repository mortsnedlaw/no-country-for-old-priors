"""Analysis module for no-country-for-old-priors"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import calendar

logger = logging.getLogger(__name__)


class TimeAnalyzer:
    """Analyze business hours and time-based patterns"""

    def __init__(self, start_hour: int = 7, start_minute: int = 0, 
                 end_hour: int = 17, end_minute: int = 0):
        self.start_hour = start_hour
        self.start_minute = start_minute
        self.end_hour = end_hour
        self.end_minute = end_minute

    def is_business_hours(self, timestamp: str) -> bool:
        """Check if timestamp is within business hours"""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            time_of_day = dt.time()
            start_time = dt.replace(hour=self.start_hour, minute=self.start_minute, second=0, microsecond=0).time()
            end_time = dt.replace(hour=self.end_hour, minute=self.end_minute, second=0, microsecond=0).time()
            return start_time <= time_of_day <= end_time
        except Exception as e:
            logger.error(f"Error checking business hours for {timestamp}: {e}")
            return False

    def get_time_of_day(self, timestamp: str) -> str:
        """Get time of day as string"""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%H:%M:%S")
        except Exception as e:
            logger.error(f"Error extracting time from {timestamp}: {e}")
            return ""


class PriorAnalyzer:
    """Analyze prior studies and retrieve patterns"""

    @staticmethod
    def calculate_prior_age(study_date_str: str, prior_date_str: str) -> Tuple[int, int, int]:
        """Calculate age between current and prior study dates"""
        try:
            # Parse dates - handle various formats
            study_date = PriorAnalyzer._parse_date(study_date_str)
            prior_date = PriorAnalyzer._parse_date(prior_date_str)

            if not study_date or not prior_date:
                return None, None, None

            days_diff = (study_date - prior_date).days

            if days_diff < 0:
                return None, None, None

            months_diff = (study_date.year - prior_date.year) * 12 + (study_date.month - prior_date.month)
            years_diff = (study_date.year - prior_date.year)

            return days_diff, months_diff, years_diff
        except Exception as e:
            logger.error(f"Error calculating prior age: {e}")
            return None, None, None

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """Parse DICOM date format"""
        if not date_str:
            return None

        # DICOM format: YYYYMMDD
        if len(date_str) == 8 and date_str.isdigit():
            try:
                return datetime.strptime(date_str, "%Y%m%d")
            except ValueError:
                pass

        # Try ISO format
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass

        # Try common date formats
        for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"]:
            try:
                return datetime.strptime(date_str[:10], fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def format_age(days: int, months: int, years: int) -> str:
        """Format age for display"""
        if days is None:
            return "Unknown"
        if years > 0:
            return f"{years}y {months % 12}m {days % 30}d"
        if months > 0:
            return f"{months}m {days % 30}d"
        return f"{days}d"


class EventAggregator:
    """Aggregate and group events for reporting"""

    @staticmethod
    def aggregate_by_user(events: List[Dict]) -> Dict[str, int]:
        """Count retrieves by user"""
        counts = {}
        for event in events:
            username = event.get("username", "Unknown")
            if username:
                counts[username] = counts.get(username, 0) + 1
        return counts

    @staticmethod
    def aggregate_by_modality(events: List[Dict]) -> Dict[str, int]:
        """Count retrieves by modality"""
        counts = {}
        for event in events:
            modality = event.get("modality", "Unknown")
            if modality:
                counts[modality] = counts.get(modality, 0) + 1
        return counts

    @staticmethod
    def aggregate_by_study_description(events: List[Dict]) -> Dict[str, int]:
        """Count retrieves by study description"""
        counts = {}
        for event in events:
            study_desc = event.get("study_description", "Unknown")
            if study_desc:
                counts[study_desc] = counts.get(study_desc, 0) + 1
        return counts

    @staticmethod
    def aggregate_by_prior_modality(events: List[Dict]) -> Dict[str, int]:
        """Count retrieves by prior study modality"""
        counts = {}
        for event in events:
            modality = event.get("prior_modality", "Unknown")
            if modality:
                counts[modality] = counts.get(modality, 0) + 1
        return counts

    @staticmethod
    def aggregate_by_prior_description(events: List[Dict]) -> Dict[str, int]:
        """Count retrieves by prior study description"""
        counts = {}
        for event in events:
            desc = event.get("prior_study_description", "Unknown")
            if desc:
                counts[desc] = counts.get(desc, 0) + 1
        return counts

    @staticmethod
    def aggregate_by_time_of_day(events: List[Dict]) -> Dict[str, int]:
        """Count retrieves by hour of day"""
        counts = {}
        for event in events:
            time_str = event.get("time_of_day", "")
            if time_str:
                hour = time_str.split(":")[0]
                counts[f"{hour}:00"] = counts.get(f"{hour}:00", 0) + 1
        return counts

    @staticmethod
    def aggregate_by_prior_age(events: List[Dict]) -> Dict[str, int]:
        """Count retrieves by prior age ranges"""
        counts = {
            "0-7d": 0,
            "8-30d": 0,
            "31-90d": 0,
            "91-365d": 0,
            ">1y": 0,
        }

        for event in events:
            days = event.get("prior_age_days")
            if days is not None:
                if days <= 7:
                    counts["0-7d"] += 1
                elif days <= 30:
                    counts["8-30d"] += 1
                elif days <= 90:
                    counts["31-90d"] += 1
                elif days <= 365:
                    counts["91-365d"] += 1
                else:
                    counts[">1y"] += 1

        return counts

    @staticmethod
    def aggregate_by_user_modality(events: List[Dict]) -> Dict[str, Dict[str, int]]:
        """Count retrieves by user and modality"""
        counts = {}
        for event in events:
            username = event.get("username", "Unknown")
            modality = event.get("modality", "Unknown")
            if username and modality:
                if username not in counts:
                    counts[username] = {}
                counts[username][modality] = counts[username].get(modality, 0) + 1
        return counts

    @staticmethod
    def business_hours_stats(events: List[Dict]) -> Dict[str, int]:
        """Calculate business vs non-business hours stats"""
        return {
            "business_hours": sum(1 for e in events if e.get("is_business_hours")),
            "after_hours": sum(1 for e in events if not e.get("is_business_hours")),
            "total": len(events),
        }
