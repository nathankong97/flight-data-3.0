from pathlib import Path

import pytest

from src import airport_codes


def write_sample_file(tmp_path: Path, name: str, contents: str) -> Path:
    file_path = tmp_path / name
    file_path.write_text(contents, encoding="utf-8")
    return file_path


def test_load_airport_codes_reads_file(monkeypatch, tmp_path):
    base_dir = tmp_path / "data"
    base_dir.mkdir()
    write_sample_file(
        base_dir,
        "airport_JP.txt",
        """
        # Tokyo area
        HND
        NRT

        # duplicates
        HND
        """,
    )
    monkeypatch.setattr(airport_codes, "DATA_DIR", base_dir)

    codes = airport_codes.load_airport_codes("jp")

    assert codes == ["HND", "NRT"]


def test_load_airport_codes_raises_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(airport_codes, "DATA_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        airport_codes.load_airport_codes("us")


def test_load_airport_codes_rejects_blank(monkeypatch):
    with pytest.raises(ValueError):
        airport_codes.load_airport_codes("")


def test_available_regions(monkeypatch, tmp_path):
    base_dir = tmp_path / "data"
    base_dir.mkdir()
    write_sample_file(base_dir, "airport_US.txt", "LAX\nJFK\n")
    write_sample_file(base_dir, "airport_cn.txt", "CAN\nPEK\n")
    write_sample_file(base_dir, "ignore.txt", "")
    monkeypatch.setattr(airport_codes, "DATA_DIR", base_dir)

    regions = airport_codes.available_regions()

    assert regions == ["CN", "US"]
