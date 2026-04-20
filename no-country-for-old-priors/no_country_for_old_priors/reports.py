"""Report generation for no-country-for-old-priors"""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from jinja2 import Template

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate CSV and HTML reports"""

    def __init__(self, output_directory: Path):
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def write_csv(self, filename: str, data: List[Dict], headers: Optional[List[str]] = None):
        """Write data to CSV file"""
        if not data:
            logger.warning(f"No data to write to {filename}")
            return

        output_path = self.output_directory / filename
        try:
            if headers is None:
                headers = list(data[0].keys())

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for row in data:
                    writer.writerow({h: row.get(h, "") for h in headers})

            logger.info(f"Wrote {len(data)} rows to {filename}")
        except Exception as e:
            logger.error(f"Error writing CSV {filename}: {e}")

    def generate_raw_events_report(self, events: List[Dict]):
        """Generate raw events CSV"""
        headers = [
            "event_timestamp",
            "log_file",
            "event_type",
            "accession_number",
            "patient_id",
            "study_instance_uid",
            "username",
            "workstation",
            "ip_address",
        ]
        self.write_csv("raw_events.csv", events, headers)

    def generate_study_metadata_report(self, metadata: List[Dict]):
        """Generate study metadata CSV"""
        headers = [
            "study_instance_uid",
            "patient_id",
            "patient_name",
            "study_date",
            "study_time",
            "study_description",
            "modality",
            "accession_number",
            "referring_physician",
            "number_of_series",
            "number_of_instances",
        ]
        self.write_csv("study_metadata.csv", metadata, headers)

    def generate_adhoc_retrieves_report(self, retrieves: List[Dict]):
        """Generate ad-hoc retrieves CSV"""
        headers = [
            "event_timestamp",
            "current_study_uid",
            "current_accession",
            "current_modality",
            "current_study_description",
            "prior_study_uid",
            "prior_accession",
            "prior_modality",
            "prior_study_description",
            "prior_age_days",
            "prior_age_months",
            "prior_age_years",
            "is_business_hours",
            "time_of_day",
            "username",
        ]
        self.write_csv("adhoc_retrieves.csv", retrieves, headers)

    def generate_prefetch_candidates_report(self, candidates: List[Dict]):
        """Generate prefetch candidates CSV"""
        headers = [
            "current_modality",
            "current_study_description",
            "prior_modality",
            "prior_study_description",
            "frequency",
            "avg_prior_age_days",
            "business_hours_percent",
        ]
        self.write_csv("prefetch_candidates.csv", candidates, headers)

    def generate_html_summary(
        self,
        total_events: int,
        adhoc_retrieves: int,
        cached_metadata: int,
        business_hours_stats: Dict,
        user_stats: Dict,
        modality_stats: Dict,
        prior_age_stats: Dict,
        prefetch_rules: List[Dict],
    ):
        """Generate HTML summary report"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>PACS Ad-Hoc Retrieve Analysis Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
        }
        h2 {
            color: #0066cc;
            margin-top: 30px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-card.warning {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        .stat-card.success {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        .stat-card h3 {
            margin: 0;
            font-size: 14px;
            text-transform: uppercase;
            opacity: 0.9;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f0f0f0;
            font-weight: bold;
            color: #333;
        }
        tr:hover {
            background-color: #f9f9f9;
        }
        .timestamp {
            color: #666;
            font-size: 12px;
        }
        .recommendation {
            background-color: #e8f4f8;
            border-left: 4px solid #0066cc;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .recommendation strong {
            color: #0066cc;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>PACS Ad-Hoc Retrieve Analysis Report</h1>
        <p class="timestamp">Generated: {{ timestamp }}</p>

        <h2>Summary Statistics</h2>
        <div class="stats-grid">
            <div class="stat-card success">
                <h3>Total Events Parsed</h3>
                <div class="value">{{ total_events }}</div>
            </div>
            <div class="stat-card warning">
                <h3>Ad-Hoc Retrieves</h3>
                <div class="value">{{ adhoc_retrieves }}</div>
            </div>
            <div class="stat-card">
                <h3>Cached Metadata</h3>
                <div class="value">{{ cached_metadata }}</div>
            </div>
            <div class="stat-card success">
                <h3>Business Hours</h3>
                <div class="value">{{ business_hours_stats.business_hours }}</div>
            </div>
        </div>

        <h2>Business Hours Analysis</h2>
        <table>
            <tr>
                <th>Time Period</th>
                <th>Count</th>
                <th>Percentage</th>
            </tr>
            <tr>
                <td>During Business Hours</td>
                <td>{{ business_hours_stats.business_hours }}</td>
                <td>{{ "%.1f"|format(business_hours_stats.business_hours * 100 / business_hours_stats.total) }}%</td>
            </tr>
            <tr>
                <td>After Hours</td>
                <td>{{ business_hours_stats.after_hours }}</td>
                <td>{{ "%.1f"|format(business_hours_stats.after_hours * 100 / business_hours_stats.total) }}%</td>
            </tr>
        </table>

        <h2>Top Users by Ad-Hoc Retrieves</h2>
        <table>
            <tr>
                <th>Username</th>
                <th>Count</th>
            </tr>
            {% for user, count in user_stats.items()|sort(attribute='1', reverse=True)|list|first(10) %}
            <tr>
                <td>{{ user }}</td>
                <td>{{ count }}</td>
            </tr>
            {% endfor %}
        </table>

        <h2>Modality Distribution</h2>
        <table>
            <tr>
                <th>Modality</th>
                <th>Count</th>
            </tr>
            {% for modality, count in modality_stats.items()|sort(attribute='1', reverse=True) %}
            <tr>
                <td>{{ modality }}</td>
                <td>{{ count }}</td>
            </tr>
            {% endfor %}
        </table>

        <h2>Prior Study Age Distribution</h2>
        <table>
            <tr>
                <th>Age Range</th>
                <th>Count</th>
                <th>Percentage</th>
            </tr>
            {% for age_range, count in prior_age_stats.items() %}
            <tr>
                <td>{{ age_range }}</td>
                <td>{{ count }}</td>
                <td>{{ "%.1f"|format(count * 100 / adhoc_retrieves) }}%</td>
            </tr>
            {% endfor %}
        </table>

        <h2>Recommended Prefetch Rules</h2>
        {% if prefetch_rules %}
            {% for rule in prefetch_rules|first(10) %}
            <div class="recommendation">
                <strong>Rule:</strong> Prefetch {{ rule.prior_modality }} ({{ rule.prior_study_description }}) 
                when ordering {{ rule.current_modality }} ({{ rule.current_study_description }})<br>
                <strong>Frequency:</strong> {{ rule.frequency }} occurrences<br>
                <strong>Avg Prior Age:</strong> {{ rule.avg_prior_age_days }} days<br>
                <strong>Business Hours:</strong> {{ "%.1f"|format(rule.business_hours_percent) }}%
            </div>
            {% endfor %}
        {% else %}
            <p>No prefetch candidates identified.</p>
        {% endif %}

        <p style="margin-top: 40px; color: #666; font-size: 12px;">
            This report was automatically generated by no-country-for-old-priors.
            Use the accompanying CSV reports for detailed analysis.
        </p>
    </div>
</body>
</html>
        """

        # Sort and prepare prefetch rules for template
        sorted_prefetch_rules = sorted(prefetch_rules, key=lambda x: x.get("frequency", 0), reverse=True)

        template = Template(html_template)
        html_content = template.render(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_events=total_events,
            adhoc_retrieves=adhoc_retrieves,
            cached_metadata=cached_metadata,
            business_hours_stats=business_hours_stats,
            user_stats=user_stats,
            modality_stats=modality_stats,
            prior_age_stats=prior_age_stats,
            prefetch_rules=sorted_prefetch_rules,
        )

        output_path = self.output_directory / "summary_report.html"
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Wrote HTML summary report to {output_path}")
        except Exception as e:
            logger.error(f"Error writing HTML report: {e}")
