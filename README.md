# tidy-downloads

[![Tests](https://github.com/Clarelive/tidy-downloads/actions/workflows/tests.yml/badge.svg)](https://github.com/Clarelive/tidy-downloads/actions/workflows/tests.yml)

`tidy-downloads` sorts a messy folder into subfolders by file type. It is a
small command-line tool for Python 3.9 and newer, with no third-party
runtime dependencies, and it works on Windows, macOS, and Linux.

The default is a **dry run**: it prints the plan and does not move anything.
Add `--apply` when the plan looks right.

```text
$ tidy-downloads --path ~/Downloads
dry-run: vacation.jpg -> Images/vacation.jpg
dry-run: report.pdf -> Documents/report.pdf
dry-run: setup.dmg -> Installers/setup.dmg
skip: .DS_Store (hidden)
skip: movie.mp4.part (partial download)

Would move 3 files; skipped 2.
Run again with --apply to move these files.
```

## Install

From a checkout:

```bash
pip install .
tidy-downloads --help
```

With [pipx](https://pipx.pypa.io/), from GitHub:

```bash
pipx install git+https://github.com/Clarelive/tidy-downloads
```

Python 3.9 or newer is required. The install does not pull in runtime
libraries.

## Usage

```bash
# Preview your Downloads folder (nothing is moved).
tidy-downloads

# Move files into category folders.
tidy-downloads --apply

# Preview or tidy a different folder.
tidy-downloads --path ~/Desktop
tidy-downloads --path ~/Desktop --apply

# Use a config file.
tidy-downloads --config ~/tidy-downloads.toml --apply

# Put back the files moved by the last apply.
tidy-downloads --undo

# Preview the undo without moving anything.
tidy-downloads --undo --dry-run
```

| Flag | Effect |
| --- | --- |
| *(none)* | Dry run. Print what would move. |
| `--dry-run` | Same as the default. Cannot be combined with `--apply`. |
| `--apply` | Move files and write the undo log. |
| `--path DIR` | Folder to tidy. Defaults to your Downloads folder. |
| `--config FILE` | TOML or JSON config. `.toml` and `.json` are both accepted. |
| `--undo` | Reverse the last `--apply` recorded in this folder. |
| `--version` | Print the version. |

Exit codes: `0` success, `1` a problem with the folder, config, or undo log,
`2` invalid command-line flags.

## Categories

Only **files in the top level** of the folder are moved. Subfolders, including
ones created by an earlier run, are left alone, so running the tool twice does
not reshuffle files that are already sorted.

| Folder | Examples |
| --- | --- |
| `Images` | jpg, png, gif, webp, heic, svg |
| `Documents` | pdf, docx, xlsx, pptx, txt, csv, md, epub |
| `Archives` | zip, rar, 7z, tar, gz, iso |
| `Audio` | mp3, wav, flac, m4a, ogg |
| `Video` | mp4, mkv, mov, webm, avi |
| `Code` | py, js, html, css, json, sh |
| `Installers` | exe, msi, dmg, pkg, deb, rpm, appimage |
| `Others` | anything that does not match |

`.ts` is treated as **Video** (transport streams show up in Downloads more
often than TypeScript). Remap it in a config file if you want it under `Code`.

Matching uses the longest extension, so `notes.final.pdf` is a document and
`backup.tar.gz` is an archive.

## Safety rules

- Existing files are never overwritten. If `Images/photo.jpg` is already
  there, the next `photo.jpg` becomes `Images/photo (1).jpg`, then
  `photo (2).jpg`, and so on.
- Hidden files are skipped. A name that starts with `.` is hidden on every
  platform. On Windows, files with the hidden attribute are skipped too.
- Partial downloads are skipped: `.crdownload`, `.part`, and `.tmp`.
- A `tidy-downloads.toml` or `tidy-downloads.json` file inside the folder is
  left in place so your config stays put.
- The undo log `.tidy-downloads-log.json` is written in the folder you tidy.
  It records only the latest `--apply` that actually moved files. An apply
  that has nothing to do leaves the previous log alone. `--undo` reads that
  log, moves files back (again without overwriting), deletes the log, and
  removes category folders that are empty afterwards.
- Paths inside the log are relative. A log entry that points outside the
  folder is rejected.

## Config

You can customize categories and extensions with TOML or JSON. The first file
found wins:

1. `--config PATH`
2. The `TIDY_DOWNLOADS_CONFIG` environment variable
3. `tidy-downloads.toml` or `tidy-downloads.json` in the folder being tidied
4. `$XDG_CONFIG_HOME/tidy-downloads/config.toml` (or `~/.config/tidy-downloads/`)
5. `%APPDATA%\tidy-downloads\config.toml` when `APPDATA` is set
6. `~/.tidy-downloads.toml` or `~/.tidy-downloads.json`

Copy [`examples/tidy-downloads.toml`](examples/tidy-downloads.toml) or
[`examples/tidy-downloads.json`](examples/tidy-downloads.json) as a start.

```toml
replace_categories = false
skip_extensions = ["crdownload", "part", "tmp", "download"]
others = "Others"

[categories]
Ebooks = ["epub", "mobi", "azw3"]
```

```json
{
  "replace_categories": false,
  "skip_extensions": ["crdownload", "part", "tmp", "download"],
  "others": "Others",
  "categories": {
    "Ebooks": ["epub", "mobi", "azw3"]
  }
}
```

- Listed extensions are taken from their previous category and assigned to
  yours. Later categories in the file win if you list an extension twice.
- `replace_categories = true` drops the built-in lists. Unknown extensions
  still go to the fallback folder (`others`, default `Others`).
- `skip_extensions`, when present, **replaces** the built-in partial-download
  list. Include `crdownload`, `part`, and `tmp` if you still want those skipped.
- An empty list removes a built-in category (`Images = []` sends pictures to
  the fallback folder).
- The TOML reader accepts comments, `"strings"`, `'strings'`, `true`/`false`,
  numbers, arrays (including multi-line arrays), and `[tables]`. Multiline
  strings, inline tables, and dates are not supported. JSON configs use
  normal JSON.

Category names become folder names, so they cannot contain slashes or Windows
reserved names such as `CON`.

## Downloads folder

With no `--path`, the tool looks up your Downloads directory:

- **Windows:** the Downloads Known Folder, then `~/Downloads`
- **macOS and Linux:** `XDG_DOWNLOAD_DIR` in `user-dirs.dirs`, then `~/Downloads`

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

GitHub Actions runs the tests on Ubuntu, macOS, and Windows. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## 中文说明

`tidy-downloads` 是一个不依赖第三方库的命令行工具，用来把混乱的文件夹（默认是「下载」文件夹）按文件类型归类。支持 Windows、macOS 和 Linux，需要 Python 3.9 或更高版本。

默认只预览、不移动文件。确认预览无误后再加 `--apply`。

```bash
pipx install git+https://github.com/Clarelive/tidy-downloads

tidy-downloads
tidy-downloads --apply
tidy-downloads --path ~/Desktop --apply
tidy-downloads --config ~/tidy-downloads.toml --apply
tidy-downloads --undo
```

规则：

- 按扩展名放入 `Images`、`Documents`、`Archives`、`Audio`、`Video`、`Code`、`Installers`，其余进入 `Others`。
- 只整理目标文件夹的第一层，不会进入子文件夹，因此重复运行不会打乱已经归类的文件。
- 不覆盖同名文件。冲突时在扩展名前加上 ` (1)`、` (2)`。
- 跳过隐藏文件，以及未下完的文件（`.crdownload`、`.part`、`.tmp`）。
- `--undo` 根据目标文件夹里的 `.tidy-downloads-log.json` 撤销最近一次真正移动了文件的 `--apply`。
- 可以用 TOML 或 JSON 自定义分类和扩展名，示例见上文，也可以直接复制 `examples/` 里的文件。

## License

[MIT](LICENSE)
