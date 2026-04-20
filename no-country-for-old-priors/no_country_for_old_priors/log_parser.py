"""Log file parsing for no-country-for-old-priors"""

import gzip
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Iterator, Optional
import logging

logger = logging.getLogger(__name__)


class LogParser:
    """Parse PACS, router and archive logs"""

    # Regex patterns for identifier extraction
    PATTERNS = {
        "accession": r"accession[_-]?(?:number|id)?[:\s]+([A-Za-z0-9\-\.]+)",
        "study_uid": r"(?:study[_-]?)?(?:instance[_-]?)?uid[:\s]+(\d+\.\d+(?:\.\d+)*)",
        "patient_id": r"patient[_-]?id[:\s]+([A-Za-z0-9\-\.]+)",
        "username": r"user(?:name)?[:\s]+([A-Za-z0-9\-_\.@]+)",
        "workstation": r"workstation[:\s]+([A-Za-z0-9\-_\.]+)",
        "ip_address": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        "adhoc_retrieve": r"(?:ad[_-]?hoc|on[_-]?demand|dynamic)[_-]?retrieve|retrieve[_-]?event",
    }

    # Common timestamp formats
    TIMESTAMP_FORMATS = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d-%b-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]

    def __init__(self, log_directory: Path, days: int = 7):
        self.log_directory = Path(log_directory)
        self.days = days
        self.cutoff_date = datetime.now() - timedelta(days=days)

    def get_log_files(self) -> List[Path]:
        """Get all log files from directory recursively"""
        log_files = []
        for pattern in ["*.log", "*.txt", "*.log.gz", "*.txt.gz"]:
            log_files.extend(self.log_directory.rglob(pattern))
        return sorted(log_files)

    def _read_file(self, file_path: Path) -> Iterator[str]:
        """Read lines from log file (handles both plain text and gzip)"""
        try:
            if file_path.suffix == ".gz":
                with gzip.open(file_path, "rt", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        yield line.rstrip("\n")
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        yield line.rstrip("\n")
        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")

    def _parse_timestamp(self, line: str) -> Optional[datetime]:
        """Extract and parse timestamp from log line"""
        # Try to find ISO format timestamp
        iso_match = re.search(r"(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})", line)
        if iso_match:
            try:
                return datetime.fromisoformat(iso_match.group(1).replace("T", " "))
            except ValueError:
                pass

        # Try other common formats
        for fmt in self.TIMESTAMP_FORMATS:
            match = re.search(
                r"(\d{1,2}[-/]\w+[-/]\d{2,4}\s+\d{1,2}:\d{2}:\d{2}|\d{4}[-/]\d{1,2}[-/]\d{1,2}[T\s]\d{1,2}:\d{2}:\d{2})",
                line,
            )
            if match:
                try:
                    return datetime.strptime(match.group(1), fmt)
                except ValueError:
                    continue
        return None

    def _extract_identifiers(self, line: str) -> Dict[str, Optional[str]]:
        """Extract identifiers from log line"""
        identifiers = {}

        # Extract accession
        match = re.search(self.PATTERNS["accession"], line, re.IGNORECASE)
        identifiers["accession_number"] = match.group(1) if match else None

        # Extract study UID
        match = re.search(self.PATTERNS["study_uid"], line, re.IGNORECASE)
        identifiers["study_instance_uid"] = match.group(1) if match else None

        # Extract patient ID
        match = re.search(self.PATTERNS["patient_id"], line, re.IGNORECASE)
        identifiers["patient_id"] = match.group(1) if match else None

        # Extract username
        match = re.search(self.PATTERNS["username"], line, re.IGNORECASE)
        identifiers["username"] = match.group(1) if match else None

        # Extract workstation
        match = re.search(self.PATTERNS["workstation"], line, re.IGNORECASE)
        identifiers["workstation"] = match.group(1) if match else None

        # Extract IP address
        match = re.search(self.PATTERNS["ip_address"], line)
        identifiers["ip_address"] = match.group(0) if match else None

        return identifiers

    def _detect_event_type(self, line: str) -> Optional[str]:
        """Detect event type from log line"""
        line_lower = line.lower()

        if re.search(self.PATTERNS["adhoc_retrieve"], line_lower):
            return "adhoc_retrieve"

        if "retrieve" in line_lower:
            return "retrieve"

        if "query" in line_lower or "c-find" in line_lower:
            return "query"

        if "move" in line_lower or "c-move" in line_lower:
            return "move"

        if "get" in line_lower or "c-get" in line_lower:
            return "get"

        if "store" in line_lower or "c-store" in line_lower:
            return "store"

        return None

    def parse_file(self, file_path: Path) -> Iterator[Dict]:
        """Parse a single log file and yield events"""
        logger.info(f"Parsing {file_path}")
        line_count = 0

        for line in self._read_file(file_path):
            line_count += 1
            if not line.strip():
                continue

            timestamp = self._parse_timestamp(line)
            if not timestamp:
                continue

            # Skip lines outside the date range
            if timestamp < self.cutoff_date:
                continue

            event_type = self._detect_event_type(line)
            if not event_type:
                continue

            identifiers = self._extract_identifiers(line)

            yield {
                "event_timestamp": timestamp.isoformat(),
                "log_file": str(file_path),
                "log_line": line,
                "event_type": event_type,
                "accession_number": identifiers.get("accession_number"),
                "patient_id": identifiers.get("patient_id"),
                "study_instance_uid": identifiers.get("study_instance_uid"),
                "username": identifiers.get("username"),
                "workstation": identifiers.get("workstation"),
                "ip_address": identifiers.get("ip_address"),
                "raw_data": line,
            }

    def parse_all_files(self) -> Iterator[Dict]:
        """Parse all log files in directory"""
        log_files = self.get_log_files()
        logger.info(f"Found {len(log_files)} log files")

        for log_file in log_files:
            yield from self.parse_file(log_file)
