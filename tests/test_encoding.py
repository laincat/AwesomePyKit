"""Exercise chardet fallback decoding used by pip subprocess output."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fastpip.com import common


@pytest.mark.parametrize("encoding", ["gb18030", "cp1251"])
def test_detected_encoding_is_taken_from_result_dict(monkeypatch, encoding):
    monkeypatch.setattr(common, "__pdc", "ascii")
    monkeypatch.setattr(common, "__lpc", "ascii")
    monkeypatch.setattr(common, "detect", lambda data: {"encoding": encoding})
    text = "中文测试" if encoding == "gb18030" else "Привет мир"
    assert common.decode_bytes(text.encode(encoding)) == text


@pytest.mark.parametrize("encoding", [None, "nonexistent-codec"])
def test_unknown_encoding_returns_diagnostic(monkeypatch, encoding):
    monkeypatch.setattr(common, "__pdc", "ascii")
    monkeypatch.setattr(common, "__lpc", "ascii")
    monkeypatch.setattr(common, "detect", lambda data: {"encoding": encoding})
    assert common.decode_bytes(b"\xff").startswith("fastpip:")
