"""Example usage patterns for no-country-for-old-priors"""

# Example 1: Basic analysis pipeline
# ===================================

import subprocess
import sys

def basic_analysis():
    """Run a basic analysis pipeline"""
    
    # Step 1: Parse logs
    result = subprocess.run([
        sys.executable, "-m", "no_country_for_old_priors.cli", "parse-logs",
        "--log-directory", "/var/log/pacs",
        "--database", "./analysis.db",
        "--output-directory", "./reports",
        "--days", "7"
    ])
    
    if result.returncode != 0:
        print("Error parsing logs")
        return
    
    # Step 2: Query PACS (if available)
    try:
        result = subprocess.run([
            sys.executable, "-m", "no_country_for_old_priors.cli", "query-pacs",
            "--database", "./analysis.db",
            "--pacs-host", "pacs.example.com",
            "--include-patient-studies"
        ])
    except Exception as e:
        print(f"Warning: Could not query PACS: {e}")
    
    # Step 3: Generate reports
    result = subprocess.run([
        sys.executable, "-m", "no_country_for_old_priors.cli", "analyze",
        "--database", "./analysis.db",
        "--output-directory", "./reports",
        "--business-hours-start", "07:00",
        "--business-hours-end", "17:00",
        "--generate-html"
    ])
    
    if result.returncode == 0:
        print("✓ Analysis complete. Reports available in ./reports/")


# Example 2: Using the Python API directly
# ==========================================

from pathlib import Path
from no_country_for_old_priors.database import Database
from no_country_for_old_priors.log_parser import LogParser
from no_country_for_old_priors.analysis import TimeAnalyzer, EventAggregator
from no_country_for_old_priors.reports import ReportGenerator


def python_api_example():
    """Using the library API directly"""
    
    # Parse logs
    parser = LogParser(Path("/var/log/pacs"), days=7)
    events = list(parser.parse_all_files())
    print(f"Parsed {len(events)} events")
    
    # Store in database
    with Database(Path("./analysis.db")) as db:
        for event in events:
            db.insert_event(**event)
        
        # Retrieve events
        all_events = db.get_all_events()
        print(f"Stored {len(all_events)} events")
        
        # Analyze business hours
        time_analyzer = TimeAnalyzer(start_hour=7, end_hour=17)
        
        business_hour_count = sum(
            1 for e in all_events
            if time_analyzer.is_business_hours(e["event_timestamp"])
        )
        print(f"Events during business hours: {business_hour_count}")
        
        # Generate statistics
        user_stats = EventAggregator.aggregate_by_user(all_events)
        print(f"Top users: {sorted(user_stats.items(), key=lambda x: x[1], reverse=True)[:5]}")
        
        modality_stats = EventAggregator.aggregate_by_modality(all_events)
        print(f"Modality distribution: {modality_stats}")


# Example 3: Cache-only analysis (offline)
# ==========================================

def cache_only_analysis():
    """Analyze using only cached metadata"""
    
    # First, populate cache when PACS is available
    import subprocess
    subprocess.run([
        sys.executable, "-m", "no_country_for_old_priors.cli", "query-pacs",
        "--database", "./analysis_cached.db",
        "--pacs-host", "pacs.example.com",
        "--include-patient-studies"
    ])
    
    # Later, analyze without connecting to PACS
    subprocess.run([
        sys.executable, "-m", "no_country_for_old_priors.cli", "analyze",
        "--database", "./analysis_cached.db",
        "--output-directory", "./reports",
        "--generate-html"
    ])


# Example 4: Custom business hours analysis
# ===========================================

def custom_business_hours():
    """Analyze with custom business hours"""
    
    # Analyze with 6am-8pm business hours
    import subprocess
    subprocess.run([
        sys.executable, "-m", "no_country_for_old_priors.cli", "analyze",
        "--database", "./analysis.db",
        "--output-directory", "./reports",
        "--business-hours-start", "06:00",
        "--business-hours-end", "20:00",
        "--generate-html"
    ])


# Example 5: Programmatic prior study analysis
# =============================================

from no_country_for_old_priors.analysis import PriorAnalyzer
from datetime import datetime


def prior_age_analysis():
    """Calculate prior study ages"""
    
    # Example dates in DICOM format (YYYYMMDD)
    current_date = "20240419"
    prior_dates = [
        "20240418",  # 1 day
        "20240412",  # 7 days
        "20240319",  # 31 days
        "20230419",  # 1 year
    ]
    
    for prior_date in prior_dates:
        days, months, years = PriorAnalyzer.calculate_prior_age(current_date, prior_date)
        formatted = PriorAnalyzer.format_age(days, months, years)
        print(f"Prior date {prior_date}: {formatted}")


if __name__ == "__main__":
    print("Example 1: Basic Analysis Pipeline")
    print("=" * 50)
    # basic_analysis()
    
    print("\n\nExample 2: Python API")
    print("=" * 50)
    # python_api_example()
    
    print("\n\nExample 3: Prior Age Analysis")
    print("=" * 50)
    prior_age_analysis()
