# Contributing

Thanks for helping improve tidy-downloads. The tool is intentionally small:
a dependency-free Python 3.9+ command-line program that sorts one folder.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
pytest
```

On Windows, `py -m venv .venv` works the same way. Tests use temporary
directories and do not touch your real Downloads folder.

## What to keep true

- Runtime code stays in the Python standard library. Pytest is a development
  dependency only.
- Support Python 3.9 and newer. Avoid syntax and modules added after 3.9
  (`match`, `tomllib`, `list | tuple` at runtime without
  `from __future__ import annotations`).
- The default action is a dry run. `--apply` is what moves files.
- Never overwrite an existing file. Collisions use the ` (1)`, ` (2)` suffix.
- Hidden files and partial downloads stay put.
- `--undo` only reverts moves recorded in `.tidy-downloads-log.json`.
- Category folders and user-created subfolders are not scanned.
- Behavior should match on Windows, macOS, and Linux. Path handling belongs
  in `pathlib`.

## Tests

Add or update a test in `tests/` for any user-visible change. Prefer a temp
directory over mocks of the filesystem. GitHub Actions runs the suite on
Ubuntu, macOS, and Windows for Python 3.9 and 3.12.

```bash
pytest
tidy-downloads --help
```

## Pull requests

Open a pull request against `main` with a short description of the behavior
change. If you add a category or extension, mention it in the README category
list and in the 中文说明 only when the user-facing rules change.

## Reporting bugs

Please include your operating system, Python version, the command you ran,
and whether you used `--apply` or the default dry run. A small sample of
filenames (not the files themselves) is enough to reproduce most issues.
