from dataclasses import dataclass, field


@dataclass(frozen=True)
class DataTestDefinition:
    """A single data test to run against a model column."""

    model_name: str
    column: str
    test_type: str  # not_null, unique, accepted_values, etc.
    params: dict = field(default_factory=dict)
    severity: str = "error"  # "error" or "warn"
    where: str | None = None


@dataclass(frozen=True)
class DataTestResult:
    """Result of running a single data test."""

    test: DataTestDefinition
    passed: bool
    failures_count: int
    failures_sample: list[tuple]  # first N failing rows
    error: str | None = None  # database error, if any
