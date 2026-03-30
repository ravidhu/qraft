import logging
import time

from qraft.config.models import Model
from qraft.engine.base import Engine
from qraft.testing.discovery import discover_tests
from qraft.testing.generic import generate_test_sql
from qraft.testing.models import DataTestDefinition, DataTestResult

logger = logging.getLogger(__name__)

_SAMPLE_LIMIT = 5


def run_tests(
    models: list[Model],
    engine: Engine,
    schema: str,
    select: str | None = None,
    fail_fast: bool = False,
) -> list[DataTestResult]:
    """Discover and run all data tests for the given models.

    Returns a list of DataTestResult for each test executed.
    """
    all_tests = discover_tests(models)

    if not all_tests:
        return []

    # Filter by model selection if provided
    if select:
        selected_models = _resolve_select(select, models)
        all_tests = [t for t in all_tests if t.model_name in selected_models]

    results: list[DataTestResult] = []
    for test in all_tests:
        target = f"{schema}.{test.model_name}"

        # Check if model has a schema override in its front-matter
        model = next((model for model in models if model.name == test.model_name), None)
        if model:
            target = _resolve_target(model, schema)

        result = _run_single_test(test, target, engine)
        results.append(result)

        if fail_fast and not result.passed and result.test.severity == "error":
            break

    return results


def _run_single_test(
    test: DataTestDefinition, target: str, engine: Engine
) -> DataTestResult:
    """Execute a single data test and return the result."""
    try:
        sql = generate_test_sql(test, target)
    except ValueError as e:
        return DataTestResult(
            test=test,
            passed=False,
            failures_count=0,
            failures_sample=[],
            error=str(e),
        )

    try:
        # Fetch up to SAMPLE_LIMIT + 1 rows to determine if there are failures
        limited_sql = f"SELECT * FROM ({sql}) _qraft_test LIMIT {_SAMPLE_LIMIT + 1}"
        rows = engine.query(limited_sql)
        failures_count = len(rows)
        sample = rows[:_SAMPLE_LIMIT]

        return DataTestResult(
            test=test,
            passed=failures_count == 0,
            failures_count=failures_count,
            failures_sample=sample,
        )
    except Exception as error:
        return DataTestResult(
            test=test,
            passed=False,
            failures_count=0,
            failures_sample=[],
            error=str(error),
        )


def _resolve_target(model: Model, default_schema: str) -> str:
    """Resolve the fully qualified target for a model."""
    from qraft.testing.discovery import _extract_yaml_front_matter

    front_matter_content = _extract_yaml_front_matter(model.raw_sql)
    if front_matter_content and "schema" in front_matter_content:
        return f"{front_matter_content['schema']}.{model.name}"
    return f"{default_schema}.{model.name}"


def _resolve_select(select: str, models: list[Model]) -> set[str]:
    """Simple model name selection. Supports exact match and tag:name."""
    selected: set[str] = set()

    if select.startswith("tag:"):
        tag = select[4:]
        for model in models:
            from qraft.testing.discovery import _extract_yaml_front_matter

            front_matter_content = _extract_yaml_front_matter(model.raw_sql)
            if front_matter_content:
                tags = front_matter_content.get("tags", [])
                if isinstance(tags, list) and tag in tags:
                    selected.add(model.name)
                elif isinstance(tags, str) and tag in tags.split(","):
                    selected.add(model.name)
    else:
        # Exact match or wildcard prefix
        for model in models:
            if select.endswith("*"):
                if model.name.startswith(select[:-1]):
                    selected.add(model.name)
            elif model.name == select or select in (
                f"{model.name}+",
                f"+{model.name}",
                f"+{model.name}+",
            ):
                selected.add(model.name)

    return selected
