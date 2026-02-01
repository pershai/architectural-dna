"""Base classes and contracts for export functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExportResult:
    """Detailed export operation result with error handling metrics."""

    success: bool
    """Whether export succeeded (no critical errors)."""

    output_path: str
    """Path where data was exported."""

    records_exported: int
    """Number of successfully exported records."""

    records_failed: int
    """Number of records that failed to export."""

    errors: list[dict]
    """List of errors: [{"index": 0, "type": "Pattern", "error": "msg"}, ...]"""

    warnings: list[str]
    """List of non-critical warnings."""

    duration_seconds: float
    """Export operation duration in seconds."""

    def __str__(self) -> str:
        """Human-readable result summary."""
        if self.success:
            msg = f"✓ Exported {self.records_exported} records to {self.output_path}"
            if self.records_failed > 0:
                msg += f" ({self.records_failed} failed)"
            if self.warnings:
                msg += f" with {len(self.warnings)} warnings"
            return msg
        else:
            return f"✗ Export failed: {len(self.errors)} errors"


class BaseExporter(ABC):
    """Abstract base class for all export format implementations.

    Strategy pattern: Each exporter encapsulates format-specific logic.
    Subclasses inherit from this ABC to ensure contract compliance.
    """

    @abstractmethod
    def export(self, data: Any, output_path: str, **options) -> ExportResult:
        """Export data to file in the specific format.

        Args:
            data: Data to export (Pattern, AuditResult, list, dict, etc.)
            output_path: Path to output file
            **options: Format-specific options (indent, include_metadata, etc.)

        Returns:
            ExportResult: Detailed result with metrics and error information
        """
        pass

    @abstractmethod
    def supports_format(self, format_name: str) -> bool:
        """Check if this exporter handles the given format.

        Args:
            format_name: Format name to check (e.g., 'json', 'csv')

        Returns:
            True if this exporter supports the format
        """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """Get the standard file extension for this format.

        Returns:
            File extension with dot (e.g., '.json', '.csv', '.md')
        """
        pass

    def verify(self, output_path: str) -> tuple[bool, str]:
        """Verify correctness of exported file.

        Default implementation only checks file existence.
        Subclasses can override for format-specific validation.

        Args:
            output_path: Path to exported file

        Returns:
            (success, message): True if file is valid
        """
        if Path(output_path).exists():
            return True, f"File exists ({Path(output_path).stat().st_size} bytes)"
        return False, "File not found"
