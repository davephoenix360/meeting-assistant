from logging.config import fileConfig
import os
import sys

from alembic import context
from sqlalchemy import create_engine, pool

# Alembic loads this file with `backend/alembic/` on sys.path; add the backend
# root so imports like `app.*` work reliably.
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.core.config import settings
from app.db.session import Base
from app.models import models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine_kwargs = {"poolclass": pool.NullPool}
    if settings.database_url.startswith("postgresql"):
        engine_kwargs["connect_args"] = {"connect_timeout": 5}

    connectable = create_engine(settings.database_url, **engine_kwargs)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
