"""GBK-default regression without pretending a Linux host is native Windows."""

import ast
import io

import pytest

from scm.platform.demo import seed
from scm.platform.service import generate_report, rows
from scm.ports.registry import registry, source_specs
from scm.settings import ROOT


@pytest.fixture
def gbk_default(monkeypatch):
    original_open = io.open

    def gbk_open(
        file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None
    ):
        if "b" not in mode and encoding in [None, "locale"]:
            encoding = "gbk"
        return original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    monkeypatch.setattr(io, "open", gbk_open)


def test_port_registry_under_gbk_default(gbk_default):
    # Negative control: reproduce the original failure, regardless of host locale/UTF-8 mode.
    with pytest.raises(UnicodeDecodeError):
        with io.open(ROOT / "config/ports.json", encoding="locale") as stream:
            stream.read()
    ports = registry().ports
    assert len(ports) == 12
    assert next(p for p in ports if p.id == "dover").name_zh == "多佛"
    assert source_specs()


def test_demo_reports_and_text_roundtrip_under_gbk_default(factory, tmp_path, gbk_default):
    assert seed(factory)["inserted"] == 5
    with factory.begin() as session:
        assert len(rows(session, "demo")) == 5
        assert not rows(session, "live")
        for kind in ["daily", "weekly"]:
            document = generate_report(session, "demo", kind).html
            target = tmp_path / f"中文报告-{kind}.html"
            target.write_text(document, encoding="utf-8")
            assert "来源与数据质量" in target.read_text(encoding="utf-8")
            assert target.read_bytes() == document.encode("utf-8")
    for suffix in ["json", "csv", "md", "html"]:
        target = tmp_path / ("中文资料." + suffix)
        target.write_text("港口、多佛、欧元 €、预警 →", encoding="utf-8")
        assert target.read_text(encoding="utf-8") == "港口、多佛、欧元 €、预警 →"


def test_project_path_text_io_declares_encoding():
    failures = []
    # Include operational/browser scripts and test fixtures, not just production imports.
    for folder in ["src", "scripts", "tests", "migrations", "docs/ui_uat"]:
        for file in (ROOT / folder).rglob("*.py"):
            for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr not in ["read_text", "write_text"]:
                    continue
                encoding = next((k.value for k in node.keywords if k.arg == "encoding"), None)
                positional = node.args[0 if node.func.attr == "read_text" else 1 :]
                if encoding is None and not positional:
                    failures.append(f"{file.relative_to(ROOT)}:{node.lineno}")
                elif isinstance(encoding, ast.Constant) and encoding.value in [None, "locale"]:
                    failures.append(f"{file.relative_to(ROOT)}:{node.lineno}: implicit locale")
    assert not failures, "Project text file I/O needs explicit encoding: " + ", ".join(failures)
