"""Export plugins for different data formats."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseExporter(ABC):
    """Abstract base class for data exporters."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Human-readable name of the export format."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension for exported files (without dot)."""
        pass

    @property
    @abstractmethod
    def mime_type(self) -> str:
        """MIME type for the exported format."""
        pass

    @abstractmethod
    def export_networks(self, networks: List[Any]) -> bytes:
        """Export networks data to format-specific bytes."""
        pass

    @abstractmethod
    def export_hosts(self, hosts: List[Any]) -> bytes:
        """Export hosts data to format-specific bytes."""
        pass


# Registry for available exporters
_exporters: Dict[str, BaseExporter] = {}


def register_exporter(name: str, exporter: BaseExporter) -> None:
    """Register an exporter plugin."""
    _exporters[name] = exporter


def get_exporter(name: str) -> BaseExporter:
    """Get an exporter by name."""
    if name not in _exporters:
        raise ValueError(f"Unknown exporter: {name}")
    return _exporters[name]


def get_available_exporters() -> Dict[str, BaseExporter]:
    """Get all available exporters."""
    return _exporters.copy()
