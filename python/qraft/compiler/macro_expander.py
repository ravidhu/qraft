import inspect
import traceback
from pathlib import Path

from qraft import _core
from qraft.compiler.macro_loader import MacroModuleNotFound, load_macro_modules


class MacroArgumentError(Exception):
    pass


class MacroExpansionError(Exception):
    pass


class MacroExpansionLoop(Exception):
    pass


def expand(
    sql: str,
    macros_list: list[str],
    vars: dict[str, str],
    model_name: str,
    project_root: Path,
) -> str:
    """
    Expand all macro calls in resolved SQL.
    Returns SQL with all macro calls replaced by their expansions.
    """
    known_functions = load_macro_modules(macros_list, project_root)
    known_function_names = list(known_functions.keys())

    max_iterations = 100
    for iteration in range(max_iterations):
        calls = _core.find_macro_calls(sql, known_function_names)
        if not calls:
            break

        # Process calls right to left to preserve positions
        for call in reversed(calls):
            macro_function = known_functions[call.name]

            # Validate argument count
            sig = inspect.signature(macro_function)
            params = [
                p
                for p in sig.parameters.values()
                if p.name != "vars"
                and p.default is inspect.Parameter.empty
            ]
            if len(call.args) != len(params):
                raise MacroArgumentError(
                    f"'{call.name}' expects {len(params)} arguments, "
                    f"got {len(call.args)} in model '{model_name}'"
                )

            # Call the macro function
            try:
                result = macro_function(*call.args, vars=vars)
            except Exception as error:
                raise MacroExpansionError(
                    f"Error in '{call.name}' for model '{model_name}': "
                    f"{type(error).__name__}: {error}\n"
                    f"{traceback.format_exc()}"
                ) from error

            if not isinstance(result, str):
                raise MacroExpansionError(
                    f"'{call.name}' must return a string, "
                    f"got {type(result).__name__}"
                )

            # Replace the call site
            sql = sql[:call.start] + result + sql[call.end:]
    else:
        raise MacroExpansionLoop(
            f"Macro expansion exceeded {max_iterations} iterations "
            f"in model '{model_name}' -- possible infinite loop"
        )

    return sql
