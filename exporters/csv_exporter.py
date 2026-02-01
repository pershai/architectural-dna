"""CSV export format implementation."""

import csv
import json
import time
from pathlib import Path
from typing import Any

from .base import BaseExporter, ExportResult


class CsvExporter(BaseExporter):
    """CSV format exporter with automatic flattening.

    CRITICAL FEATURES:
    - Deterministic set handling (sorted for reproducible output)
    - Semicolon escaping in string lists
    - JSON encoding for complex nested types
    - UTF-8 BOM for Excel compatibility
    - Flexible delimiter support
    """

    def export(
        self,
        data: Any,
        output_path: str,
        **options
    ) -> ExportResult:
        """Export data to CSV file.

        Args:
            data: Data to export (list of dicts or single dict)
            output_path: Output file path
            **options: Format options:
                - delimiter: CSV delimiter (default: ',')
                - include_header: Write header row (default: True)

        Returns:
            ExportResult with export metrics
        """
        start_time = time.time()
        delimiter = options.get("delimiter", ",")
        include_header = options.get("include_header", True)

        try:
            # Prepare output path
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Flatten data
            if isinstance(data, dict):
                rows = [self._flatten_dict(data)]
            elif isinstance(data, list):
                rows = [self._flatten_dict(item) for item in data]
            else:
                duration = time.time() - start_time
                return ExportResult(
                    success=False,
                    output_path=output_path,
                    records_exported=0,
                    records_failed=0,
                    errors=[{"type": "ValueError", "error": "CSV export requires dict or list of dicts"}],
                    warnings=[],
                    duration_seconds=duration
                )

            if not rows:
                duration = time.time() - start_time
                return ExportResult(
                    success=True,
                    output_path=output_path,
                    records_exported=0,
                    records_failed=0,
                    errors=[],
                    warnings=["No data to export"],
                    duration_seconds=duration
                )

            # Get fieldnames from first row
            fieldnames = rows[0].keys()

            # Write CSV with UTF-8 BOM for Excel compatibility
            with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                if include_header:
                    writer.writeheader()
                writer.writerows(rows)

            duration = time.time() - start_time

            return ExportResult(
                success=True,
                output_path=str(output_file),
                records_exported=len(rows),
                records_failed=0,
                errors=[],
                warnings=[],
                duration_seconds=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            return ExportResult(
                success=False,
                output_path=output_path,
                records_exported=0,
                records_failed=0,
                errors=[{"type": type(e).__name__, "error": str(e)}],
                warnings=[],
                duration_seconds=duration
            )

    def _flatten_dict(self, d: dict, parent_key: str = "", sep: str = "_") -> dict:
        """Flatten nested dict with deterministic set/list handling.

        CRITICAL:
        - Sets are sorted for deterministic output (required for testing)
        - Semicolons in strings are escaped
        - Complex types are JSON-encoded
        - Nested dicts are recursively flattened

        Args:
            d: Dict to flatten
            parent_key: Parent key for nested fields
            sep: Separator for nested keys

        Returns:
            Flattened dict
        """
        items = []

        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                # Recursively flatten nested dicts
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, (list, set, tuple)):
                # Handle collections with deterministic ordering
                if isinstance(v, set):
                    # CRITICAL: Sort sets for deterministic output
                    v = sorted(v)

                # Check if all items are strings
                if all(isinstance(x, str) for x in v):
                    # Join strings with semicolon (escape semicolons in values)
                    items.append((new_key, "; ".join(
                        str(x).replace(";", "\\;") for x in v
                    )))
                else:
                    # Use JSON for complex types (preserves types on re-import)
                    items.append((new_key, json.dumps(list(v))))
            else:
                items.append((new_key, v))

        return dict(items)

    def supports_format(self, format_name: str) -> bool:
        """Check if this exporter handles CSV format."""
        return format_name.lower() == "csv"

    def get_file_extension(self) -> str:
        """Get CSV file extension."""
        return ".csv"

    def verify(self, output_path: str) -> tuple[bool, str]:
        """Verify exported CSV file is valid.

        Args:
            output_path: Path to CSV file

        Returns:
            (success, message): True if valid CSV
        """
        try:
            row_count = 0
            with open(output_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for _row in reader:
                    row_count += 1

            return True, f"Valid CSV with {row_count} data rows"

        except FileNotFoundError:
            return False, "File not found"
        except csv.Error as e:
            return False, f"Invalid CSV: {e}"
        except Exception as e:
            return False, f"Verification failed: {e}"
