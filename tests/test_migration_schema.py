"""The migration chain must build the schema that portal.models describes.

The rest of the suite creates tables with ``Base.metadata.create_all``, so a model change that
no migration covers (or the reverse) would pass every other test and only break a deployment.
"""

from __future__ import annotations

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.command import upgrade
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from portal.config import settings
from portal.models import Base

ROOT = Path(__file__).resolve().parent.parent


def alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    return config


def test_migrations_have_a_single_head():
    # Two branches (for example two PRs that both add revision 039) make ``alembic upgrade head`` fail.
    assert len(ScriptDirectory.from_config(alembic_config()).get_heads()) == 1


def test_migrations_build_the_schema_the_models_describe(tmp_path, monkeypatch):
    db_path = tmp_path / "migrated.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{db_path}")

    upgrade(alembic_config(), "head")

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as connection:
            differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()
    assert differences == [], f"models and migrations disagree: {differences}"
