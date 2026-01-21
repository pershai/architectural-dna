"""Constants and configuration values for C# architectural analysis.

This module centralizes magic numbers and thresholds used throughout
the C# semantic analysis and pattern detection systems.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CSharpAnalysisConstants:
    """Constants for C# code analysis."""

    # Attribute extraction
    ATTRIBUTE_SEARCH_LINES_BEFORE: int = 10  # Lines to search before class/method
    ATTRIBUTE_SEARCH_LINES_AFTER: int = 5    # Lines to search after class/method

    # LCOM calculation
    METHOD_REGION_SIZE: int = 500      # Characters to examine per method
    METHOD_REGION_FALLBACK: int = 1000  # Fallback size if brace matching fails

    # Pattern detection confidence thresholds
    PATTERN_CONFIDENCE_HIGH: float = 0.6    # High confidence threshold
    PATTERN_CONFIDENCE_MEDIUM: float = 0.5  # Medium confidence threshold
    PATTERN_CONFIDENCE_LOW: float = 0.4     # Low confidence threshold

    # Quality scoring thresholds (referenced from config.yaml, but can be overridden)
    DEFAULT_LCOM_THRESHOLD: float = 0.8
    DEFAULT_LOC_THRESHOLD: int = 500
    DEFAULT_COMPLEXITY_THRESHOLD: int = 15

    # Dependency limits
    DEFAULT_MAX_DEPENDENCIES_PER_CLASS: int = 7
    DEFAULT_MAX_DEPENDENCIES_PER_NAMESPACE: int = 50

    # Pattern detection scoring weights
    SINGLETON_INDICATORS: int = 3  # Number of indicators for singleton pattern
    FACTORY_INDICATORS: int = 3
    BUILDER_INDICATORS: int = 3
    REPOSITORY_INDICATORS: int = 3
    DECORATOR_INDICATORS: int = 3
    ADAPTER_INDICATORS: int = 3
    FACADE_INDICATORS: int = 2
    PROXY_INDICATORS: int = 2
    OBSERVER_INDICATORS: int = 3
    STRATEGY_INDICATORS: int = 3
    COMMAND_INDICATORS: int = 3
    CHAIN_OF_RESPONSIBILITY_INDICATORS: int = 3
    STATE_INDICATORS: int = 3
    UNIT_OF_WORK_INDICATORS: int = 3
    CQRS_INDICATORS: int = 3
    EVENT_SOURCING_INDICATORS: int = 3
    PUBSUB_INDICATORS: int = 3


# Global instance for easy access
CSHARP_CONSTANTS = CSharpAnalysisConstants()
