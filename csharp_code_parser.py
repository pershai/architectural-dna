"""Shared C# code parsing utilities."""

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BraceFindMode(Enum):
    """Mode for brace-finding algorithm."""

    IMMEDIATE = "immediate"  # Start counting braces immediately
    WAIT_FOR_OPENING = "wait_for_opening"  # Wait for first { before counting


@dataclass
class BraceFindResult:
    """Result of brace-finding operation."""

    end_position: int
    success: bool
    reason: str | None = None


class CSharpCodeParser:
    """Shared C# code parsing utilities.

    Provides unified brace-finding logic that works with both
    line-based and string-based code representations.
    """

    @staticmethod
    def find_block_end(
        content: str | list[str],
        start: int,
        mode: BraceFindMode = BraceFindMode.IMMEDIATE,
        max_iterations: int = 500_000,
    ) -> BraceFindResult:
        """
        Find the end of a brace-delimited block in C# code.

        This method handles:
        - Single-line comments (//)
        - Multi-line comments (/* */)
        - String literals ("..." and @"...")
        - Character literals ('...')
        - Nested braces

        Args:
            content: Source code as string or list of lines
            start: Starting position (char index for string, line number for list)
            mode: When to start counting braces:
                  - IMMEDIATE: Start counting from first brace encountered
                  - WAIT_FOR_OPENING: Wait for opening brace before counting
            max_iterations: Safety limit to prevent infinite loops (default: 500K)

        Returns:
            BraceFindResult with end position and success status
        """
        # Normalize input to string for unified processing
        is_line_based = isinstance(content, list)
        if is_line_based:
            # Convert lines to string, track line boundaries
            line_boundaries = [0]
            current_pos = 0
            for line in content:
                current_pos += len(line) + 1  # +1 for newline
                line_boundaries.append(current_pos)

            content_str = "\n".join(content)
            # Convert line number to character position
            start_pos = line_boundaries[start] if start < len(line_boundaries) else 0
        else:
            content_str = content
            start_pos = start
            line_boundaries = None

        # State machine for brace counting
        brace_count = 0
        counting_started = mode == BraceFindMode.IMMEDIATE
        i = start_pos
        iterations = 0
        length = len(content_str)

        while i < length and iterations < max_iterations:
            iterations += 1

            # Get current and next character
            char = content_str[i]
            next_char = content_str[i + 1] if i + 1 < length else ""

            # Skip single-line comments
            if char == "/" and next_char == "/":
                while i < length and content_str[i] != "\n":
                    i += 1
                continue

            # Skip multi-line comments
            if char == "/" and next_char == "*":
                i += 2
                while i < length - 1:
                    if content_str[i : i + 2] == "*/":
                        i += 2
                        break
                    i += 1
                continue

            # Skip string literals (regular and verbatim)
            if char == '"':
                # Check for verbatim string @"..."
                is_verbatim = i > 0 and content_str[i - 1] == "@"
                i += 1
                while i < length:
                    if content_str[i] == '"':
                        # Verbatim string: "" is escape for "
                        if (
                            is_verbatim
                            and i < length - 1
                            and content_str[i + 1] == '"'
                        ):
                            i += 2
                            continue
                        # Regular string: \" is escape
                        if not is_verbatim and i > 0 and content_str[i - 1] == "\\":
                            i += 1
                            continue
                        i += 1
                        break
                    i += 1
                continue

            # Skip char literals
            if char == "'":
                i += 1
                while i < length:
                    if content_str[i] == "'" and (
                        i == 0 or content_str[i - 1] != "\\"
                    ):
                        i += 1
                        break
                    i += 1
                continue

            # Count braces
            if char == "{":
                if mode == BraceFindMode.WAIT_FOR_OPENING:
                    counting_started = True
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if counting_started and brace_count == 0:
                    # Convert back to line number if needed
                    if is_line_based and line_boundaries:
                        # Find which line this position is on
                        for line_num, boundary in enumerate(line_boundaries):
                            if i < boundary:
                                return BraceFindResult(
                                    end_position=line_num - 1, success=True
                                )
                    else:
                        return BraceFindResult(end_position=i + 1, success=True)

            i += 1

        # Failed to find closing brace
        if iterations >= max_iterations:
            fallback = (
                len(content) - 1 if is_line_based else min(start_pos + 5000, length)
            )
            return BraceFindResult(
                end_position=fallback,
                success=False,
                reason=f"Exceeded max iterations ({max_iterations})",
            )

        # Reached end of content
        fallback = len(content) - 1 if is_line_based else min(start_pos + 5000, length)
        return BraceFindResult(
            end_position=fallback,
            success=False,
            reason="End of content reached without finding closing brace",
        )
