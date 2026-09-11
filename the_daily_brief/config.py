"""Configuration loader for The Daily Brief."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


@dataclass
class LLMConfig:
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"


@dataclass
class Config:
    output_dir: Path = field(default_factory=lambda: Path("~/.the-daily-brief").expanduser())
    brief_after_hour: int = 9
    brief_language: str = "en"
    llm: LLMConfig = field(default_factory=LLMConfig)
    connectors: dict[str, Any] = field(default_factory=dict)

    @property
    def briefs_dir(self) -> Path:
        """Directory where generated briefs are stored."""
        return self.output_dir / "briefs"

    @property
    def state_file(self) -> Path:
        """Path to the state JSON file."""
        return self.output_dir / "state.json"

    @property
    def logs_dir(self) -> Path:
        """Directory where logs are stored."""
        return self.output_dir / "logs"

    def ensure_directories(self) -> None:
        """Ensure all required output directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.briefs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


def load_config(
    config_path: Path | str | None = None,
    env_path: Path | str | None = None,
) -> Config:
    """Load configuration from YAML and environment variables."""
    if env_path is not None:
        load_dotenv(Path(env_path))
    else:
        load_dotenv(PROJECT_ROOT / ".env")

    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH

    raw: dict[str, Any] = {}
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                raw = loaded
    else:
        logger.warning("Config file not found at %s, using defaults", path)

    output_dir_str = raw.get("output_dir", "~/.the-daily-brief")
    output_dir = Path(os.path.expanduser(str(output_dir_str)))

    llm_raw = raw.get("llm", {})
    llm_config = LLMConfig(
        provider=llm_raw.get("provider", "gemini"),
        model=llm_raw.get("model", "gemini-2.0-flash"),
    )

    return Config(
        output_dir=output_dir,
        brief_after_hour=raw.get("brief_after_hour", 9),
        brief_language=raw.get("brief_language", "en"),
        llm=llm_config,
        connectors=raw.get("connectors", {}),
    )


_current_config: Config | None = None


def get_config() -> Config:
    """Get the cached configuration instance or load it."""
    global _current_config
    if _current_config is None:
        _current_config = load_config()
    return _current_config
