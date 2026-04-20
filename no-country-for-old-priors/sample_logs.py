"""Sample log files for testing"""

# Sample PACS log entry
PACS_LOG_SAMPLE = """
2024-04-19 14:23:45 [RETRIEVE] Event Type: AD-HOC RETRIEVE
2024-04-19 14:23:45   AccessionNumber: ACC-2024-041900123
2024-04-19 14:23:45   StudyInstanceUID: 1.2.826.0.1.3680043.8.498.123456789
2024-04-19 14:23:45   PatientID: PAT-2024-001
2024-04-19 14:23:45   StudyDate: 20240419
2024-04-19 14:23:45   StudyTime: 142345
2024-04-19 14:23:45   Modality: CT
2024-04-19 14:23:45   StudyDescription: CT CHEST WITHOUT CONTRAST
2024-04-19 14:23:45   Username: dr_smith
2024-04-19 14:23:45   Workstation: WS-RAD-001
2024-04-19 14:23:45   IP Address: 192.168.1.100
2024-04-19 14:23:45 Status: COMPLETED
"""

# Sample router log entry
ROUTER_LOG_SAMPLE = """
2024-04-19 14:24:12 [ROUTER] Message routing
2024-04-19 14:24:12   Source: PACS (192.168.1.50)
2024-04-19 14:24:12   Destination: Archive (192.168.1.60)
2024-04-19 14:24:12   Accession: ACC-2024-041900124
2024-04-19 14:24:12   User: radiologist@hospital.org
2024-04-19 14:24:12   Retrieve Event: AD-HOC
2024-04-19 14:24:12   Priority: HIGH
"""

# Sample archive log entry
ARCHIVE_LOG_SAMPLE = """
2024-04-19T14:25:30Z [ARCHIVE] Dynamic Retrieve Request
2024-04-19T14:25:30Z patient_id=PAT-2024-002
2024-04-19T14:25:30Z study_uid=1.2.826.0.1.3680043.8.498.987654321
2024-04-19T14:25:30Z accession_id=ACC-2024-041900125
2024-04-19T14:25:30Z event=adhoc_retrieve
2024-04-19T14:25:30Z username=tech_user
2024-04-19T14:25:30Z workstation=WS-READ-002
2024-04-19T14:25:30Z ip_addr=192.168.1.101
2024-04-19T14:25:30Z modality=MR
2024-04-19T14:25:30Z study_desc=MR BRAIN WITH AND WITHOUT CONTRAST
2024-04-19T14:25:30Z series_count=15
2024-04-19T14:25:30Z instances_count=450
2024-04-19T14:25:30Z timestamp=2024-04-19 14:25:30
"""


def create_sample_logs(log_directory):
    """Create sample log files for testing"""
    from pathlib import Path
    import gzip
    
    log_dir = Path(log_directory)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create plain text log
    pacs_log = log_dir / "pacs.log"
    with open(pacs_log, "w") as f:
        f.write(PACS_LOG_SAMPLE * 10)  # Repeat 10 times
    
    # Create gzipped log
    archive_log_gz = log_dir / "archive.log.gz"
    with gzip.open(archive_log_gz, "wt") as f:
        f.write(ARCHIVE_LOG_SAMPLE * 10)
    
    # Create router log
    router_log = log_dir / "router.log"
    with open(router_log, "w") as f:
        f.write(ROUTER_LOG_SAMPLE * 10)
    
    print(f"Created sample logs in {log_dir}")
    print(f"  - {pacs_log}")
    print(f"  - {router_log}")
    print(f"  - {archive_log_gz}")


if __name__ == "__main__":
    import sys
    log_dir = sys.argv[1] if len(sys.argv) > 1 else "./sample_logs"
    create_sample_logs(log_dir)
