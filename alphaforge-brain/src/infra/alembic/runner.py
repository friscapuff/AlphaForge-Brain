from __future__ import annotations

import importlib
from importlib import resources
from sqlite3 import Connection
from typing import Iterable

from ..logging import get_logger

LOGGER = get_logger(__name__)


def _iter_version_modules() -> Iterable[str]:
    try:
        versions_pkg = resources.files(__package__).joinpath("versions")
    except FileNotFoundError:
        return []
    if not versions_pkg.is_dir():
        return []
    modules: list[str] = []
    for entry in versions_pkg.iterdir():
        if entry.name.endswith(".py") and entry.name != "__init__.py":
            modules.append(entry.name[:-3])
    modules.sort()
    return modules


def apply_python_migrations(conn: Connection) -> None:
    modules = _iter_version_modules()
    if not modules:
        return

    existing = {row[0] for row in conn.execute("SELECT id FROM schema_migrations")}

    for module_name in modules:
        module = importlib.import_module(f"{__package__}.versions.{module_name}")
        revision = getattr(module, "revision", module_name)
        migration_id = f"py_{revision}"
        if migration_id in existing:
            continue
        upgrade = getattr(module, "upgrade", None)
        if not callable(upgrade):
            LOGGER.warning("migration.skip.no_upgrade", module=module_name)
            continue
        LOGGER.info("migration.applying", id=migration_id, module=module_name)
        try:
            conn.execute("BEGIN")
            upgrade(conn)
            conn.execute(
                "INSERT INTO schema_migrations (id, applied_at) VALUES (?, strftime('%s','now'))",
                (migration_id,),
            )
            conn.execute("COMMIT")
            existing.add(migration_id)
        except Exception as exc:  # pragma: no cover - defensive guard
            conn.execute("ROLLBACK")
            LOGGER.error(
                "migration.failed",
                id=migration_id,
                module=module_name,
                error=str(exc),
            )
            raise


__all__ = ["apply_python_migrations"]
