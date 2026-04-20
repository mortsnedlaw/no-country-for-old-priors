# Quick Start Guide

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd no-country-for-old-priors
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Verify installation:**
   ```bash
   no-country-for-old-priors --help
   ```

## 5-Minute Tutorial

### Step 1: Create Sample Data (Optional)

To test with sample logs:

```bash
python sample_logs.py ./test_logs
```

This creates sample PACS, router, and archive logs in `./test_logs/`.

### Step 2: Parse Logs

```bash
no-country-for-old-priors parse-logs \
  --log-directory ./test_logs \
  --database ./analysis.db \
  --output-directory ./reports \
  --days 30
```

This:
- Scans `./test_logs/` for all `.log`, `.txt`, `.log.gz`, `.txt.gz` files
- Extracts events from the last 30 days
- Stores everything in `analysis.db`

Check progress:
```bash
no-country-for-old-priors status --database ./analysis.db
```

### Step 3: Query PACS (Optional)

If you have access to your PACS server:

```bash
no-country-for-old-priors query-pacs \
  --database ./analysis.db \
  --pacs-host your-pacs-server.local \
  --pacs-port 11112 \
  --include-patient-studies
```

This retrieves DICOM metadata using C-FIND and caches it in the database.

**Note:** If PACS is not available or you want to work offline, skip this step and proceed to analysis.

### Step 4: Generate Reports

```bash
no-country-for-old-priors analyze \
  --database ./analysis.db \
  --output-directory ./reports \
  --business-hours-start 08:00 \
  --business-hours-end 18:00 \
  --generate-html
```

This generates:
- `raw_events.csv` - All parsed events
- `study_metadata.csv` - DICOM metadata (if queried)
- `adhoc_retrieves.csv` - Ad-hoc retrieves with correlations
- `prefetch_candidates.csv` - Recommended prefetch rules
- `summary_report.html` - Interactive HTML report

### Step 5: Review Reports

Open `./reports/summary_report.html` in your browser to see:
- Summary statistics
- Business hours analysis
- Top users and modalities
- Prior study age distribution
- Recommended prefetch rules

## Real-World Workflow

### Scenario 1: Weekly Analysis

```bash
#!/bin/bash

# Weekly PACS analysis script
DB_FILE="/data/pacs_analysis.db"
LOG_DIR="/var/log/pacs"
OUTPUT_DIR="/data/reports/$(date +%Y%m%d)"

# Step 1: Parse last 7 days of logs
no-country-for-old-priors parse-logs \
  --log-directory "$LOG_DIR" \
  --database "$DB_FILE" \
  --output-directory "$OUTPUT_DIR" \
  --days 7

# Step 2: Update PACS metadata cache
no-country-for-old-priors query-pacs \
  --database "$DB_FILE" \
  --pacs-host pacs.hospital.local \
  --include-patient-studies \
  --throttle-delay 0.2

# Step 3: Generate analysis
no-country-for-old-priors analyze \
  --database "$DB_FILE" \
  --output-directory "$OUTPUT_DIR" \
  --business-hours-start 07:00 \
  --business-hours-end 19:00 \
  --generate-html

# Step 4: Email report
echo "PACS analysis complete" | mail -s "Weekly PACS Report" admin@hospital.local
```

### Scenario 2: Offline Analysis

When PACS is unavailable or you want to work with cached data:

```bash
# First session (when PACS is available):
no-country-for-old-priors query-pacs \
  --database ./analysis_cached.db \
  --pacs-host pacs.example.com \
  --include-patient-studies

# Later session (PACS down or offline analysis):
no-country-for-old-priors analyze \
  --database ./analysis_cached.db \
  --output-directory ./reports \
  --generate-html
```

### Scenario 3: Multiple Environments

Compare ad-hoc retrieves across different time periods:

```bash
# Create reports for different date ranges
for days in 7 14 30 60; do
  output="./reports_${days}days"
  mkdir -p "$output"
  
  no-country-for-old-priors parse-logs \
    --log-directory /var/log/pacs \
    --database "./analysis_${days}d.db" \
    --output-directory "$output" \
    --days "$days"
  
  no-country-for-old-priors query-pacs \
    --database "./analysis_${days}d.db" \
    --pacs-host pacs.local \
    --include-patient-studies
  
  no-country-for-old-priors analyze \
    --database "./analysis_${days}d.db" \
    --output-directory "$output" \
    --generate-html
done
```

## Interpreting Results

### prefetch_candidates.csv

This is the key output for improving prefetch rules. Each row represents a pattern:

| Column | Meaning |
|--------|---------|
| `current_modality` | Modality being ordered |
| `current_study_description` | Description of current study |
| `prior_modality` | Modality of prior study being retrieved |
| `prior_study_description` | Description of prior study |
| `frequency` | How often this pattern occurs |
| `avg_prior_age_days` | Average days between studies |
| `business_hours_percent` | % occurring during business hours |

**Example prefetch rule:**
- When CT CHEST FOLLOW-UP is ordered, radiologists ad-hoc retrieve prior CT CHEST ~73% of the time
- Prior studies are ~45 days old on average
- 82% of these retrievals happen during business hours
- **Recommendation:** Create a prefetch rule: "CT CHEST → prior CT CHEST (within 180 days)"

### adhoc_retrieves.csv

Detailed log of each ad-hoc retrieve event:
- Which study was being read
- Which prior study was retrieved
- How old the prior study was
- Who retrieved it
- When it happened

Use this for:
- Identifying frequent users
- Finding modality combinations
- Understanding retrieve patterns by time of day

### raw_events.csv

All extracted log events, useful for:
- Verifying log parsing accuracy
- Debugging extraction issues
- Building custom analyses

## Troubleshooting

### "No events found"
- Check that log directory exists and contains logs
- Verify logs are less than N days old (adjust `--days` parameter)
- Ensure log format matches expected patterns

### PACS query fails
- Verify PACS server hostname and port
- Check AE titles match your PACS configuration
- Try with `--throttle-delay` increased (e.g., 0.5)
- Review logs with `--verbose` flag

### HTML report doesn't display correctly
- Ensure you're opening it in a modern browser
- Check for JavaScript console errors
- Try regenerating with `--generate-html` flag

### Slow performance
- Reduce number of days analyzed
- Use `--no-live-query` to skip PACS queries
- Increase `--throttle-delay` if PACS is rate-limiting

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Check [examples.py](examples.py) for Python API usage
- Review [config.example.json](config.example.json) for configuration options
