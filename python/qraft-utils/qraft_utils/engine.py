"""Engine type enum for cross-engine SQL generation."""

from enum import StrEnum


class Engine(StrEnum):
    DUCKDB = "duckdb"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    TRINO = "trino"

    @classmethod
    def from_vars(cls, vars: dict) -> "Engine":
        """Extract the engine type from the vars dict.

        Falls back to POSTGRES when vars["engine"] is missing or unrecognized.
        """
        raw = vars.get("engine", "postgres")
        try:
            return cls(raw)
        except ValueError:
            return cls.POSTGRES
