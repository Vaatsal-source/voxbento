"""The migration chain must build the schema that portal.models describes.

The rest of the suite creates tables with ``Base.metadata.create_all``, so a model change that
no migration covers (or the reverse) would pass every other test and only break a deployment.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from portal.models import Base

ROOT = Path(__file__).resolve().parent.parent


def alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    return config


def test_migrations_have_a_single_head():
    assert len(ScriptDirectory.from_config(alembic_config()).get_heads()) == 1


def test_migrations_build_the_schema_the_models_describe(tmp_path):
    db_path = tmp_path / "migrated.db"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env={**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as connection:
            differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()
    assert differences == [], f"models and migrations disagree: {differences}"
