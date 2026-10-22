"""Load built-in categories and optional TOML or JSON user config.

Search order when ``--config`` is not passed:

1. ``TIDY_DOWNLOADS_CONFIG`` (error if that path is missing)
2. ``tidy-downloads.toml`` then ``tidy-downloads.json`` in the target folder
3. ``$XDG_CONFIG_HOME/tidy-downloads/config.toml`` (or ``~/.config/...``)
4. the same directory's ``config.json``
5. ``%APPDATA%/tidy-downloads/config.toml`` and ``config.json`` on Windows
6. ``~/.tidy-downloads.toml`` then ``~/.tidy-downloads.json``

The first file that exists wins. Listed extensions are reassigned to the
user's category. Set ``replace_categories = true`` to ignore the built-in
categories entirely. When ``skip_extensions`` is present it replaces the
built-in partial-download list.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from tidy_downloads.categories import (
    DEFAULT_CATEGORIES,
    DEFAULT_SKIP_EXTENSIONS,
    OTHERS_NAME,
)
from tidy_downloads.errors import ConfigError
from tidy_downloads.toml_subset import parse_toml_subset

_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL"}
_WIN_RESERVED.update(f"COM{i}" for i in range(1, 10))
_WIN_RESERVED.update(f"LPT{i}" for i in range(1, 10))


@dataclass(frozen=True)
class AppConfig:
    """Resolved categories used by the sorter."""

    categories: dict[str, tuple[str, ...]]
    ranked: tuple[tuple[str, str], ...]
    skip_extensions: frozenset[str]
    others_name: str
    source: str

    def category_for(self, filename: str) -> str:
        """Return the category for ``filename`` using the longest extension."""
        lowered = filename.lower()
        for extension, category in self.ranked:
            if lowered.endswith("." + extension):
                return category
        return self.others_name

    def is_partial(self, filename: str) -> bool:
        lowered = filename.lower()
        return any(lowered.endswith("." + extension) for extension in self.skip_extensions)


def default_config() -> AppConfig:
    return build_config({}, source="defaults")


def load_config(folder: Path, explicit: Path | None = None) -> AppConfig:
    """Load config for ``folder``, or the built-in defaults."""
    if explicit is not None:
        path = explicit.expanduser()
        if not path.is_file():
            raise ConfigError(f"config file not found: {path}")
        return load_config_file(path)

    env_path = os.environ.get("TIDY_DOWNLOADS_CONFIG")
    if env_path:
        path = Path(env_path).expanduser()
        if not path.is_file():
            raise ConfigError(f"config file not found: {path}")
        return load_config_file(path)

    for candidate in config_candidates(folder):
        if candidate.is_file():
            return load_config_file(candidate)
    return default_config()


def config_candidates(folder: Path) -> list[Path]:
    """Return config paths in search order, excluding the env override."""
    paths = [folder / "tidy-downloads.toml", folder / "tidy-downloads.json"]
    if os.environ.get("XDG_CONFIG_HOME"):
        base = Path(os.environ["XDG_CONFIG_HOME"]).expanduser()
    else:
        base = Path.home() / ".config"
    paths.append(base / "tidy-downloads" / "config.toml")
    paths.append(base / "tidy-downloads" / "config.json")
    appdata = os.environ.get("APPDATA")
    if appdata:
        windows_base = Path(appdata).expanduser() / "tidy-downloads"
        paths.append(windows_base / "config.toml")
        paths.append(windows_base / "config.json")
    paths.append(Path.home() / ".tidy-downloads.toml")
    paths.append(Path.home() / ".tidy-downloads.json")
    return paths


def load_config_file(path: Path) -> AppConfig:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ConfigError(f"could not read config {path}: {exc}") from exc
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"{path}: {exc}") from exc
    elif suffix == ".toml":
        try:
            data = parse_toml_subset(text)
        except ConfigError as exc:
            raise ConfigError(f"{path}: {exc}") from exc
    else:
        raise ConfigError(f"config file must end in .toml or .json: {path}")
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: config must be a table or object")
    try:
        return build_config(data, source=str(path))
    except ConfigError as exc:
        raise ConfigError(f"{path}: {exc}") from exc


def build_config(data: dict, source: str = "config") -> AppConfig:
    """Merge ``data`` onto the built-in categories."""
    replace = data.get("replace_categories", False)
    if not isinstance(replace, bool):
        raise ConfigError("replace_categories must be true or false")

    others = data.get("others", OTHERS_NAME)
    if not isinstance(others, str):
        raise ConfigError("others must be a string")
    others_name = validate_category_name(others)

    if "skip_extensions" in data and data["skip_extensions"] is not None:
        skip = frozenset(normalize_extensions(data["skip_extensions"], where="skip_extensions"))
    else:
        skip = frozenset(DEFAULT_SKIP_EXTENSIONS)

    categories: dict[str, list[str]] = {}
    if not replace:
        for name, extensions in DEFAULT_CATEGORIES.items():
            categories[name] = list(extensions)

    user_categories = data.get("categories", {})
    if user_categories is None:
        user_categories = {}
    if not isinstance(user_categories, dict):
        raise ConfigError("categories must be a table or object of extension lists")

    for raw_name, raw_extensions in user_categories.items():
        name = validate_category_name(str(raw_name))
        extensions = normalize_extensions(raw_extensions, where=f"categories.{name}")
        stolen = set(extensions)
        for existing_name, existing in list(categories.items()):
            if existing_name == name:
                continue
            categories[existing_name] = [item for item in existing if item not in stolen]
        categories[name] = extensions

    compact = {name: tuple(extensions) for name, extensions in categories.items() if extensions}
    extension_map: dict[str, str] = {}
    for name, extensions in compact.items():
        for extension in extensions:
            extension_map[extension] = name
    ranked = tuple(sorted(extension_map.items(), key=lambda item: (len(item[0]), item[0]), reverse=True))
    return AppConfig(
        categories=compact,
        ranked=ranked,
        skip_extensions=skip,
        others_name=others_name,
        source=source,
    )


def normalize_extensions(value: object, *, where: str) -> list[str]:
    if not isinstance(value, list):
        raise ConfigError(f"{where} must be a list of extensions")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        extension = normalize_extension(item, where=where)
        if extension not in seen:
            seen.add(extension)
            normalized.append(extension)
    return normalized


def normalize_extension(value: object, *, where: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{where}: each extension must be a string")
    extension = value.strip().lower().lstrip(".")
    if not extension or extension in {".", ".."}:
        raise ConfigError(f"{where}: invalid extension {value!r}")
    if any(separator in extension for separator in ("/", "\\", "\x00")) or any(
        character.isspace() for character in extension
    ):
        raise ConfigError(f"{where}: invalid extension {value!r}")
    return extension


def validate_category_name(name: str) -> str:
    if not isinstance(name, str):
        raise ConfigError("category name must be a string")
    cleaned = name.strip()
    if not cleaned:
        raise ConfigError("category name cannot be empty")
    if cleaned in {".", ".."} or cleaned.endswith("."):
        raise ConfigError(f"invalid category name {name!r}")
    if any(separator in cleaned for separator in ("/", "\\", "\x00")):
        raise ConfigError(f"invalid category name {name!r}")
    reserved = cleaned.split(".", 1)[0].upper()
    if reserved in _WIN_RESERVED:
        raise ConfigError(f"category name {cleaned!r} is reserved on Windows")
    return cleaned
