"""Configuration loader for The Daily Brief."""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
SPACE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def is_valid_space_name(name: str) -> bool:
    """Validate that space name contains only alphanumeric characters, dashes, or underscores."""
    return bool(SPACE_NAME_REGEX.match(name))


@dataclass
class LLMConfig:
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"


@dataclass
class ConnectorInstance:
    """Instance of a connector configured within a space."""

    id: str
    type: str  # e.g. "gmail", "obsidian"
    name: str  # human-readable label, e.g. "Work Gmail"
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert connector instance to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "config": self.config,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConnectorInstance":
        """Load connector instance from dictionary."""
        return cls(
            id=str(data.get("id", data.get("type", "conn"))),
            type=str(data.get("type", "gmail")),
            name=str(data.get("name", data.get("type", "Unnamed"))),
            config=dict(data.get("config", {})),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass
class SpaceConfig:
    """Configuration for a specific space with dynamic connectors."""

    name: str
    connectors: list[ConnectorInstance] = field(default_factory=list)

    @property
    def gmail_token_env(self) -> str:
        for c in self.connectors:
            if c.type == "gmail" and c.enabled:
                return str(c.config.get("token_env", "GMAIL_REFRESH_TOKEN"))
        return (
            "GMAIL_REFRESH_TOKEN"
            if self.name == "default"
            else f"GMAIL_REFRESH_TOKEN_{self.name.upper().replace('-', '_')}"
        )

    @property
    def gmail_audit_days(self) -> int:
        for c in self.connectors:
            if c.type == "gmail" and c.enabled:
                return int(c.config.get("audit_days", 5))
        return 5

    @property
    def gmail_max_emails(self) -> int:
        for c in self.connectors:
            if c.type == "gmail" and c.enabled:
                return int(c.config.get("max_emails", 20))
        return 20

    @property
    def gmail_scan_hours(self) -> int:
        for c in self.connectors:
            if c.type == "gmail" and c.enabled:
                return int(c.config.get("scan_hours", 12))
        return 12

    @property
    def obsidian_enabled(self) -> bool:
        return any(c.type == "obsidian" and c.enabled for c in self.connectors)

    @property
    def obsidian_scan_dirs(self) -> list[str]:
        for c in self.connectors:
            if c.type == "obsidian" and c.enabled:
                dirs = c.config.get("scan_dirs", ["50 Daily", "10 Projects"])
                if isinstance(dirs, str):
                    return [d.strip() for d in dirs.split(",") if d.strip()]
                return list(dirs)
        return ["50 Daily", "10 Projects"]

    def to_dict(self) -> dict[str, Any]:
        """Convert SpaceConfig to dictionary."""
        return {
            "name": self.name,
            "connectors": [c.to_dict() for c in self.connectors],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpaceConfig":
        """Load SpaceConfig from dictionary."""
        name = str(data.get("name", "default"))
        conns_data = data.get("connectors", [])
        connectors: list[ConnectorInstance] = []
        for c_item in conns_data:
            if isinstance(c_item, dict):
                connectors.append(ConnectorInstance.from_dict(c_item))
        return cls(name=name, connectors=connectors)


@dataclass
class Config:
    output_dir: Path = field(default_factory=lambda: Path("~/.the-daily-brief").expanduser())
    storage_dir: Path = field(default_factory=lambda: Path("~/Desktop/TheDailyBrief").expanduser())
    brief_language: str = "en"
    llm: LLMConfig = field(default_factory=LLMConfig)
    connectors: dict[str, Any] = field(default_factory=dict)
    spaces: dict[str, SpaceConfig] = field(default_factory=dict)

    @property
    def briefs_dir(self) -> Path:
        """Directory where generated briefs are stored."""
        return self.output_dir / "briefs"

    @property
    def state_file(self) -> Path:
        """Path to the state JSON file."""
        return self.output_dir / "state.json"

    @property
    def spaces_file(self) -> Path:
        """Path to the spaces JSON file."""
        return self.output_dir / "spaces.json"

    @property
    def logs_dir(self) -> Path:
        """Directory where logs are stored."""
        return self.output_dir / "logs"

    def get_space(self, name: str) -> SpaceConfig:
        """Get configuration for a space by name, creating a default fallback if missing."""
        if name in self.spaces:
            return self.spaces[name]

        # Dynamic fallback for unconfigured space
        token_env = (
            "GMAIL_REFRESH_TOKEN"
            if name == "default"
            else f"GMAIL_REFRESH_TOKEN_{name.upper().replace('-', '_')}"
        )
        return SpaceConfig(
            name=name,
            connectors=[
                ConnectorInstance(
                    id=f"{name}_gmail",
                    type="gmail",
                    name=f"{name.capitalize()} Gmail",
                    config={"token_env": token_env},
                )
            ],
        )

    def get_space_dir(self, space_name: str, target_date: date | None = None) -> Path:
        """Get or create target output directory for space: <storage_dir>/<DD-MM-YY>/<space>."""
        if not is_valid_space_name(space_name):
            raise ValueError(f"Invalid space name: {space_name!r}")
        date_str = (target_date or date.today()).strftime("%d-%m-%y")
        path = (self.storage_dir / date_str / space_name).resolve()
        # Verify path remains within storage_dir boundary
        if not path.is_relative_to(self.storage_dir.resolve()):
            raise ValueError(f"Path traversal detected in space name: {space_name!r}")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_spaces(self) -> None:
        """Persist spaces configuration to output_dir/spaces.json atomically."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        payload = {name: space.to_dict() for name, space in self.spaces.items()}
        tmp_file = self.spaces_file.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_file, self.spaces_file)

    def add_space(self, name: str) -> SpaceConfig:
        """Add a new space and persist changes."""
        clean_name = name.strip().lower().replace(" ", "_")
        if not is_valid_space_name(clean_name):
            raise ValueError(f"Invalid space identifier: {clean_name!r}")
        if clean_name not in self.spaces:
            self.spaces[clean_name] = SpaceConfig(name=clean_name, connectors=[])
            self.save_spaces()
        return self.spaces[clean_name]

    def remove_space(self, name: str) -> bool:
        """Remove a space and persist changes."""
        if name in self.spaces:
            del self.spaces[name]
            self.save_spaces()
            return True
        return False

    def add_connector(self, space_name: str, conn: ConnectorInstance) -> None:
        """Add a connector to a space and persist changes."""
        space = self.get_space(space_name)
        if space_name not in self.spaces:
            self.spaces[space_name] = space
        # Avoid duplicate IDs
        space.connectors = [c for c in space.connectors if c.id != conn.id]
        space.connectors.append(conn)
        self.save_spaces()

    def remove_connector(self, space_name: str, conn_id: str) -> bool:
        """Remove a connector by ID from a space and persist changes."""
        if space_name in self.spaces:
            before_len = len(self.spaces[space_name].connectors)
            self.spaces[space_name].connectors = [
                c for c in self.spaces[space_name].connectors if c.id != conn_id
            ]
            if len(self.spaces[space_name].connectors) != before_len:
                self.save_spaces()
                return True
        return False

    def ensure_directories(self) -> None:
        """Ensure all required output directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.briefs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)


def load_config(
    config_path: Path | str | None = None,
    env_path: Path | str | None = None,
) -> Config:
    """Load configuration from YAML, spaces.json, and environment variables."""
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

    env_storage = os.getenv("DAILY_BRIEF_STORAGE_PATH")
    storage_dir_str = env_storage or raw.get("storage_dir", "~/Desktop/TheDailyBrief")
    storage_dir = Path(os.path.expanduser(str(storage_dir_str)))

    llm_raw = raw.get("llm", {})
    llm_config = LLMConfig(
        provider=llm_raw.get("provider", "gemini"),
        model=llm_raw.get("model", "gemini-2.0-flash"),
    )

    # 1. First check if user saved dynamic spaces to spaces.json
    spaces: dict[str, SpaceConfig] = {}
    spaces_json_file = output_dir / "spaces.json"
    if spaces_json_file.is_file():
        try:
            with open(spaces_json_file, encoding="utf-8") as sf:
                s_json = json.load(sf)
                if isinstance(s_json, dict):
                    for s_name, s_val in s_json.items():
                        if isinstance(s_val, dict):
                            spaces[s_name] = SpaceConfig.from_dict(s_val)
        except Exception as exc:
            logger.warning("Failed to load spaces.json: %s", exc)

    # 2. If no saved spaces in spaces.json, parse spaces from config.yaml
    if not spaces:
        spaces_raw = raw.get("spaces", {})
        if isinstance(spaces_raw, dict):
            for s_name, s_cfg in spaces_raw.items():
                if isinstance(s_cfg, dict):
                    conns: list[ConnectorInstance] = []
                    # Check if explicit connectors list is defined
                    if "connectors" in s_cfg and isinstance(s_cfg["connectors"], list):
                        for c_item in s_cfg["connectors"]:
                            if isinstance(c_item, dict):
                                conns.append(ConnectorInstance.from_dict(c_item))
                    else:
                        # Convert legacy flat config to connector instances
                        token_env = s_cfg.get(
                            "gmail_token_env",
                            "GMAIL_REFRESH_TOKEN"
                            if s_name == "default"
                            else f"GMAIL_REFRESH_TOKEN_{s_name.upper().replace('-', '_')}",
                        )
                        max_emails = int(s_cfg.get("max_emails", s_cfg.get("gmail_max_emails", 20)))
                        scan_hours = int(s_cfg.get("scan_hours", s_cfg.get("gmail_scan_hours", 12)))
                        audit_days = int(s_cfg.get("audit_days", s_cfg.get("gmail_audit_days", 5)))
                        obs_enabled = bool(s_cfg.get("obsidian_enabled", True))
                        obs_default = ["50 Daily", "10 Projects"]
                        obs_dirs = list(s_cfg.get("obsidian_scan_dirs", obs_default))

                        conns.append(
                            ConnectorInstance(
                                id=f"{s_name}_gmail",
                                type="gmail",
                                name=f"{s_name.capitalize()} Gmail",
                                config={
                                    "token_env": token_env,
                                    "max_emails": max_emails,
                                    "scan_hours": scan_hours,
                                    "audit_days": audit_days,
                                },
                                enabled=True,
                            )
                        )
                        if obs_enabled:
                            conns.append(
                                ConnectorInstance(
                                    id=f"{s_name}_obsidian",
                                    type="obsidian",
                                    name="Obsidian Vault",
                                    config={"scan_dirs": obs_dirs},
                                    enabled=True,
                                )
                            )

                    spaces[s_name] = SpaceConfig(name=s_name, connectors=conns)

    # 3. Fallback to default space if completely empty
    if not spaces:
        spaces["default"] = SpaceConfig(
            name="default",
            connectors=[
                ConnectorInstance(
                    id="default_gmail",
                    type="gmail",
                    name="Default Gmail",
                    config={"token_env": "GMAIL_REFRESH_TOKEN"},
                ),
                ConnectorInstance(
                    id="default_obsidian",
                    type="obsidian",
                    name="Obsidian Vault",
                    config={"scan_dirs": ["50 Daily", "10 Projects"]},
                ),
            ],
        )

    return Config(
        output_dir=output_dir,
        storage_dir=storage_dir,
        brief_language=raw.get("brief_language", "en"),
        llm=llm_config,
        connectors=raw.get("connectors", {}),
        spaces=spaces,
    )


_current_config: Config | None = None


def get_config() -> Config:
    """Get the cached configuration instance or load it."""
    global _current_config
    if _current_config is None:
        _current_config = load_config()
    return _current_config
