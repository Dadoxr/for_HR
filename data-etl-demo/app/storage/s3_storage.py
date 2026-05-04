import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract storage backend for ETL staging."""

    @abstractmethod
    def save(self, path: str, data: list[dict[str, Any]]) -> str:
        """Save data and return the storage path."""

    @abstractmethod
    def load(self, path: str) -> list[dict[str, Any]]:
        """Load the most recent data from the given path."""


class LocalStorage(StorageBackend):
    """Local filesystem storage for development and demo.

    In production, replace with S3Storage backed by boto3.
    """

    def __init__(self, base_dir: str = "data/staging") -> None:
        self.base_dir = Path(base_dir)

    def save(self, path: str, data: list[dict[str, Any]]) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_path = self.base_dir / path / f"{timestamp}.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, default=str, indent=2))
        logger.info("Saved %d records to %s", len(data), file_path)
        return str(file_path)

    def load(self, path: str) -> list[dict[str, Any]]:
        staging_dir = self.base_dir / path
        if not staging_dir.exists():
            logger.warning("Staging path %s does not exist", staging_dir)
            return []
        files = sorted(staging_dir.glob("*.json"))
        if not files:
            logger.warning("No files found in %s", staging_dir)
            return []
        latest = files[-1]
        logger.info("Loading data from %s", latest)
        return json.loads(latest.read_text())


# Alias for backward compatibility
S3Storage = LocalStorage
