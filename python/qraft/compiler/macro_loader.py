import importlib
import importlib.util
import inspect
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_module_cache: dict[str, object] = {}


def load_macro_modules(
    macros_list: list[str],
    project_root: Path,
) -> dict[str, Callable[..., Any]]:
    """Import modules, discover public functions.

    Returns ``{function_name: callable}`` across all modules.
    """
    functions: dict[str, Callable[..., Any]] = {}

    for module_name in macros_list:
        module = _load_module(module_name, project_root)
        for name, macro_function in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue
            if name in functions:
                logger.warning(
                    "Macro function '%s' already defined, "
                    "ignoring duplicate from module '%s'",
                    name,
                    module_name,
                )
                continue
            functions[name] = macro_function

    return functions


def _load_module(name: str, project_root: Path) -> object:
    if name in _module_cache:
        return _module_cache[name]

    # Try local macros/ directory first
    macro_file = project_root / "macros" / f"{name}.py"
    if macro_file.exists():
        spec = importlib.util.spec_from_file_location(
            f"qraft_macros.{name}", macro_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _module_cache[name] = module
        return module

    # Fall back to installed package
    try:
        module = importlib.import_module(name)
        _module_cache[name] = module
        return module
    except ModuleNotFoundError:
        pass

    raise MacroModuleNotFound(
        f"Macro module '{name}' not found in macros/ directory "
        f"and not installed as a package"
    )


class MacroModuleNotFound(Exception):
    pass
