"""Plan, apply, and undo file moves for one folder.

Only the top level of the folder is organized. Subfolders, including the
category folders created by an earlier run, are left in place. The undo log
records the latest ``--apply`` that actually moved something.
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tidy_downloads.config import AppConfig
from tidy_downloads.errors import TidyError, UndoError

LOG_FILENAME = ".tidy-downloads-log.json"
LOG_VERSION = 1
_SILENT_NAMES = {LOG_FILENAME, LOG_FILENAME + ".tmp"}
_CONFIG_NAMES = {"tidy-downloads.toml", "tidy-downloads.json"}
_NUMBERED_NAME = re.compile(r"^(?P<base>.*) \((?P<num>[0-9]{1,6})\)$")
_MAX_COLLISIONS = 10000


@dataclass(frozen=True)
class PlannedMove:
    source: Path
    destination: Path


@dataclass(frozen=True)
class PlannedSkip:
    path: Path
    reason: str


@dataclass(frozen=True)
class Plan:
    folder: Path
    moves: tuple[PlannedMove, ...]
    skips: tuple[PlannedSkip, ...]


@dataclass(frozen=True)
class UndoAction:
    source: Path
    destination: Path | None
    status: str
    detail: str = ""


def log_path(folder: Path) -> Path:
    return folder / LOG_FILENAME


def build_plan(folder: Path, config: AppConfig) -> Plan:
    """Describe moves and skips without touching the filesystem."""
    folder = folder.resolve()
    case_insensitive = filesystem_is_case_insensitive()
    reserved: set[str] = set()
    moves: list[PlannedMove] = []
    skips: list[PlannedSkip] = []
    try:
        entries = sorted(folder.iterdir(), key=lambda entry: entry.name.casefold())
    except OSError as exc:
        raise TidyError(f"cannot read folder {folder}: {exc}") from exc

    for entry in entries:
        if entry.name in _SILENT_NAMES:
            continue
        if not _is_movable(entry):
            # Directories (and links to directories) stay where they are.
            # Other special files are reported so they are not silently lost.
            if entry.is_dir():
                continue
            skips.append(PlannedSkip(entry, "not a regular file"))
            continue
        if entry.name in _CONFIG_NAMES:
            skips.append(PlannedSkip(entry, "config file"))
            continue
        if is_hidden(entry):
            skips.append(PlannedSkip(entry, "hidden"))
            continue
        if config.is_partial(entry.name):
            skips.append(PlannedSkip(entry, "partial download"))
            continue
        category = config.category_for(entry.name)
        destination = unique_destination(
            folder / category,
            entry.name,
            reserved,
            case_insensitive,
        )
        moves.append(PlannedMove(entry, destination))
    return Plan(folder=folder, moves=tuple(moves), skips=tuple(skips))


def apply_plan(plan: Plan) -> tuple[PlannedMove, ...]:
    """Move planned files and write the undo log.

    Destinations are chosen again at move time so a file that appears between
    the preview and ``--apply`` is not overwritten. An apply that moves
    nothing keeps the previous log, so undo still reverts the last real run.
    """
    folder = plan.folder
    case_insensitive = filesystem_is_case_insensitive()
    reserved: set[str] = set()
    completed: list[PlannedMove] = []
    current_name = folder.name
    try:
        for planned in plan.moves:
            current_name = planned.source.name
            if not planned.source.exists() and not planned.source.is_symlink():
                continue
            destination = unique_destination(
                planned.destination.parent,
                planned.destination.name,
                reserved,
                case_insensitive,
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise TidyError(f"refusing to overwrite {destination}")
            planned.source.rename(destination)
            completed.append(PlannedMove(planned.source, destination))
    except TidyError:
        if completed:
            write_log(folder, completed)
        raise
    except OSError as exc:
        if completed:
            write_log(folder, completed)
            raise TidyError(
                f"failed while moving {current_name}: {exc}. "
                "Files already moved were recorded; run --undo to put them back."
            ) from exc
        raise TidyError(f"failed while moving {current_name}: {exc}") from exc
    if completed:
        write_log(folder, completed)
    return tuple(completed)


def undo(folder: Path, *, dry_run: bool) -> tuple[UndoAction, ...]:
    """Reverse the moves recorded in the folder's undo log."""
    folder = folder.resolve()
    entries = read_log(folder)
    # Resolve every logged path before moving so a bad entry cannot leave
    # the folder half-restored.
    located = [
        (entry, _join_logged(folder, entry["to"]), _join_logged(folder, entry["from"]))
        for entry in entries
    ]
    case_insensitive = filesystem_is_case_insensitive()
    reserved: set[str] = set()
    actions: list[UndoAction] = []
    failed: list[tuple[int, dict[str, str]]] = []

    for index, (entry, current, original) in reversed(list(enumerate(located))):
        if not current.exists() and not current.is_symlink():
            actions.append(UndoAction(current, None, "missing"))
            continue
        destination = unique_destination(
            original.parent,
            original.name,
            reserved,
            case_insensitive,
        )
        if dry_run:
            actions.append(UndoAction(current, destination, "preview"))
            continue
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise TidyError(f"refusing to overwrite {destination}")
            current.rename(destination)
        except (OSError, TidyError) as exc:
            failed.append((index, entry))
            actions.append(UndoAction(current, destination, "failed", str(exc)))
            continue
        actions.append(UndoAction(current, destination, "restored"))
        _remove_empty_parents(current, folder)

    if not dry_run:
        if failed:
            failed.sort(key=lambda item: item[0])
            _write_raw_log(folder, [entry for _, entry in failed])
        else:
            try:
                log_path(folder).unlink()
            except OSError as exc:
                raise UndoError(f"could not remove undo log: {exc}") from exc
    return tuple(actions)


def write_log(folder: Path, moves: list[PlannedMove] | tuple[PlannedMove, ...]) -> None:
    payload_moves = []
    for move in moves:
        payload_moves.append(
            {
                "from": move.source.relative_to(folder).as_posix(),
                "to": move.destination.relative_to(folder).as_posix(),
            }
        )
    _write_raw_log(folder, payload_moves)


def read_log(folder: Path) -> list[dict[str, str]]:
    path = log_path(folder)
    if not path.is_file():
        raise UndoError(
            f"no undo log in {folder}. "
            f"Run with --apply first; the log is {LOG_FILENAME}."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise UndoError(f"could not read undo log {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise UndoError(f"undo log is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != LOG_VERSION:
        raise UndoError("unsupported undo log version")
    moves = data.get("moves")
    if not isinstance(moves, list):
        raise UndoError("undo log is missing a moves list")
    checked: list[dict[str, str]] = []
    for entry in moves:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("from"), str)
            or not isinstance(entry.get("to"), str)
        ):
            raise UndoError("undo log contains an invalid move")
        _safe_relative(entry["from"])
        _safe_relative(entry["to"])
        checked.append({"from": entry["from"], "to": entry["to"]})
    return checked


def unique_destination(
    directory: Path,
    filename: str,
    reserved: set[str],
    case_insensitive: bool,
) -> Path:
    """Return a path that does not collide with a file or an earlier choice.

    Taken names grow a `` (1)``, `` (2)``, ... suffix before the last
    extension. A file that is already numbered continues at the next number
    instead of becoming ``name (1) (1)``.
    """
    for index, name in enumerate(_candidate_names(filename)):
        if index > _MAX_COLLISIONS:
            break
        candidate = directory / name
        key = _fs_key(candidate, case_insensitive)
        if key in reserved or candidate.exists():
            continue
        reserved.add(key)
        return candidate
    raise TidyError(f"could not find a free name for {filename} in {directory}")


def is_hidden(path: Path) -> bool:
    """Return True for dotfiles and, on Windows, the hidden attribute."""
    if path.name.startswith("."):
        return True
    if os.name != "nt":
        return False
    try:
        attributes = path.stat().st_file_attributes  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return False
    hidden = getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0x2)
    return bool(attributes & hidden)


def filesystem_is_case_insensitive() -> bool:
    """Guess collision rules for the platform.

    macOS and Windows are case-insensitive by default. A case-sensitive
    volume on those systems is uncommon; Linux is treated as case-sensitive.
    """
    return os.name == "nt" or sys.platform == "darwin"


def _candidate_names(filename: str):
    path = Path(filename)
    suffix = path.suffix
    stem = path.stem
    match = _NUMBERED_NAME.fullmatch(stem)
    yield filename
    if match and match.group("base"):
        base = match.group("base")
        number = int(match.group("num")) + 1
    else:
        base = stem
        number = 1
    while True:
        yield f"{base} ({number}){suffix}"
        number += 1


def _is_movable(entry: Path) -> bool:
    if entry.is_symlink():
        # Move the link itself. Links to directories are left alone.
        return not entry.is_dir()
    return entry.is_file()


def _fs_key(path: Path, case_insensitive: bool) -> str:
    text = str(path)
    return text.casefold() if case_insensitive else text


def _safe_relative(value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise UndoError("undo log contains an empty path")
    normalized = value.replace("\\", "/")
    if normalized.startswith("/"):
        raise UndoError(f"undo log path escapes the folder: {value}")
    relative = Path(normalized)
    # Reject absolute paths, empty paths, parent segments, and drive-relative
    # parts (``C:name``) so a tampered log cannot leave the folder.
    if relative.is_absolute() or not relative.parts:
        raise UndoError(f"undo log path escapes the folder: {value}")
    for part in relative.parts:
        if part in {".", ".."} or ":" in part or "\x00" in part:
            raise UndoError(f"undo log path escapes the folder: {value}")
    return relative


def _join_logged(folder: Path, value: str) -> Path:
    relative = _safe_relative(value)
    candidate = folder.joinpath(*relative.parts)
    _ensure_inside(folder, candidate)
    return candidate


def _ensure_inside(folder: Path, candidate: Path) -> None:
    folder_resolved = folder.resolve()
    try:
        resolved = candidate.resolve()
    except OSError as exc:
        raise UndoError(f"undo log path escapes the folder: {candidate}") from exc
    if resolved != folder_resolved and folder_resolved not in resolved.parents:
        raise UndoError(f"undo log path escapes the folder: {candidate}")


def _write_raw_log(folder: Path, moves: list[dict[str, str]]) -> None:
    payload = {
        "version": LOG_VERSION,
        "tool": "tidy-downloads",
        "created_at": _timestamp(),
        "moves": moves,
    }
    destination = log_path(folder)
    temporary = destination.with_name(destination.name + ".tmp")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    try:
        temporary.write_text(text, encoding="utf-8")
        _hide_file(temporary)
        temporary.replace(destination)
        _hide_file(destination)
    except OSError as exc:
        raise TidyError(f"could not write undo log {destination}: {exc}") from exc


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hide_file(path: Path) -> None:
    """Set the Windows hidden attribute. Dotfiles are already hidden elsewhere."""
    if os.name != "nt":
        return
    try:
        import ctypes

        get_attributes = ctypes.windll.kernel32.GetFileAttributesW
        set_attributes = ctypes.windll.kernel32.SetFileAttributesW
        current = get_attributes(str(path))
        if current == 0xFFFFFFFF:
            return
        set_attributes(str(path), current | 0x2)
    except (AttributeError, OSError, ValueError):
        return


def _remove_empty_parents(removed_file: Path, root: Path) -> None:
    current = removed_file.parent
    while current != root:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
