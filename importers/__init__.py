"""Import plugins for different data formats."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class BaseImporter(ABC):
    """Abstract base class for data importers."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Human-readable name of the import format."""
        pass

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Supported file extensions (without dots)."""
        pass

    @abstractmethod
    def import_networks(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Import networks from file content. Returns list of network data dicts."""
        pass

    @abstractmethod
    def import_hosts(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Import hosts from file content. Returns list of host data dicts."""
        pass

    @abstractmethod
    def validate_networks_data(
        self, data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate networks data. Returns (valid_data, error_messages)."""
        pass

    @abstractmethod
    def validate_hosts_data(
        self, data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate hosts data. Returns (valid_data, error_messages)."""
        pass


# Registry for available importers
_importers: Dict[str, BaseImporter] = {}


def register_importer(name: str, importer: BaseImporter) -> None:
    """Register an importer plugin."""
    _importers[name] = importer


def get_importer(name: str) -> BaseImporter:
    """Get an importer by name."""
    if name not in _importers:
        raise ValueError(f"Unknown importer: {name}")
    return _importers[name]


def get_available_importers() -> Dict[str, BaseImporter]:
    """Get all available importers."""
    return _importers.copy()


def detect_format_by_extension(filename: str) -> str:
    """Detect import format by file extension."""
    extension = filename.lower().split(".")[-1]

    for name, importer in _importers.items():
        if extension in importer.file_extensions:
            return name

    raise ValueError(f"Unsupported file extension: {extension}")
