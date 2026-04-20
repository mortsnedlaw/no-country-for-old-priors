"""Main CLI entry point for no-country-for-old-priors"""

import logging
import click
from pathlib import Path
from datetime import datetime

from no_country_for_old_priors.config import Config, PacsConfig, BusinessHours
from no_country_for_old_priors.database import Database
from no_country_for_old_priors.log_parser import LogParser
from no_country_for_old_priors.dicom_query import DicomQuerier, DicomQueryError
from no_country_for_old_priors.analysis import TimeAnalyzer, PriorAnalyzer, EventAggregator
from no_country_for_old_priors.reports import ReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
def main():
    """PACS ad-hoc retrieve event analyzer"""
    pass


@main.command()
@click.option("--log-directory", type=click.Path(exists=True), required=True, help="Directory containing log files")
@click.option("--database", type=click.Path(), required=True, help="SQLite database path")
@click.option("--output-directory", type=click.Path(), required=True, help="Output directory for reports")
@click.option("--days", type=int, default=7, help="Number of days to analyze")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
def parse_logs(log_directory, database, output_directory, days, verbose):
    """Parse log files and extract events"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = Config(
        log_directory=Path(log_directory),
        database_path=Path(database),
        output_directory=Path(output_directory),
        days=days,
    )

    try:
        with Database(config.database_path) as db:
            parser = LogParser(config.log_directory, days=config.days)

            total_events = 0
            for event in parser.parse_all_files():
                event_id = db.insert_event(**event)
                if event_id:
                    total_events += 1

            click.echo(f"✓ Parsed {total_events} events from logs")
            click.echo(f"✓ Database: {config.database_path}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option("--database", type=click.Path(exists=True), required=True, help="SQLite database path")
@click.option("--pacs-host", type=str, required=True, help="PACS server hostname")
@click.option("--pacs-port", type=int, default=11112, help="PACS server port")
@click.option("--ae-title", type=str, default="NCFOP", help="Local AE title")
@click.option("--called-ae-title", type=str, default="PACS", help="PACS AE title")
@click.option("--throttle-delay", type=float, default=0.1, help="Delay between queries (seconds)")
@click.option("--no-live-query", is_flag=True, help="Only use cached metadata")
@click.option("--include-patient-studies", is_flag=True, help="Retrieve all studies for patients")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
def query_pacs(database, pacs_host, pacs_port, ae_title, called_ae_title, throttle_delay, 
               no_live_query, include_patient_studies, verbose):
    """Query PACS and cache metadata"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        with Database(Path(database)) as db:
            queried_studies = set()
            queried_patients = set()
            failed_queries = 0
            cached_count = 0

            # Get all unique studies and patients from events
            events = db.get_all_events()
            click.echo(f"Found {len(events)} events to process")

            if not no_live_query:
                try:
                    querier = DicomQuerier(
                        pacs_host=pacs_host,
                        pacs_port=pacs_port,
                        ae_title=ae_title,
                        called_ae_title=called_ae_title,
                        throttle_delay=throttle_delay,
                    )
                except ImportError:
                    click.echo("⚠ pydicom/pynetdicom not installed. Using cache-only mode.", err=True)
                    no_live_query = True

            if not no_live_query:
                with click.progressbar(events, label="Querying PACS") as bar:
                    for event in bar:
                        # Query by study UID
                        if event.get("study_instance_uid") and event["study_instance_uid"] not in queried_studies:
                            try:
                                metadata = querier.query_study_by_uid(event["study_instance_uid"])
                                if metadata:
                                    db.insert_dicom_metadata(
                                        cached_from="C-FIND",
                                        **metadata,
                                    )
                                    cached_count += 1
                                queried_studies.add(event["study_instance_uid"])
                            except DicomQueryError as e:
                                logger.warning(f"Failed to query study {event['study_instance_uid']}: {e}")
                                failed_queries += 1

                        # Query by accession if study UID query failed
                        if (
                            not event.get("study_instance_uid")
                            and event.get("accession_number")
                            and event["accession_number"] not in queried_studies
                        ):
                            try:
                                metadata = querier.query_by_accession(event["accession_number"])
                                if metadata:
                                    db.insert_dicom_metadata(
                                        cached_from="C-FIND",
                                        **metadata,
                                    )
                                    cached_count += 1
                                queried_studies.add(event["accession_number"])
                            except DicomQueryError as e:
                                logger.warning(f"Failed to query accession {event['accession_number']}: {e}")
                                failed_queries += 1

                        # Query patient studies if requested
                        if (
                            include_patient_studies
                            and event.get("patient_id")
                            and event["patient_id"] not in queried_patients
                        ):
                            try:
                                patient_studies = querier.query_patient_studies(event["patient_id"])
                                for study in patient_studies:
                                    db.insert_patient_studies(
                                        patient_id=event["patient_id"],
                                        **{k: v for k, v in study.items() if k != "patient_id"},
                                    )
                                queried_patients.add(event["patient_id"])
                            except DicomQueryError as e:
                                logger.warning(f"Failed to query patient studies for {event['patient_id']}: {e}")

            click.echo(f"✓ Cached {cached_count} studies")
            if failed_queries > 0:
                click.echo(f"⚠ Failed queries: {failed_queries}")
            click.echo(f"✓ Database: {database}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option("--database", type=click.Path(exists=True), required=True, help="SQLite database path")
@click.option("--output-directory", type=click.Path(), required=True, help="Output directory for reports")
@click.option("--business-hours-start", type=str, default="07:00", help="Business hours start (HH:MM)")
@click.option("--business-hours-end", type=str, default="17:00", help="Business hours end (HH:MM)")
@click.option("--generate-html", is_flag=True, help="Generate HTML summary report")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
def analyze(database, output_directory, business_hours_start, business_hours_end, generate_html, verbose):
    """Analyze events and generate reports"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Parse business hours
        start_parts = business_hours_start.split(":")
        end_parts = business_hours_end.split(":")

        with Database(Path(database)) as db:
            # Get all events and metadata
            events = db.get_all_events()
            click.echo(f"Found {len(events)} events")

            # Initialize analyzers
            time_analyzer = TimeAnalyzer(
                start_hour=int(start_parts[0]),
                start_minute=int(start_parts[1]),
                end_hour=int(end_parts[0]),
                end_minute=int(end_parts[1]),
            )

            # Analyze ad-hoc retrieves
            adhoc_retrieves = []
            for event in events:
                if event.get("event_type") == "adhoc_retrieve":
                    is_business = time_analyzer.is_business_hours(event["event_timestamp"])
                    time_of_day = time_analyzer.get_time_of_day(event["event_timestamp"])

                    # Try to find prior studies for this patient
                    prior_studies = db.get_patient_studies(event.get("patient_id", "")) if event.get("patient_id") else []

                    for prior_study in prior_studies:
                        # Skip if it's the same study
                        if prior_study["study_instance_uid"] == event.get("study_instance_uid"):
                            continue

                        # Calculate prior age
                        current_date = event.get("study_date") or event.get("event_timestamp", "").split("T")[0]
                        prior_date = prior_study.get("study_date", "")

                        days, months, years = PriorAnalyzer.calculate_prior_age(current_date, prior_date)

                        # Get metadata for both studies
                        current_metadata = db.get_dicom_metadata(event.get("study_instance_uid", ""))
                        prior_metadata = db.get_dicom_metadata(prior_study["study_instance_uid"])

                        retrieve_record = {
                            "event_id": event["id"],
                            "event_timestamp": event["event_timestamp"],
                            "current_study_uid": event.get("study_instance_uid"),
                            "current_accession": event.get("accession_number"),
                            "prior_study_uid": prior_study["study_instance_uid"],
                            "prior_accession": prior_study.get("accession_number"),
                            "prior_age_days": days,
                            "prior_age_months": months,
                            "prior_age_years": years,
                            "is_business_hours": is_business,
                            "time_of_day": time_of_day,
                            "username": event.get("username"),
                            "modality": current_metadata.get("modality") if current_metadata else prior_study.get("modality"),
                            "prior_modality": prior_metadata.get("modality") if prior_metadata else prior_study.get("modality"),
                            "study_description": current_metadata.get("study_description") if current_metadata else "",
                            "prior_study_description": prior_metadata.get("study_description") if prior_metadata else prior_study.get("study_description"),
                        }

                        adhoc_retrieves.append(retrieve_record)
                        db.insert_adhoc_retrieve(**retrieve_record)

            click.echo(f"✓ Analyzed {len(adhoc_retrieves)} ad-hoc retrieve events")

            # Generate reports
            report_generator = ReportGenerator(Path(output_directory))

            # Raw events
            report_generator.generate_raw_events_report(events)

            # Study metadata
            cursor = db.cursor
            cursor.execute("SELECT * FROM dicom_metadata")
            metadata = [dict(row) for row in cursor.fetchall()]
            report_generator.generate_study_metadata_report(metadata)

            # Ad-hoc retrieves
            report_generator.generate_adhoc_retrieves_report(adhoc_retrieves)

            # Prefetch candidates - aggregate by current+prior modality/description
            prefetch_candidates = {}
            for retrieve in adhoc_retrieves:
                key = (
                    retrieve.get("modality"),
                    retrieve.get("study_description"),
                    retrieve.get("prior_modality"),
                    retrieve.get("prior_study_description"),
                )
                if key not in prefetch_candidates:
                    prefetch_candidates[key] = {
                        "current_modality": key[0],
                        "current_study_description": key[1],
                        "prior_modality": key[2],
                        "prior_study_description": key[3],
                        "frequency": 0,
                        "total_prior_age_days": 0,
                        "business_hours_count": 0,
                    }
                prefetch_candidates[key]["frequency"] += 1
                prefetch_candidates[key]["total_prior_age_days"] += retrieve.get("prior_age_days") or 0
                if retrieve.get("is_business_hours"):
                    prefetch_candidates[key]["business_hours_count"] += 1

            # Calculate averages and percentages
            prefetch_list = []
            for rule in prefetch_candidates.values():
                rule["avg_prior_age_days"] = int(rule["total_prior_age_days"] / rule["frequency"]) if rule["frequency"] > 0 else 0
                rule["business_hours_percent"] = (rule["business_hours_count"] / rule["frequency"]) * 100 if rule["frequency"] > 0 else 0
                prefetch_list.append(rule)

            report_generator.generate_prefetch_candidates_report(prefetch_list)

            # HTML summary if requested
            if generate_html:
                business_hours_stats = EventAggregator.business_hours_stats(adhoc_retrieves)
                user_stats = EventAggregator.aggregate_by_user(adhoc_retrieves)
                modality_stats = EventAggregator.aggregate_by_modality(adhoc_retrieves)
                prior_age_stats = EventAggregator.aggregate_by_prior_age(adhoc_retrieves)

                report_generator.generate_html_summary(
                    total_events=len(events),
                    adhoc_retrieves=len(adhoc_retrieves),
                    cached_metadata=len(metadata),
                    business_hours_stats=business_hours_stats,
                    user_stats=user_stats,
                    modality_stats=modality_stats,
                    prior_age_stats=prior_age_stats,
                    prefetch_rules=prefetch_list,
                )

            click.echo(f"✓ Reports written to {output_directory}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option("--database", type=click.Path(exists=True), required=True, help="SQLite database path")
def status(database):
    """Show database statistics"""
    try:
        with Database(Path(database)) as db:
            total_events = db.count_events()
            cached_metadata = db.count_metadata()
            adhoc_retrieves = db.count_adhoc_retrieves()

            click.echo(f"Database: {database}")
            click.echo(f"  Events: {total_events}")
            click.echo(f"  Cached Metadata: {cached_metadata}")
            click.echo(f"  Ad-Hoc Retrieves: {adhoc_retrieves}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
