import pytest
from sqlalchemy.orm import sessionmaker

from scm.database.session import make_engine, migrate


@pytest.fixture
def factory(tmp_path):
    engine = make_engine("sqlite:///" + str(tmp_path / "test.db"))
    migrate(engine)
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()
