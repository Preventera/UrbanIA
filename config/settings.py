"""
AX5 UrbanIA — Configuration centralisée
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Configuration de l'application"""

    # API
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_debug: bool = os.getenv("API_DEBUG", "true").lower() == "true"

    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    # FalkorDB
    falkordb_host: str = os.getenv("FALKORDB_HOST", "localhost")
    falkordb_port: int = int(os.getenv("FALKORDB_PORT", "6379"))
    falkordb_graph: str = os.getenv("FALKORDB_GRAPH", "AX5_UrbanIA_SafetyGraph")

    # PostGIS
    postgis_uri: str = os.getenv("POSTGIS_URI", "postgresql://urbania:urbania@localhost:5432/urbania_geo")

    # Données
    cnesst_data_dir: str = os.getenv("CNESST_DATA_DIR", "./data/cnesst")
    saaq_data_dir: str = os.getenv("SAAQ_DATA_DIR", "./data/saaq")

    # Alertes
    alert_threshold_orange: int = int(os.getenv("ALERT_THRESHOLD_ORANGE", "65"))
    alert_threshold_red: int = int(os.getenv("ALERT_THRESHOLD_RED", "85"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


def get_settings() -> Settings:
    return Settings()
