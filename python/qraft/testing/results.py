import json
from datetime import datetime, timezone
from pathlib import Path

from qraft.testing.models import DataTestResult


def write_test_results(
    results: list[DataTestResult],
    env_name: str,
    schema: str,
    target_dir: Path,
) -> Path:
    """Write test results to target/test_results.json.

    Returns the path to the written file.
    """
    test_entries = []
    for test_result in results:
        entry: dict = {
            "model": test_result.test.model_name,
            "column": test_result.test.column,
            "test_type": test_result.test.test_type,
            "severity": test_result.test.severity,
            "passed": test_result.passed,
        }
        if test_result.test.params:
            entry["params"] = test_result.test.params
        if test_result.test.where:
            entry["where"] = test_result.test.where
        if not test_result.passed:
            entry["failures_count"] = test_result.failures_count
            if test_result.failures_sample:
                entry["failures_sample"] = [
                    [str(v) for v in row] for row in test_result.failures_sample
                ]
        if test_result.error:
            entry["error"] = test_result.error
        test_entries.append(entry)

    passed = sum(1 for test_result in results if test_result.passed)
    failed = sum(1 for test_result in results if not test_result.passed and test_result.test.severity == "error" and not test_result.error)
    warned = sum(1 for test_result in results if not test_result.passed and test_result.test.severity == "warn")
    errored = sum(1 for test_result in results if test_result.error)

    payload = {
        "metadata": {
            "env": env_name,
            "schema": schema,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "errored": errored,
        },
        "results": test_entries,
    }

    out_path = target_dir / "test_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path
