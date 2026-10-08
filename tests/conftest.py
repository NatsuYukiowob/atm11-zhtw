import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import common  # noqa: E402


@pytest.fixture(autouse=True)
def no_glossary(monkeypatch):
    """測試不讀 work/glossary.json：術語表設為空，to_tw 只剩 OpenCC。"""
    monkeypatch.setattr(common, "_glossary_rules", [])


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """把 WORK/DATA/QUEUE/REPORTS/DIST 指到暫存目錄（新模組一律用 common.X 屬性存取）。"""
    for name in ("WORK", "DATA", "QUEUE", "REPORTS", "DIST"):
        d = tmp_path / name.lower()
        d.mkdir()
        monkeypatch.setattr(common, name, d)
    return tmp_path
