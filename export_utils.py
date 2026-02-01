"""Common utilities for file export operations (shared between audit and pattern exporters).

This module provides reusable utilities to prevent duplication between:
- Universal Pattern Export (exporters/ with BaseExporter)
- C# Audit Reporting (csharp_audit_reporter.py)

Key utilities:
- atomic_file_write() - Ensures data integrity (temp → rename)
- validate_io_path() - Permission and path validation
"""

import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WriteResult:
    """Result of a file write operation."""

    success: bool
    """Whether write succeeded."""

    duration_seconds: float
    """Operation duration in seconds."""

    error: str | None = None
    """Error message if write failed."""

    file_size: int = 0
    """Size of written file in bytes."""

    def __str__(self) -> str:
        """Human-readable result."""
        if self.success:
            return f"✓ Written {self.file_size} bytes in {self.duration_seconds:.2f}s"
        else:
            return f"✗ Failed: {self.error}"


def atomic_file_write(
    output_path: str,
    write_func: Callable[[Path], None],
    create_parents: bool = True
) -> WriteResult:
    """Atomic file write helper (temp → rename).

    Writes to a temporary file first, then atomically renames it to the target path.
    This prevents corruption if the write operation fails or is interrupted.

    **Usage example:**
    ```python
    def _write_json(temp_file: Path):
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    result = atomic_file_write("/path/to/file.json", _write_json)
    if result.success:
        print(f"File written: {result.file_size} bytes")
    else:
        print(f"Error: {result.error}")
    ```

    Args:
        output_path: Target file path where data will be written.
        write_func: Callable that performs the write. Receives Path to temp file.
                   Signature: (Path) -> None
        create_parents: If True, create parent directories if missing (default: True).

    Returns:
        WriteResult with success status, duration, and optional error message.

    Behavior:
        1. Creates parent directories if create_parents=True
        2. Tests writability by touching a test file
        3. Writes to temp file (.tmp suffix)
        4. Atomically renames temp file to target path
        5. Returns file size and duration metrics
        6. On failure, cleans up temp file and returns error
    """
    start_time = time.time()
    temp_file = None

    try:
        output_file = Path(output_path)

        # Create parent directories if needed
        if create_parents:
            output_file.parent.mkdir(parents=True, exist_ok=True)

        # Test writability before attempting write
        test_file = output_file.with_suffix(".tmp_test")
        try:
            test_file.touch()
            test_file.unlink()
        except PermissionError as e:
            duration = time.time() - start_time
            return WriteResult(
                success=False,
                duration_seconds=duration,
                error=f"Cannot write to {output_path}: {e}"
            )

        # Write to temp file first (atomic operation)
        temp_file = output_file.with_suffix(".tmp")
        write_func(temp_file)

        # Atomic rename (POSIX: atomic, Windows: nearly atomic)
        temp_file.replace(output_file)

        # Get file size and duration
        file_size = output_file.stat().st_size
        duration = time.time() - start_time

        return WriteResult(
            success=True,
            duration_seconds=duration,
            file_size=file_size
        )

    except Exception as e:
        # Clean up temp file on failure
        if temp_file and temp_file.exists():
            with suppress(OSError):
                temp_file.unlink()

        duration = time.time() - start_time
        return WriteResult(
            success=False,
            duration_seconds=duration,
            error=str(e)
        )


def validate_io_path(output_path: str) -> tuple[bool, str]:
    """Validate that output path is writable.

    Checks if the target path and parent directories are writable.
    Creates parent directories if they don't exist.

    Args:
        output_path: Path to validate.

    Returns:
        (valid: bool, error_message: str)
        - If valid: (True, "")
        - If invalid: (False, error_description)

    Example:
        ```python
        valid, error = validate_io_path("/path/to/file.json")
        if not valid:
            print(f"Cannot write: {error}")
        ```
    """
    try:
        path = Path(output_path)
        parent = path.parent

        # Create parent directories if they don't exist
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

        # Test writability with a temporary file
        test_file = parent / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            return False, f"Cannot write to {output_path}: {e}"

        return True, ""

    except Exception as e:
        return False, f"Unexpected error validating {output_path}: {e}"
