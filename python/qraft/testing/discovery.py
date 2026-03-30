import yaml

from qraft.config.models import Model
from qraft.testing.models import DataTestDefinition


def _extract_yaml_front_matter(raw_sql: str) -> dict | None:
    """Extract and parse YAML front-matter from raw SQL using PyYAML.

    Unlike the Rust parser (which only handles flat key:value),
    this handles nested structures like the `columns:` block.
    """
    trimmed = raw_sql.strip()
    if not trimmed.startswith("---"):
        return None

    end = trimmed.find("---", 3)
    if end == -1:
        return None

    yaml_block = trimmed[3:end]
    try:
        parsed = yaml.safe_load(yaml_block)
        return parsed if isinstance(parsed, dict) else None
    except yaml.YAMLError:
        return None


def discover_tests(models: list[Model]) -> list[DataTestDefinition]:
    """Discover test definitions from model front-matter `columns:` blocks."""
    tests: list[DataTestDefinition] = []

    for model in models:
        front_matter_content = _extract_yaml_front_matter(model.raw_sql)
        if front_matter_content is None:
            continue

        columns = front_matter_content.get("columns")
        if columns is None:
            continue

        # Normalise columns to list of (name, config_dict) pairs.
        # Supports two formats:
        #   dict: {col_name: {tests: [...]}}
        #   list: [{name: col_name, tests: [...]}]  (dbt-style)
        col_pairs: list[tuple[str, dict]] = []
        if isinstance(columns, dict):
            for col_name, col_config in columns.items():
                if isinstance(col_config, dict):
                    col_pairs.append((col_name, col_config))
        elif isinstance(columns, list):
            for item in columns:
                if isinstance(item, dict) and "name" in item:
                    col_pairs.append((item["name"], item))
        else:
            continue

        for col_name, col_config in col_pairs:
            col_tests = col_config.get("tests")
            if not col_tests or not isinstance(col_tests, list):
                continue

            for test_entry in col_tests:
                test_def = _parse_test_entry(model.name, col_name, test_entry)
                if test_def is not None:
                    tests.append(test_def)

    return tests


def _parse_test_entry(
    model_name: str, column: str, entry: str | dict
) -> DataTestDefinition | None:
    """Parse a single test entry from the YAML into a DataTestDefinition."""
    if isinstance(entry, str):
        # Simple test: "unique", "not_null"
        return DataTestDefinition(
            model_name=model_name,
            column=column,
            test_type=entry,
        )

    if isinstance(entry, dict):
        # Parameterized test: {accepted_values: {values: [...]}}
        if len(entry) != 1:
            return None

        test_type = next(iter(entry))
        config = entry[test_type]
        if not isinstance(config, dict):
            config = {}

        # Extract test-level config (severity, where) from params
        severity = config.pop("severity", "error")
        where_clause = config.pop("where", None)

        return DataTestDefinition(
            model_name=model_name,
            column=column,
            test_type=test_type,
            params=config,
            severity=str(severity),
            where=str(where_clause) if where_clause is not None else None,
        )

    return None
