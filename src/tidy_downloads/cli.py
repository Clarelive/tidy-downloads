"""Command-line interface for tidy-downloads.

The default is a dry run. Pass ``--apply`` to move files, or ``--undo`` to
reverse the last apply that wrote a log in the target folder.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tidy_downloads import __version__
from tidy_downloads.config import load_config
from tidy_downloads.errors import TidyError
from tidy_downloads.locations import default_downloads_dir
from tidy_downloads.sorter import Plan, UndoAction, apply_plan, build_plan, undo


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code.

    The installed console script passes this return value to ``sys.exit``.
    """
    try:
        return _run(argv)
    except TidyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 1


def _run(argv: list[str] | None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        parser.error("--apply and --dry-run cannot be used together")
    if args.undo and args.apply:
        parser.error("--undo cannot be combined with --apply")

    folder = _resolve_folder(args.path)
    if args.undo:
        actions = undo(folder, dry_run=args.dry_run)
        _print_undo(folder, actions, dry_run=args.dry_run)
        if any(action.status == "failed" for action in actions):
            return 1
        return 0

    config = load_config(folder, explicit=args.config)
    plan = build_plan(folder, config)
    if args.apply:
        completed = apply_plan(plan)
        _print_apply(plan, completed)
        return 0
    _print_dry_run(plan)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tidy-downloads",
        description=(
            "Sort files in a folder into subfolders by file type. "
            "The default is a dry run that only prints the plan."
        ),
        epilog=(
            "examples:\n"
            "  tidy-downloads\n"
            "  tidy-downloads --apply\n"
            "  tidy-downloads --path ~/Desktop --dry-run\n"
            "  tidy-downloads --config ~/tidy-downloads.toml --apply\n"
            "  tidy-downloads --undo\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="folder to tidy (default: your Downloads folder)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="move files into category folders",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan without moving files (this is the default)",
    )
    parser.add_argument(
        "--undo",
        action="store_true",
        help="reverse the last --apply using the log in the folder",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="TOML or JSON file with custom categories and extensions",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _resolve_folder(path: Path | None) -> Path:
    folder = path.expanduser() if path is not None else default_downloads_dir()
    if not folder.exists():
        raise TidyError(f"folder does not exist: {folder}")
    if not folder.is_dir():
        raise TidyError(f"not a folder: {folder}")
    try:
        return folder.resolve()
    except OSError as exc:
        raise TidyError(f"cannot open folder {folder}: {exc}") from exc


def _print_dry_run(plan: Plan) -> None:
    for move in plan.moves:
        print(f"dry-run: {_relative(plan, move.source)} -> {_relative(plan, move.destination)}")
    for skip in plan.skips:
        print(f"skip: {_relative(plan, skip.path)} ({skip.reason})")
    print()
    print(f"Would move {_count(len(plan.moves))}; skipped {_count(len(plan.skips))}.")
    if plan.moves:
        print("Run again with --apply to move these files.")


def _print_apply(plan: Plan, completed: tuple) -> None:
    for move in completed:
        print(f"moved: {_relative(plan, move.source)} -> {_relative(plan, move.destination)}")
    for skip in plan.skips:
        print(f"skip: {_relative(plan, skip.path)} ({skip.reason})")
    print()
    print(f"Moved {_count(len(completed))}; skipped {_count(len(plan.skips))}.")


def _print_undo(folder: Path, actions: tuple[UndoAction, ...], *, dry_run: bool) -> None:
    restored = 0
    for action in actions:
        source_text = _relative_to(folder, action.source)
        if action.status == "missing":
            print(f"missing: {source_text}")
            continue
        destination_text = _relative_to(folder, action.destination) if action.destination else "?"
        if action.status == "preview":
            print(f"undo: {source_text} -> {destination_text}")
            restored += 1
        elif action.status == "restored":
            print(f"restored: {source_text} -> {destination_text}")
            restored += 1
        else:
            detail = f" ({action.detail})" if action.detail else ""
            print(f"failed: {source_text}{detail}")
    print()
    if dry_run:
        print(f"Would restore {_count(restored)}.")
        if restored:
            print("Run again with --undo to restore these files.")
        return
    failed = sum(1 for action in actions if action.status == "failed")
    print(f"Restored {_count(restored)}; failed {_count(failed)}.")


def _relative(plan: Plan, path: Path) -> str:
    return _relative_to(plan.folder, path)


def _relative_to(folder: Path, path: Path) -> str:
    try:
        return path.relative_to(folder).as_posix()
    except ValueError:
        return path.name


def _count(amount: int) -> str:
    noun = "file" if amount == 1 else "files"
    return f"{amount} {noun}"
