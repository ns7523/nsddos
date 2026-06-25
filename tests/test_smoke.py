"""Basic scaffold smoke tests."""

from pathlib import Path

from nsddos import config as config_module


def test_load_config_returns_dict(tmp_path: Path, monkeypatch) -> None:
    """Config loader should return dictionary."""
    runtime_dirs = (
        tmp_path,
        tmp_path / "logs",
        tmp_path / "runtime",
        tmp_path / "runtime" / "snapshots",
    )
    monkeypatch.setattr(config_module, "RUNTIME_DIRECTORIES", runtime_dirs)
    assert isinstance(config_module.load_config(tmp_path / "config.yaml"), dict)
