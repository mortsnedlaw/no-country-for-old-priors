"""DICOM C-FIND queries for no-country-for-old-priors"""

import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

try:
    from pydicom.dataset import Dataset
    from pydicom.sequence import Sequence
    from pydicom.uid import ImplicitVRLittleEndian
    import pynetdicom
    from pynetdicom import AE
    from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelFind
except ImportError:
    pydicom = None
    pynetdicom = None

logger = logging.getLogger(__name__)


class DicomQueryError(Exception):
    """Exception for DICOM query errors"""
    pass


class DicomQuerier:
    """Query PACS using DICOM C-FIND"""

    def __init__(
        self,
        pacs_host: str,
        pacs_port: int = 11112,
        ae_title: str = "NCFOP",
        called_ae_title: str = "PACS",
        timeout: int = 30,
        throttle_delay: float = 0.1,
    ):
        if pydicom is None or pynetdicom is None:
            raise ImportError("pydicom and pynetdicom are required for DICOM queries")

        self.pacs_host = pacs_host
        self.pacs_port = pacs_port
        self.ae_title = ae_title
        self.called_ae_title = called_ae_title
        self.timeout = timeout
        self.throttle_delay = throttle_delay
        self.last_query_time = 0.0

    def _throttle(self):
        """Throttle queries to avoid overwhelming PACS"""
        elapsed = time.time() - self.last_query_time
        if elapsed < self.throttle_delay:
            time.sleep(self.throttle_delay - elapsed)
        self.last_query_time = time.time()

    def query_study_by_uid(self, study_uid: str) -> Optional[Dict]:
        """Query study by Study Instance UID"""
        try:
            self._throttle()

            ae = AE()
            ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)

            assoc = ae.associate(
                self.pacs_host,
                self.pacs_port,
                ae_title=self.ae_title,
                remote_ae=self.called_ae_title,
            )

            if not assoc.is_established:
                raise DicomQueryError(f"Association failed: {assoc.association_rejected_reason}")

            ds = Dataset()
            ds.PatientName = ""
            ds.PatientID = ""
            ds.StudyInstanceUID = study_uid
            ds.StudyDate = ""
            ds.StudyTime = ""
            ds.StudyDescription = ""
            ds.Modality = ""
            ds.AccessionNumber = ""
            ds.ReferringPhysicianName = ""
            ds.StudyComments = ""
            ds.NumberOfStudyRelatedSeries = ""
            ds.NumberOfStudyRelatedInstances = ""

            responses = []
            for response in assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind):
                if response.status.is_success:
                    responses.append(response.dataset)

            assoc.release()

            if not responses:
                return None

            # Use first response
            result = responses[0]
            return {
                "study_instance_uid": str(result.get("StudyInstanceUID", "")),
                "patient_id": str(result.get("PatientID", "")),
                "patient_name": str(result.get("PatientName", "")),
                "study_date": str(result.get("StudyDate", "")),
                "study_time": str(result.get("StudyTime", "")),
                "study_description": str(result.get("StudyDescription", "")),
                "modality": str(result.get("Modality", "")),
                "accession_number": str(result.get("AccessionNumber", "")),
                "referring_physician": str(result.get("ReferringPhysicianName", "")),
                "study_comments": str(result.get("StudyComments", "")),
                "number_of_series": int(result.get("NumberOfStudyRelatedSeries", 0) or 0),
                "number_of_instances": int(result.get("NumberOfStudyRelatedInstances", 0) or 0),
            }

        except Exception as e:
            logger.error(f"Error querying study {study_uid}: {e}")
            raise DicomQueryError(f"Query failed: {e}")

    def query_patient_studies(self, patient_id: str) -> List[Dict]:
        """Query all studies for a patient"""
        try:
            self._throttle()

            ae = AE()
            ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)

            assoc = ae.associate(
                self.pacs_host,
                self.pacs_port,
                ae_title=self.ae_title,
                remote_ae=self.called_ae_title,
            )

            if not assoc.is_established:
                raise DicomQueryError(f"Association failed: {assoc.association_rejected_reason}")

            ds = Dataset()
            ds.PatientName = ""
            ds.PatientID = patient_id
            ds.StudyInstanceUID = ""
            ds.StudyDate = ""
            ds.StudyTime = ""
            ds.StudyDescription = ""
            ds.Modality = ""
            ds.AccessionNumber = ""
            ds.ReferringPhysicianName = ""
            ds.StudyComments = ""
            ds.NumberOfStudyRelatedSeries = ""
            ds.NumberOfStudyRelatedInstances = ""

            results = []
            for response in assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind):
                if response.status.is_success:
                    result = response.dataset
                    results.append({
                        "study_instance_uid": str(result.get("StudyInstanceUID", "")),
                        "patient_id": str(result.get("PatientID", "")),
                        "patient_name": str(result.get("PatientName", "")),
                        "study_date": str(result.get("StudyDate", "")),
                        "study_time": str(result.get("StudyTime", "")),
                        "study_description": str(result.get("StudyDescription", "")),
                        "modality": str(result.get("Modality", "")),
                        "accession_number": str(result.get("AccessionNumber", "")),
                        "referring_physician": str(result.get("ReferringPhysicianName", "")),
                        "study_comments": str(result.get("StudyComments", "")),
                        "number_of_series": int(result.get("NumberOfStudyRelatedSeries", 0) or 0),
                        "number_of_instances": int(result.get("NumberOfStudyRelatedInstances", 0) or 0),
                    })

            assoc.release()
            return results

        except Exception as e:
            logger.error(f"Error querying patient studies for {patient_id}: {e}")
            raise DicomQueryError(f"Query failed: {e}")

    def query_by_accession(self, accession_number: str) -> Optional[Dict]:
        """Query study by accession number"""
        try:
            self._throttle()

            ae = AE()
            ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)

            assoc = ae.associate(
                self.pacs_host,
                self.pacs_port,
                ae_title=self.ae_title,
                remote_ae=self.called_ae_title,
            )

            if not assoc.is_established:
                raise DicomQueryError(f"Association failed: {assoc.association_rejected_reason}")

            ds = Dataset()
            ds.PatientName = ""
            ds.PatientID = ""
            ds.StudyInstanceUID = ""
            ds.StudyDate = ""
            ds.StudyTime = ""
            ds.StudyDescription = ""
            ds.Modality = ""
            ds.AccessionNumber = accession_number
            ds.ReferringPhysicianName = ""
            ds.StudyComments = ""
            ds.NumberOfStudyRelatedSeries = ""
            ds.NumberOfStudyRelatedInstances = ""

            responses = []
            for response in assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind):
                if response.status.is_success:
                    responses.append(response.dataset)

            assoc.release()

            if not responses:
                return None

            result = responses[0]
            return {
                "study_instance_uid": str(result.get("StudyInstanceUID", "")),
                "patient_id": str(result.get("PatientID", "")),
                "patient_name": str(result.get("PatientName", "")),
                "study_date": str(result.get("StudyDate", "")),
                "study_time": str(result.get("StudyTime", "")),
                "study_description": str(result.get("StudyDescription", "")),
                "modality": str(result.get("Modality", "")),
                "accession_number": str(result.get("AccessionNumber", "")),
                "referring_physician": str(result.get("ReferringPhysicianName", "")),
                "study_comments": str(result.get("StudyComments", "")),
                "number_of_series": int(result.get("NumberOfStudyRelatedSeries", 0) or 0),
                "number_of_instances": int(result.get("NumberOfStudyRelatedInstances", 0) or 0),
            }

        except Exception as e:
            logger.error(f"Error querying by accession {accession_number}: {e}")
            raise DicomQueryError(f"Query failed: {e}")
