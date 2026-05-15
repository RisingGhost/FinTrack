from pathlib import Path


def load_sql_queries(queries_dir: str) -> dict[str, str]:
    base_path = Path(queries_dir)
    if not base_path.exists():
        raise FileNotFoundError(f"Queries dir not found: {queries_dir}")

    queries: dict[str, str] = {}
    for file_path in sorted(base_path.rglob("*.sql")):
        relative_path = file_path.relative_to(base_path).as_posix()
        queries[relative_path] = file_path.read_text(encoding="utf-8")

    return queries
