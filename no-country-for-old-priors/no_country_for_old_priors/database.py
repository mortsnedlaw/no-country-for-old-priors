"""Database management for no-country-for-old-priors"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class Database:
    """SQLite database for storing events and DICOM metadata"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def connect(self):
        """Connect to database and initialize schema"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_schema()

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _init_schema(self):
        """Initialize database schema"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_timestamp TEXT NOT NULL,
                log_file TEXT NOT NULL,
                log_line TEXT,
                event_type TEXT,
                accession_number TEXT,
                patient_id TEXT,

                username TEXT,
                workstation TEXT,
                ip_address TEXT,
                raw_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_timestamp, log_file, log_line)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS dicom_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                study_instance_uid TEXT UNIQUE NOT NULL,
                patient_id TEXT,
                patient_name TEXT,
                study_date TEXT,
                study_time TEXT,
                study_description TEXT,
                modality TEXT,
                accession_number TEXT,
                referring_physician TEXT,
                study_comments TEXT,
                number_of_series INTEGER,
                number_of_instances INTEGER,
                cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
                cached_from TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS adhoc_retrieves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                current_event_id INTEGER NOT NULL,
                current_study_uid TEXT,
                current_accession TEXT,
                prior_study_uid TEXT,
                prior_accession TEXT,
                prior_age_days INTEGER,
                prior_age_months INTEGER,
                prior_age_years INTEGER,
                is_business_hours BOOLEAN,
                time_of_day TEXT,
                username TEXT,
                modality TEXT,
                prior_modality TEXT,
                study_description TEXT,
                prior_study_description TEXT,
                analysis_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(current_event_id) REFERENCES events(id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_studies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                study_instance_uid TEXT NOT NULL,
                study_date TEXT,
                study_time TEXT,
                study_description TEXT,
                modality TEXT,
                cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(patient_id, study_instance_uid)
            )
        """)

        self.conn.commit()

    def insert_event(
        self,
        event_timestamp: str,
        log_file: str,
        log_line: str,
        event_type: str = None,
        accession_number: str = None,
        patient_id: str = None,
        study_instance_uid: str = None,
        username: str = None,
        workstation: str = None,
        ip_address: str = None,
        raw_data: str = None,
    ) -> Optional[int]:
        """Insert a log event"""
        try:
            self.cursor.execute(
                """
                INSERT INTO events (
                    event_timestamp, log_file, log_line, event_type,
                    accession_number, patient_id,
                    study_instance_uid, username, workstation, ip_address, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_timestamp,
                    log_file,
                    log_line,
                    event_type,
                    accession_number,
                    patient_id,
                    study_instance_uid,
                    username,
                    workstation,
                    ip_address,
                    raw_data,
                ),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_event(self, event_id: int) -> Optional[Dict]:
        """Get event by ID"""
        self.cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_all_events(self) -> List[Dict]:
        """Get all events"""
        self.cursor.execute("SELECT * FROM events ORDER BY event_timestamp DESC")
        return [dict(row) for row in self.cursor.fetchall()]

    def insert_dicom_metadata(
        self,
        study_instance_uid: str,
        patient_id: str = None,
        patient_name: str = None,
        study_date: str = None,
        study_time: str = None,
        study_description: str = None,
        modality: str = None,
        accession_number: str = None,
        referring_physician: str = None,
        study_comments: str = None,
        number_of_series: int = None,
        number_of_instances: int = None,
        cached_from: str = None,
    ) -> bool:
        """Insert or update DICOM metadata"""
        try:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO dicom_metadata (
                    study_instance_uid, patient_id, patient_name,
                    study_date, study_time, study_description, modality,
                    accession_number, referring_physician, study_comments,
                    number_of_series, number_of_instances, cached_from
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    study_instance_uid,
                    patient_id,
                    patient_name,
                    study_date,
                    study_time,
                    study_description,
                    modality,
                    accession_number,
                    referring_physician,
                    study_comments,
                    number_of_series,
                    number_of_instances,
                    cached_from,
                ),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error inserting metadata: {e}")
            return False

    def get_dicom_metadata(self, study_instance_uid: str) -> Optional[Dict]:
        """Get DICOM metadata for a study"""
        self.cursor.execute(
            "SELECT * FROM dicom_metadata WHERE study_instance_uid = ?",
            (study_instance_uid,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def insert_patient_studies(
        self,
        patient_id: str,
        study_instance_uid: str,
        study_date: str = None,
        study_time: str = None,
        study_description: str = None,
        modality: str = None,
    ) -> bool:
        """Insert patient studies"""
        try:
            self.cursor.execute(
                """
                INSERT OR IGNORE INTO patient_studies (
                    patient_id, study_instance_uid, study_date, study_time,
                    study_description, modality
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (patient_id, study_instance_uid, study_date, study_time, study_description, modality),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error inserting patient studies: {e}")
            return False

    def get_patient_studies(self, patient_id: str) -> List[Dict]:
        """Get all studies for a patient"""
        self.cursor.execute(
            "SELECT * FROM patient_studies WHERE patient_id = ? ORDER BY study_date DESC",
            (patient_id,),
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def insert_adhoc_retrieve(
        self,
        current_event_id: int,
        current_study_uid: str = None,
        current_accession: str = None,
        prior_study_uid: str = None,
        prior_accession: str = None,
        prior_age_days: int = None,
        prior_age_months: int = None,
        prior_age_years: int = None,
        is_business_hours: bool = False,
        time_of_day: str = None,
        username: str = None,
        modality: str = None,
        prior_modality: str = None,
        study_description: str = None,
        prior_study_description: str = None,
    ) -> bool:
        """Insert ad-hoc retrieve analysis"""
        try:
            self.cursor.execute(
                """
                INSERT INTO adhoc_retrieves (
                    current_event_id, current_study_uid, current_accession,
                    prior_study_uid, prior_accession, prior_age_days,
                    prior_age_months, prior_age_years, is_business_hours,
                    time_of_day, username, modality, prior_modality,
                    study_description, prior_study_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    current_event_id,
                    current_study_uid,
                    current_accession,
                    prior_study_uid,
                    prior_accession,
                    prior_age_days,
                    prior_age_months,
                    prior_age_years,
                    is_business_hours,
                    time_of_day,
                    username,
                    modality,
                    prior_modality,
                    study_description,
                    prior_study_description,
                ),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error inserting adhoc retrieve: {e}")
            return False

    def get_all_adhoc_retrieves(self) -> List[Dict]:
        """Get all ad-hoc retrieve analyses"""
        self.cursor.execute(
            """
            SELECT ar.*, e.event_timestamp, e.username as event_username
            FROM adhoc_retrieves ar
            LEFT JOIN events e ON ar.current_event_id = e.id
            ORDER BY e.event_timestamp DESC
            """
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def count_events(self) -> int:
        """Count total events"""
        self.cursor.execute("SELECT COUNT(*) FROM events")
        return self.cursor.fetchone()[0]

    def count_metadata(self) -> int:
        """Count cached metadata entries"""
        self.cursor.execute("SELECT COUNT(*) FROM dicom_metadata")
        return self.cursor.fetchone()[0]

    def count_adhoc_retrieves(self) -> int:
        """Count ad-hoc retrieve analyses"""
        self.cursor.execute("SELECT COUNT(*) FROM adhoc_retrieves")
        return self.cursor.fetchone()[0]
