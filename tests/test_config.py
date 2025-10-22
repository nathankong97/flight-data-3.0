import pytest

from src.config import REPO_ROOT, load_config


def _clear_db_env(monkeypatch):
    for key in [
        "DATABASE_URL",
        "DATABASE_HOST",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
        "DATABASE_NAME",
        "DATABASE_PORT",
        "HOST",
        "USER",
        "PASSWORD",
        "DB",
        "PORT",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_load_config_reads_env_file(tmp_path, monkeypatch):
    _clear_db_env(monkeypatch)
    env_file = tmp_path / "test.env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql://example",
                "LOG_DIR=logs/testing",
                "LOG_LEVEL=debug",
                "APP_NAME=ingest-runner",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("LOG_DIR", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("APP_NAME", raising=False)

    config = load_config(env_file)

    assert config.database_url == "postgresql://example"
    assert config.log_directory == REPO_ROOT / "logs/testing"
    assert config.log_level == "DEBUG"
    assert config.app_name == "ingest-runner"


def test_load_config_prefers_environment_variables(tmp_path, monkeypatch):
    _clear_db_env(monkeypatch)
    env_file = tmp_path / "test.env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql://example",
                f"LOG_DIR={tmp_path/'from_env_file'}",
            ]
        ),
        encoding="utf-8",
    )

    env_log_dir = tmp_path / "from_env"
    monkeypatch.setenv("DATABASE_URL", "postgresql://override")
    monkeypatch.setenv("LOG_DIR", str(env_log_dir))
    monkeypatch.setenv("LOG_LEVEL", "warning")
    monkeypatch.setenv("APP_NAME", "runtime-app")

    config = load_config(env_file)

    assert config.database_url == "postgresql://override"
    assert config.log_directory == env_log_dir
    assert config.log_level == "WARNING"
    assert config.app_name == "runtime-app"


def test_load_config_requires_database_url(tmp_path, monkeypatch):
    _clear_db_env(monkeypatch)
    env_file = tmp_path / "empty.env"
    env_file.write_text("", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError):
        load_config(env_file)


def test_load_config_builds_url_from_components(tmp_path, monkeypatch):
    _clear_db_env(monkeypatch)
    env_file = tmp_path / "components.env"
    env_file.write_text(
        "\n".join(
            [
                "HOST=db.internal",
                "USER=ingest",
                "PASSWORD=secret!",
                "DB=flights",
                "LOG_DIR=logs",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(env_file)

    assert (
        config.database_url
        == "postgresql://ingest:secret%21@db.internal:5432/flights"
    )
    assert config.log_directory == REPO_ROOT / "logs"
