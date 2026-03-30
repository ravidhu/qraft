import os
import re
from pathlib import Path

from dotenv import load_dotenv

ENV_VAR_RE = re.compile(r"\$\{(\w+)\}")


def load_env(project_dir: Path = Path(".")) -> None:
    """Load the project's .env file."""
    env_path = project_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def resolve_env_vars(obj: object) -> object:
    """Recursively resolve ${VAR} in a dict/list/str."""
    if isinstance(obj, str):

        def replace(match: re.Match) -> str:
            var_name = match.group(1)
            value = os.environ.get(var_name)
            if value is None:
                raise ValueError(
                    f"Environment variable ${{{var_name}}} is not set"
                )
            return value

        return ENV_VAR_RE.sub(replace, obj)
    elif isinstance(obj, dict):
        return {k: resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_env_vars(item) for item in obj]
    return obj
