# Architecture and Design

## Overview

no-country-for-old-priors is a metadata-only PACS analysis tool that identifies ad-hoc retrieve patterns to improve prefetch rules. It follows a three-phase pipeline:

1. **Parse** - Extract events from log files
2. **Query** - Cache DICOM metadata from PACS using C-FIND
3. **Analyze** - Correlate events and generate reports

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Interface (cli.py)                   │
│              parse-logs | query-pacs | analyze              │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┬──────────────┐
        │                             │              │
        ▼                             ▼              ▼
┌───────────────┐            ┌────────────────┐  ┌──────────┐
│ LogParser     │            │ DicomQuerier   │  │ Analysis │
│ log_parser.py │            │ dicom_query.py │  │analysis. │
└───────┬───────┘            └────────┬───────┘  │   py    │
        │                             │          └──────────┘
        │    ┌────────────────────────┘
        │    │
        ▼    ▼
┌──────────────────────────────────────┐
│      Database (database.py)          │
│   SQLite Schema & Operations         │
│  ┌────────────────────────────────┐  │
│  │ events                         │  │
│  │ dicom_metadata                 │  │
│  │ adhoc_retrieves                │  │
│  │ patient_studies                │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│  ReportGenerator (reports.py)        │
│  CSV and HTML Output                 │
└──────────────────────────────────────┘
```

## Component Details

### 1. log_parser.py - Log File Parsing

**Purpose:** Extract structured data from unstructured log files

**Key Features:**
- Handles plain text and gzip-compressed files
- Recursive directory scanning
- Multiple timestamp format detection
- Regex-based identifier extraction

**Extraction Patterns:**
- `AccessionNumber` - DICOM accession
- `StudyInstanceUID` - DICOM study UID
- `PatientID` - Patient identifier
- `username` - User identifier
- IP addresses and workstations

**Event Detection:**
- Ad-hoc retrievals
- DICOM queries (C-FIND)
- DICOM moves (C-MOVE)
- DICOM gets (C-GET)
- Store operations (C-STORE)

**Output:** Iterator of event dictionaries

### 2. database.py - SQLite Management

**Schema:**

```sql
events
├── id (PK)
├── event_timestamp
├── log_file
├── event_type
├── accession_number, study_instance_uid
├── patient_id, username
├── workstation, ip_address
└── raw_data

dicom_metadata
├── id (PK)
├── study_instance_uid (UNIQUE)
├── patient_id, patient_name
├── study_date, study_time
├── study_description, modality
├── accession_number
├── referring_physician
├── number_of_series, number_of_instances
└── cached_at, cached_from

adhoc_retrieves
├── id (PK)
├── current_event_id (FK→events)
├── current_study_uid, current_accession
├── current_modality, current_study_description
├── prior_study_uid, prior_accession
├── prior_modality, prior_study_description
├── prior_age_days/months/years
├── is_business_hours, time_of_day
└── username

patient_studies
├── id (PK)
├── patient_id
├── study_instance_uid (UNIQUE+patient_id)
├── study_date, study_time
├── study_description, modality
└── cached_at
```

**Key Operations:**
- Insert/upsert events and metadata
- Query by study UID, accession, patient ID
- Retrieve aggregated statistics
- Handle conflicts gracefully

### 3. dicom_query.py - PACS Communication

**Purpose:** Query PACS server using DICOM C-FIND

**Supported Queries:**
- Query by Study Instance UID
- Query by Accession Number
- Query by Patient ID (all studies)

**Implementation:**
- Uses pydicom for DICOM dataset construction
- Uses pynetdicom for DICOM association
- Implements throttling to avoid PACS overload
- Error handling for failed queries

**Caching:**
- Results stored in SQLite to avoid repeated queries
- Tracks cache source ("C-FIND")
- Intelligent insert-or-replace logic

### 4. analysis.py - Event Analysis

**TimeAnalyzer:**
- Detects business hours from timestamps
- Supports configurable start/end times
- Handles timezone-aware parsing

**PriorAnalyzer:**
- Correlates current and prior studies
- Calculates age in days, months, years
- Parses DICOM dates (YYYYMMDD format)
- Formats age for display

**EventAggregator:**
- Aggregates by: user, modality, study description
- Calculates statistics
- Groups by time of day
- Analyzes business hours patterns

### 5. reports.py - Report Generation

**CSV Reports:**
- Uses Python's csv module
- Raw events, metadata, ad-hoc retrieves
- Prefetch candidates with aggregations

**HTML Report:**
- Jinja2 templating
- Responsive grid layout
- Summary statistics cards
- Interactive tables
- Prefetch recommendations

## Data Flow

### Parse Phase
```
Log File
   │
   ├─ Read lines (handle .gz)
   ├─ Parse timestamp
   ├─ Detect event type
   ├─ Extract identifiers (regex)
   │
   ▼
Event Dict
   │
   ▼
Database → events table
```

### Query Phase
```
Event in DB
   │
   ├─ Extract study_uid or accession
   │
   ▼
DICOM C-FIND to PACS
   │
   ├─ Create Association
   ├─ Send query
   ├─ Collect responses
   ├─ Close association
   │
   ▼
Metadata Dict
   │
   ▼
Database → dicom_metadata table
         → patient_studies table
```

### Analysis Phase
```
Events + Metadata from DB
   │
   ├─ Filter ad-hoc retrievals
   ├─ Check business hours
   ├─ Find patient's prior studies
   ├─ Calculate prior age
   ├─ Correlate metadata
   │
   ▼
Adhoc Retrieve Records
   │
   ├─ Store in DB → adhoc_retrieves
   ├─ Aggregate by modality/description
   ├─ Calculate statistics
   │
   ▼
CSV Reports + HTML Summary
```

## Design Decisions

### 1. SQLite Over Other Databases
- **Why:** No external database required, portable, sufficient for analysis scale
- **Trade-off:** Not ideal for extremely large datasets (100M+ events)

### 2. C-FIND Only (No C-MOVE/C-GET)
- **Why:** HIPAA compliance, metadata-only analysis, reduces PACS load
- **Trade-off:** Cannot retrieve actual image objects

### 3. Caching Strategy
- **Why:** Repeated queries expensive, PACS not always available
- **Trade-off:** Stale metadata if studies updated frequently

### 4. Regex for Log Parsing
- **Why:** Flexible, handles variable log formats
- **Trade-off:** Not as robust as structured logging

### 5. Throttling for C-FIND
- **Why:** Prevents PACS overload
- **Trade-off:** Analysis takes longer

## Extension Points

### Adding Custom Event Types
Edit `LogParser._detect_event_type()` to recognize new patterns.

### Adding Custom Analysis
Extend `EventAggregator` with new aggregation methods.

### Adding Custom Reports
Extend `ReportGenerator` with new report methods.

### Supporting New Log Formats
Add patterns to `LogParser.PATTERNS` dictionary.

## Performance Considerations

**Typical Analysis Times:**
- Parse 1000 log events: < 1 second
- Query 100 studies from PACS: 5-30 seconds (depends on throttle delay)
- Generate reports: < 5 seconds

**Database Size:**
- 10,000 events: ~5 MB
- 1,000 metadata entries: ~1 MB
- 10,000 adhoc_retrieves: ~3 MB

**Optimization Tips:**
- Use `--no-live-query` to skip PACS queries
- Increase `--throttle-delay` if PACS is slow
- Reduce `--days` parameter for faster parsing
- Run analysis in off-peak hours

## Error Handling

### Missing Dependencies
- Graceful fallback for pydicom/pynetdicom
- Uses cache-only mode if DICOM libraries unavailable

### Log Parsing Errors
- UTF-8 decoding errors handled gracefully
- Missing fields don't crash parsing
- Warnings logged for skipped entries

### Database Conflicts
- Duplicate events ignored silently
- Metadata upserted (replace on conflict)
- Referential integrity maintained

### PACS Query Failures
- Individual query failures don't stop analysis
- Failures logged with details
- Analysis continues with cached data

## Testing

Key areas to test:
- Log parsing with various formats
- Timestamp parsing edge cases
- DICOM metadata extraction
- Business hours calculation
- Prior age calculation
- Report generation

See `tests/` directory for test suite.
