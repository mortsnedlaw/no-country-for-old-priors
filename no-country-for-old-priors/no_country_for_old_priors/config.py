"""Configuration management for no-country-for-old-priors"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class BusinessHours:
    """Business hours configuration"""
    start_hour: int = 7
    start_minute: int = 0
    end_hour: int = 17
    end_minute: int = 0

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class PacsConfig:
    """PACS server configuration"""
    host: str
    port: int = 11112
    ae_title: str = "NCFOP"
    called_ae_title: str = "PACS"
    timeout: int = 30

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class Config:
    """Main configuration"""
    log_directory: Path
    database_path: Path
    output_directory: Path
    days: int = 7
    business_hours: BusinessHours = None
    pacs_config: Optional[PacsConfig] = None
    cache_only: bool = False
    throttle_delay: float = 0.1  # seconds between C-FIND queries
    include_patient_study_list: bool = False

    def __post_init__(self):
        if self.business_hours is None:
            self.business_hours = BusinessHours()
        self.log_directory = Path(self.log_directory)
        self.database_path = Path(self.database_path)
        self.output_directory = Path(self.output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def to_dict(self):
        data = asdict(self)
        data["log_directory"] = str(self.log_directory)
        data["database_path"] = str(self.database_path)
        data["output_directory"] = str(self.output_directory)
        data["business_hours"] = self.business_hours.to_dict()
        if self.pacs_config:
            data["pacs_config"] = self.pacs_config.to_dict()
        return data

    @classmethod
    def from_file(cls, config_file: Path) -> "Config":
        """Load configuration from JSON file"""
        with open(config_file, "r") as f:
            data = json.load(f)
        
        if "business_hours" in data and data["business_hours"]:
            data["business_hours"] = BusinessHours.from_dict(data["business_hours"])
        
        if "pacs_config" in data and data["pacs_config"]:
            data["pacs_config"] = PacsConfig.from_dict(data["pacs_config"])
        
        return cls(**data)

    def save_to_file(self, config_file: Path):
        """Save configuration to JSON file"""
        with open(config_file, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
