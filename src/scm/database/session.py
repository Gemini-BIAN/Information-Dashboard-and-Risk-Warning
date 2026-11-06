from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from scm.settings import DATABASE_URL, ROOT


def make_engine(url=DATABASE_URL):
    if url.startswith("sqlite:///") and ":memory:" not in url:
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        url, connect_args={"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def sqlite_settings(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")

    return engine


def migrate(engine):
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")


def session_factory(url=DATABASE_URL):
    engine = make_engine(url)
    migrate(engine)
    return sessionmaker(engine, expire_on_commit=False)
