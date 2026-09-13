"""Tests for configuration loading."""

from pathlib import Path

from the_daily_brief.config import load_config


def test_load_config_defaults(tmp_path: Path) -> None:
    """Test loading configuration when no file is present."""
    non_existent = tmp_path / "missing.yaml"
    config = load_config(config_path=non_existent)

    assert config.storage_dir == Path("~/Desktop/TheDailyBrief").expanduser()
    assert config.brief_language == "en"
    assert config.llm.provider == "gemini"
    assert config.llm.model == "gemini-2.0-flash"
    assert config.briefs_dir == config.output_dir / "briefs"
    assert config.state_file == config.output_dir / "state.json"
    assert config.logs_dir == config.output_dir / "logs"
    assert "default" in config.spaces


def test_load_config_from_yaml(tmp_path: Path) -> None:
    """Test loading configuration from a valid YAML file."""
    yaml_content = """
output_dir: /tmp/test-brief
storage_dir: /tmp/test-saves
brief_language: ru
llm:
  provider: openai
  model: gpt-4o
spaces:
  work:
    gmail_token_env: GMAIL_REFRESH_TOKEN_WORK
    audit_days: 7
    obsidian_enabled: false
connectors:
  gmail:
    enabled: true
    max_emails: 10
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    config = load_config(config_path=config_file)
    assert config.output_dir == Path("/tmp/test-brief")
    assert config.storage_dir == Path("/tmp/test-saves")
    assert config.brief_language == "ru"
    assert config.llm.provider == "openai"
    assert config.llm.model == "gpt-4o"
    assert "work" in config.spaces
    assert config.spaces["work"].gmail_token_env == "GMAIL_REFRESH_TOKEN_WORK"
    assert config.spaces["work"].gmail_audit_days == 7
    assert config.spaces["work"].obsidian_enabled is False
    assert config.connectors["gmail"]["enabled"] is True
    assert config.connectors["gmail"]["max_emails"] == 10
