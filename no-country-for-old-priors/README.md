# no-country-for-old-priors

A Python CLI tool that analyzes PACS, router, and archive logs to identify ad-hoc retrieve events during production hours and correlates them with DICOM study metadata using C-FIND only. This helps identify opportunities for prefetch optimization rules.

## Features

- **Log Parsing**: Recursively reads plain text and gzip-compressed log files
- **Event Extraction**: Extracts identifiers (AccessionNumber, StudyInstanceUID, PatientID, usernames, timestamps, IP addresses)
- **SQLite Storage**: Stores all parsed events and cached DICOM metadata in SQLite
- **DICOM C-FIND Queries**: Retrieves metadata from PACS using C-FIND only (no C-MOVE or C-GET)
- **Metadata Caching**: Avoids repeated PACS queries through intelligent caching
- **Business Hours Analysis**: Identifies which ad-hoc retrieves occur during configured business hours
- **Prior Study Analysis**: Correlates current studies with prior studies and calculates prior age
- **Comprehensive Reporting**: Generates CSV and HTML reports including:
  - `raw_events.csv` - All parsed log events
  - `study_metadata.csv` - DICOM study metadata
  - `adhoc_retrieves.csv` - Correlated ad-hoc retrieve events with prior studies
  - `prefetch_candidates.csv` - Recommended prefetch rules aggregated by modality and description
  - `summary_report.html` - Interactive HTML summary with statistics
- **Cache-Only Mode**: Analyze using only cached metadata without live PACS queries
- **Configurable Business Hours**: Set custom business hours (e.g., 07:00-17:00)
- **Query Throttling**: Throttle C-FIND queries to avoid overwhelming PACS

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd no-country-for-old-priors

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

## Usage

### 1. Parse Log Files

Extract events from PACS, router, and archive logs:

```bash
no-country-for-old-priors parse-logs \
  --log-directory /path/to/logs \
  --database ./analysis.db \
  --output-directory ./reports \
  --days 7
```

**Options:**
- `--log-directory`: Directory containing log files (recursively searched)
- `--database`: Path to SQLite database (created if doesn't exist)
- `--output-directory`: Directory for reports
- `--days`: Number of days to analyze (default: 7)
- `--verbose`: Enable debug logging

### 2. Query PACS and Cache Metadata

Retrieve DICOM metadata using C-FIND and cache results:

```bash
no-country-for-old-priors query-pacs \
  --database ./analysis.db \
  --pacs-host pacs.example.com \
  --pacs-port 11112 \
  --ae-title NCFOP \
  --called-ae-title PACS \
  --throttle-delay 0.1 \
  --include-patient-studies
```

**Options:**
- `--database`: Path to SQLite database
- `--pacs-host`: PACS server hostname (required)
- `--pacs-port`: PACS server port (default: 11112)
- `--ae-title`: Local AE title (default: NCFOP)
- `--called-ae-title`: PACS AE title (default: PACS)
- `--throttle-delay`: Delay between queries in seconds (default: 0.1)
- `--no-live-query`: Use only cached metadata (skip live queries)
- `--include-patient-studies`: Retrieve all studies for each patient
- `--verbose`: Enable debug logging

### 3. Analyze Events and Generate Reports

Analyze events and generate CSV and HTML reports:

```bash
no-country-for-old-priors analyze \
  --database ./analysis.db \
  --output-directory ./reports \
  --business-hours-start 07:00 \
  --business-hours-end 17:00 \
  --generate-html
```

**Options:**
- `--database`: Path to SQLite database
- `--output-directory`: Directory for reports
- `--business-hours-start`: Business hours start time in HH:MM format (default: 07:00)
- `--business-hours-end`: Business hours end time in HH:MM format (default: 17:00)
- `--generate-html`: Generate HTML summary report
- `--verbose`: Enable debug logging

### 4. Check Database Status

View statistics about the database:

```bash
no-country-for-old-priors status --database ./analysis.db
```

## Example Workflow

```bash
# Step 1: Parse logs from the last 14 days
no-country-for-old-priors parse-logs \
  --log-directory /var/log/pacs \
  --database ./pacs_analysis.db \
  --output-directory ./reports \
  --days 14

# Step 2: Check what we have so far
no-country-for-old-priors status --database ./pacs_analysis.db

# Step 3: Query PACS to cache metadata (if PACS is available)
no-country-for-old-priors query-pacs \
  --database ./pacs_analysis.db \
  --pacs-host 192.168.1.100 \
  --pacs-port 11112 \
  --include-patient-studies \
  --throttle-delay 0.2

# Step 4: Analyze and generate reports
no-country-for-old-priors analyze \
  --database ./pacs_analysis.db \
  --output-directory ./reports \
  --business-hours-start 08:00 \
  --business-hours-end 18:00 \
  --generate-html

# Step 5: Review the reports
# - reports/raw_events.csv
# - reports/study_metadata.csv
# - reports/adhoc_retrieves.csv
# - reports/prefetch_candidates.csv
# - reports/summary_report.html
```

## Cache-Only Analysis

If you don't have live access to PACS or want to work offline:

```bash
# First parse and cache metadata
no-country-for-old-priors query-pacs \
  --database ./pacs_analysis.db \
  --pacs-host pacs.example.com \
  --include-patient-studies

# Later, analyze without querying PACS again
no-country-for-old-priors analyze \
  --database ./pacs_analysis.db \
  --output-directory ./reports \
  --generate-html
```

## Log File Formats

The tool supports log files in the following formats:

- Plain text logs (`.log`, `.txt`)
- Gzip-compressed logs (`.log.gz`, `.txt.gz`)

### Required Information in Logs

The tool extracts the following information from logs:

- **Timestamps**: ISO 8601 or common log formats (automatically detected)
- **Identifiers**:
  - `AccessionNumber` or variations
  - `StudyInstanceUID` or variations
  - `PatientID` or variations
- **User Information**:
  - `username` or `user` fields
  - Workstation/IP addresses
- **Event Type Detection**:
  - "ad-hoc retrieve", "on-demand retrieve", etc.

### Example Log Lines

```
2024-04-19 14:23:45 [RETRIEVE] AccessionNumber=ACC123456 StudyInstanceUID=1.2.3.4.5 PatientID=PAT001 username=dr_smith workstation=WS001 IP=192.168.1.100 - ad-hoc retrieve requested

2024-04-19T14:25:30Z patient_id=PAT002 study_uid=1.2.3.4.6 accession_id=ACC123457 event=adhoc_retrieve username=tech_user
```

## Output Reports

### raw_events.csv
Contains all extracted log events with parsed identifiers.

**Columns:**
- event_timestamp
- log_file
- event_type
- accession_number, patient_id, study_instance_uid
- username, workstation, ip_address

### study_metadata.csv
DICOM study metadata retrieved from PACS.

**Columns:**
- study_instance_uid, patient_id, patient_name
- study_date, study_time
- study_description, modality
- accession_number
- referring_physician
- number_of_series, number_of_instances

### adhoc_retrieves.csv
Correlated ad-hoc retrieve events with prior studies.

**Columns:**
- event_timestamp
- current_study_uid, current_accession, current_modality, current_study_description
- prior_study_uid, prior_accession, prior_modality, prior_study_description
- prior_age_days, prior_age_months, prior_age_years
- is_business_hours, time_of_day
- username

### prefetch_candidates.csv
Recommended prefetch rules aggregated by modality and study description.

**Columns:**
- current_modality, current_study_description
- prior_modality, prior_study_description
- frequency (number of occurrences)
- avg_prior_age_days
- business_hours_percent

### summary_report.html
Interactive HTML report with:
- Summary statistics
- Business hours analysis
- Top users and modalities
- Prior study age distribution
- Recommended prefetch rules with frequency and timing

## Configuration

You can create a JSON configuration file for repeated analyses:

```json
{
  "log_directory": "/var/log/pacs",
  "database_path": "/data/analysis.db",
  "output_directory": "/data/reports",
  "days": 14,
  "business_hours": {
    "start_hour": 7,
    "start_minute": 0,
    "end_hour": 17,
    "end_minute": 0
  },
  "pacs_config": {
    "host": "pacs.example.com",
    "port": 11112,
    "ae_title": "NCFOP",
    "called_ae_title": "PACS",
    "timeout": 30
  },
  "throttle_delay": 0.1,
  "include_patient_study_list": true
}
```

## Architecture

### Components

- **log_parser.py**: Extracts events from log files
- **database.py**: SQLite schema and operations
- **dicom_query.py**: DICOM C-FIND queries using pydicom and pynetdicom
- **analysis.py**: Business hours and prior study analysis
- **reports.py**: CSV and HTML report generation
- **config.py**: Configuration management
- **cli.py**: Click-based command-line interface

### Database Schema

- `events`: Parsed log events
- `dicom_metadata`: Cached DICOM study metadata
- `adhoc_retrieves`: Analyzed ad-hoc retrieve correlations
- `patient_studies`: Patient study lists (if requested)

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests (if available)
pytest tests/

# Format code
black no_country_for_old_priors/

# Lint
flake8 no_country_for_old_priors/
```

## Requirements

- Python 3.8+
- click >= 8.1.0
- pydicom >= 2.4.0
- pandas >= 2.0.0
- jinja2 >= 3.1.0
- python-dateutil >= 2.8.0

For DICOM C-FIND queries, you'll also need:
- pynetdicom >= 1.4.0 (optional, required for live PACS queries)

## License

See LICENSE file.

## Support

For issues or questions, please refer to the project documentation or contact the development team.
