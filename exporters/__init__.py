"""Export format handlers with factory pattern."""

from .base import BaseExporter, ExportResult

__all__ = ["BaseExporter", "ExportResult", "ExporterFactory"]


class ExporterFactory:
    """Factory for creating export format handlers (Registry pattern).

    Centralized registry for exporter implementations.
    Supports dynamic registration and instantiation of exporters.
    """

    _exporters: dict[str, type[BaseExporter]] = {}

    @classmethod
    def register(cls, format_name: str, exporter_class: type[BaseExporter]) -> None:
        """Register a new exporter class for a format.

        Args:
            format_name: Format identifier (e.g., 'json', 'csv')
            exporter_class: Exporter class (must inherit from BaseExporter)

        Raises:
            TypeError: If exporter_class doesn't inherit from BaseExporter
        """
        if not issubclass(exporter_class, BaseExporter):
            raise TypeError(
                f"{exporter_class.__name__} must inherit from BaseExporter"
            )
        cls._exporters[format_name.lower()] = exporter_class

    @classmethod
    def get_exporter(cls, format_name: str) -> BaseExporter:
        """Get an exporter instance for the given format.

        Args:
            format_name: Format identifier

        Returns:
            Initialized exporter instance

        Raises:
            ValueError: If format is not registered
        """
        exporter_class = cls._exporters.get(format_name.lower())
        if not exporter_class:
            supported = ", ".join(sorted(cls.supported_formats()))
            raise ValueError(
                f"Unknown export format: {format_name}. Supported: {supported}"
            )
        return exporter_class()

    @classmethod
    def supported_formats(cls) -> list[str]:
        """Get list of all registered formats.

        Returns:
            Sorted list of format names
        """
        return sorted(cls._exporters.keys())


# Auto-registration of built-in exporters (import at end to avoid circular imports)
from .csv_exporter import CsvExporter  # noqa: E402
from .json_exporter import JsonExporter  # noqa: E402
from .markdown_exporter import MarkdownExporter  # noqa: E402

ExporterFactory.register("json", JsonExporter)
ExporterFactory.register("csv", CsvExporter)
ExporterFactory.register("md", MarkdownExporter)
ExporterFactory.register("markdown", MarkdownExporter)
