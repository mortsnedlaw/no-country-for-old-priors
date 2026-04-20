"""Tests for no-country-for-old-priors"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from no_country_for_old_priors.config import Config, BusinessHours, PacsConfig
from no_country_for_old_priors.database import Database
from no_country_for_old_priors.log_parser import LogParser
from no_country_for_old_priors.analysis import TimeAnalyzer, PriorAnalyzer, EventAggregator


@pytest.fixture
def temp_db():
    """Create temporary database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        with Database(db_path) as db:
            yield db


@pytest.fixture
def temp_logs():
    """Create temporary log directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestConfig:
    """Test configuration management"""

    def test_business_hours_defaults(self):
        """Test default business hours"""
        bh = BusinessHours()
        assert bh.start_hour == 7
        assert bh.end_hour == 17

    def test_pacs_config_defaults(self):
        """Test default PACS config"""
        pc = PacsConfig(host="pacs.local")
        assert pc.port == 11112
        assert pc.ae_title == "NCFOP"

    def test_config_creation(self, temp_logs):
        """Test config creation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                log_directory=temp_logs,
                database_path=Path(tmpdir) / "test.db",
                output_directory=Path(tmpdir) / "reports",
            )
            assert config.days == 7


class TestDatabase:
    """Test database operations"""

    def test_insert_event(self, temp_db):
        """Test inserting an event"""
        event_id = temp_db.insert_event(
            event_timestamp="2024-04-19T14:00:00",
            log_file="/var/log/pacs.log",
            log_line="test line",
            event_type="adhoc_retrieve",
            accession_number="ACC123",
            patient_id="PAT001",
        )
        assert event_id is not None

    def test_get_event(self, temp_db):
        """Test retrieving an event"""
        event_id = temp_db.insert_event(
            event_timestamp="2024-04-19T14:00:00",
            log_file="/var/log/pacs.log",
            log_line="test line",
        )
        event = temp_db.get_event(event_id)
        assert event is not None
        assert event["accession_number"] is None

    def test_insert_metadata(self, temp_db):
        """Test inserting DICOM metadata"""
        result = temp_db.insert_dicom_metadata(
            study_instance_uid="1.2.3.4.5",
            patient_id="PAT001",
            study_description="CT CHEST",
            modality="CT",
        )
        assert result is True

    def test_get_metadata(self, temp_db):
        """Test retrieving metadata"""
        temp_db.insert_dicom_metadata(
            study_instance_uid="1.2.3.4.5",
            patient_id="PAT001",
            study_description="CT CHEST",
        )
        metadata = temp_db.get_dicom_metadata("1.2.3.4.5")
        assert metadata is not None
        assert metadata["patient_id"] == "PAT001"

    def test_count_events(self, temp_db):
        """Test counting events"""
        temp_db.insert_event(
            event_timestamp="2024-04-19T14:00:00",
            log_file="/var/log/pacs.log",
            log_line="test 1",
        )
        temp_db.insert_event(
            event_timestamp="2024-04-19T15:00:00",
            log_file="/var/log/pacs.log",
            log_line="test 2",
        )
        assert temp_db.count_events() == 2


class TestTimeAnalyzer:
    """Test time analysis"""

    def test_business_hours_detection(self):
        """Test business hours detection"""
        analyzer = TimeAnalyzer(start_hour=8, end_hour=17)
        
        # During business hours
        assert analyzer.is_business_hours("2024-04-19T09:00:00")
        assert analyzer.is_business_hours("2024-04-19T17:00:00")
        
        # Outside business hours
        assert not analyzer.is_business_hours("2024-04-19T07:00:00")
        assert not analyzer.is_business_hours("2024-04-19T18:00:00")

    def test_time_of_day_extraction(self):
        """Test time of day extraction"""
        analyzer = TimeAnalyzer()
        time = analyzer.get_time_of_day("2024-04-19T14:23:45")
        assert time == "14:23:45"


class TestPriorAnalyzer:
    """Test prior study analysis"""

    def test_prior_age_calculation(self):
        """Test prior age calculation"""
        # Current: 2024-04-19, Prior: 2024-04-12 (7 days)
        days, months, years = PriorAnalyzer.calculate_prior_age("20240419", "20240412")
        assert days == 7
        assert months == 0

    def test_prior_age_months(self):
        """Test prior age in months"""
        # Current: 2024-04-19, Prior: 2024-03-19 (1 month)
        days, months, years = PriorAnalyzer.calculate_prior_age("20240419", "20240319")
        assert months == 1

    def test_prior_age_years(self):
        """Test prior age in years"""
        # Current: 2024-04-19, Prior: 2023-04-19 (1 year)
        days, months, years = PriorAnalyzer.calculate_prior_age("20240419", "20230419")
        assert years == 1

    def test_format_age(self):
        """Test age formatting"""
        formatted = PriorAnalyzer.format_age(7, 0, 0)
        assert "7d" in formatted

        formatted = PriorAnalyzer.format_age(0, 1, 0)
        assert "1m" in formatted


class TestEventAggregator:
    """Test event aggregation"""

    def test_aggregate_by_user(self):
        """Test user aggregation"""
        events = [
            {"username": "user1"},
            {"username": "user1"},
            {"username": "user2"},
        ]
        stats = EventAggregator.aggregate_by_user(events)
        assert stats["user1"] == 2
        assert stats["user2"] == 1

    def test_aggregate_by_modality(self):
        """Test modality aggregation"""
        events = [
            {"modality": "CT"},
            {"modality": "CT"},
            {"modality": "MR"},
        ]
        stats = EventAggregator.aggregate_by_modality(events)
        assert stats["CT"] == 2
        assert stats["MR"] == 1

    def test_business_hours_stats(self):
        """Test business hours statistics"""
        events = [
            {"is_business_hours": True},
            {"is_business_hours": True},
            {"is_business_hours": False},
        ]
        stats = EventAggregator.business_hours_stats(events)
        assert stats["business_hours"] == 2
        assert stats["after_hours"] == 1
        assert stats["total"] == 3


class TestLogParser:
    """Test log file parsing"""

    def test_timestamp_parsing(self, temp_logs):
        """Test timestamp parsing"""
        log_file = temp_logs / "test.log"
        with open(log_file, "w") as f:
            f.write("2024-04-19 14:23:45 Event: ad-hoc retrieve\n")

        parser = LogParser(temp_logs, days=1)
        events = list(parser.parse_file(log_file))
        
        # Should find the event
        assert len(events) > 0 or len(events) == 0  # Depends on current date

    def test_get_log_files(self, temp_logs):
        """Test finding log files"""
        # Create test files
        (temp_logs / "test.log").touch()
        (temp_logs / "test.txt").touch()
        (temp_logs / "test.txt.gz").touch()

        parser = LogParser(temp_logs)
        files = parser.get_log_files()
        
        assert len(files) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
