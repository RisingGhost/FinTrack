import re
from typing import Any

_PARAM_RE = re.compile(r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)")


def bind_named_params(sql: str, params: dict[str, Any]) -> tuple[str, list[Any]]:
    """Convert :named params SQL to asyncpg positional SQL ($1, $2, ...)."""
    order: list[str] = []
    indexes: dict[str, int] = {}

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in params:
            raise KeyError(f"Missing SQL parameter: {name}")

        idx = indexes.get(name)
        if idx is None:
            order.append(name)
            idx = len(order)
            indexes[name] = idx

        return f"${idx}"

    converted_sql = _PARAM_RE.sub(repl, sql)
    args = [params[name] for name in order]
    return converted_sql, args
