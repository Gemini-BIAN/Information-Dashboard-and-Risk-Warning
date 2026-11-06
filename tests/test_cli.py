import os
import subprocess
import sys

from sqlalchemy import func, select

from scm.database.models import Event, Report, ShipmentSnapshot
from scm.database.session import session_factory
from scm.settings import ROOT


def test_cli_fresh_database_without_api_key(tmp_path):
    database = "sqlite:///" + str(tmp_path / "e2e.db")
    environment = os.environ.copy()
    environment.pop("SCM_LLM_API_KEY", None)
    environment["SCM_LLM_PROVIDER"] = "none"
    for command in [
        ["init"],
        ["demo"],
        ["demo"],
        [
            "report",
            "--kind",
            "daily",
            "--mode",
            "demo",
            "--day",
            "2026-11-06",
            "--output",
            str(tmp_path / "daily.html"),
        ],
        [
            "report",
            "--kind",
            "weekly",
            "--mode",
            "demo",
            "--day",
            "2026-11-06",
            "--output",
            str(tmp_path / "weekly.html"),
        ],
    ]:
        result = subprocess.run(
            [sys.executable, "-m", "scm.cli", "--database-url", database, *command],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
    with session_factory(database)() as session:
        assert session.scalar(select(func.count()).select_from(Event)) == 5
        assert session.scalar(select(func.count()).select_from(ShipmentSnapshot)) == 3
        assert session.scalar(select(func.count()).select_from(Report)) == 2
    assert "演示数据" in (tmp_path / "daily.html").read_text(encoding="utf-8")
    assert "未来1–3个月" in (tmp_path / "weekly.html").read_text(encoding="utf-8")
