"""Command-line behavior against temporary folders."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tidy_downloads import __version__
from tidy_downloads.cli import main
from tidy_downloads.sorter import LOG_FILENAME

ROOT = Path(__file__).resolve().parents[1]


def test_module_help():
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-m", "tidy_downloads", "--help"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert "dry run" in result.stdout.lower()


def test_help_and_version(capsys):
    assert main(["--help"]) == 0
    assert "dry run" in capsys.readouterr().out.lower()
    assert main(["--version"]) == 0
    assert f"tidy-downloads {__version__}" in capsys.readouterr().out


def test_rejects_bad_flags(box, capsys):
    assert main(["--not-a-flag"]) == 2
    assert main(["--path", str(box), "--apply", "--dry-run"]) == 2
    assert main(["--path", str(box), "--undo", "--apply"]) == 2
    assert capsys.readouterr().err


def test_missing_folder_and_file_path(box, capsys):
    assert main(["--path", str(box / "missing")]) == 1
    target = box / "file.txt"
    target.write_text("x", encoding="utf-8")
    assert main(["--path", str(target)]) == 1
    assert "not a folder" in capsys.readouterr().err


def test_default_downloads_folder(capsys):
    assert main([]) == 1
    assert "does not exist" in capsys.readouterr().err
    downloads = Path.home() / "Downloads"
    downloads.mkdir()
    (downloads / "a.jpg").write_bytes(b"x")
    assert main([]) == 0
    assert (downloads / "a.jpg").is_file()
    assert "dry-run: a.jpg -> Images/a.jpg" in capsys.readouterr().out


def test_dry_run_changes_nothing(box, capsys):
    (box / "vacation.jpg").write_bytes(b"x")
    (box / "subdir").mkdir()
    assert main(["--path", str(box), "--dry-run"]) == 0
    assert (box / "vacation.jpg").is_file()
    assert not (box / "Images").exists()
    assert not (box / LOG_FILENAME).exists()
    output = capsys.readouterr().out
    assert "dry-run: vacation.jpg -> Images/vacation.jpg" in output
    assert "Would move 1 file" in output
    assert "subdir" not in output
    assert "--apply" in output


def test_apply_sorts_each_built_in_category(box, capsys):
    files = {
        "vacation.jpg": "Images",
        "report.pdf": "Documents",
        "backup.tar.gz": "Archives",
        "song.mp3": "Audio",
        "clip.mp4": "Video",
        "main.py": "Code",
        "setup.dmg": "Installers",
        "README": "Others",
        "data.xyz": "Others",
        "photo.JPG": "Images",
        "my report.pdf": "Documents",
        "movie.ts": "Video",
    }
    for name in files:
        (box / name).write_text(name, encoding="utf-8")
    (box / "简历.txt").write_text("你好", encoding="utf-8")
    assert main(["--path", str(box), "--apply"]) == 0
    for name, category in files.items():
        assert (box / category / name).read_text(encoding="utf-8") == name
        assert not (box / name).exists()
    assert (box / "Documents" / "简历.txt").read_text(encoding="utf-8") == "你好"
    output = capsys.readouterr().out
    assert "moved: vacation.jpg -> Images/vacation.jpg" in output
    assert "Moved " in output
    log = json.loads((box / LOG_FILENAME).read_text(encoding="utf-8"))
    assert log["version"] == 1
    assert log["tool"] == "tidy-downloads"
    assert {"from": "vacation.jpg", "to": "Images/vacation.jpg"} in log["moves"]
    assert all("/" in entry["to"] or entry["to"].count("\\") == 0 for entry in log["moves"])
    assert "\\" not in (box / LOG_FILENAME).read_text(encoding="utf-8")


def test_skips_hidden_partial_and_does_not_recurse(box, capsys):
    (box / ".secret.png").write_bytes(b"x")
    (box / "movie.mp4.part").write_bytes(b"x")
    (box / "doc.crdownload").write_bytes(b"x")
    (box / "note.tmp").write_bytes(b"x")
    (box / "file.TMP").write_bytes(b"x")
    (box / "keep.tmp.txt").write_text("kept", encoding="utf-8")
    (box / "sub").mkdir()
    (box / "sub" / "hidden-nest.jpg").write_bytes(b"x")
    assert main(["--path", str(box), "--apply"]) == 0
    for name in (".secret.png", "movie.mp4.part", "doc.crdownload", "note.tmp", "file.TMP"):
        assert (box / name).is_file()
    assert (box / "Documents" / "keep.tmp.txt").read_text(encoding="utf-8") == "kept"
    assert (box / "sub" / "hidden-nest.jpg").is_file()
    output = capsys.readouterr().out
    assert "skip: .secret.png (hidden)" in output
    assert "skip: movie.mp4.part (partial download)" in output


def test_never_overwrites_and_continues_numbering(box):
    (box / "Images").mkdir()
    (box / "Images" / "a.jpg").write_text("old", encoding="utf-8")
    (box / "Images" / "a (1).jpg").write_text("older", encoding="utf-8")
    (box / "a.jpg").write_text("new", encoding="utf-8")
    (box / "a (1).jpg").write_text("also new", encoding="utf-8")
    assert main(["--path", str(box), "--apply"]) == 0
    assert (box / "Images" / "a.jpg").read_text(encoding="utf-8") == "old"
    assert (box / "Images" / "a (1).jpg").read_text(encoding="utf-8") == "older"
    assert (box / "Images" / "a (2).jpg").read_text(encoding="utf-8") == "also new"
    assert (box / "Images" / "a (3).jpg").read_text(encoding="utf-8") == "new"


def test_category_path_blocked_by_a_file(box, capsys):
    (box / "Images").write_text("not a directory", encoding="utf-8")
    (box / "a.jpg").write_text("x", encoding="utf-8")
    assert main(["--path", str(box), "--apply"]) == 1
    assert (box / "a.jpg").is_file()
    assert "error:" in capsys.readouterr().err


def test_undo_round_trip_and_preview(box, capsys):
    (box / "a.jpg").write_text("pic", encoding="utf-8")
    (box / "b.pdf").write_text("doc", encoding="utf-8")
    assert main(["--path", str(box), "--apply"]) == 0
    assert main(["--path", str(box), "--undo", "--dry-run"]) == 0
    preview = capsys.readouterr().out
    assert "undo: Images/a.jpg -> a.jpg" in preview
    assert (box / "Images" / "a.jpg").is_file()
    assert (box / LOG_FILENAME).is_file()
    assert main(["--path", str(box), "--undo"]) == 0
    assert (box / "a.jpg").read_text(encoding="utf-8") == "pic"
    assert (box / "b.pdf").read_text(encoding="utf-8") == "doc"
    assert not (box / "Images").exists()
    assert not (box / "Documents").exists()
    assert not (box / LOG_FILENAME).exists()
    assert "restored: Images/a.jpg -> a.jpg" in capsys.readouterr().out


def test_undo_does_not_overwrite_and_keeps_extra_files(box):
    (box / "a.jpg").write_text("original", encoding="utf-8")
    assert main(["--path", str(box), "--apply"]) == 0
    (box / "a.jpg").write_text("newer", encoding="utf-8")
    (box / "Images" / "keep.txt").write_text("stay", encoding="utf-8")
    assert main(["--path", str(box), "--undo"]) == 0
    assert (box / "a.jpg").read_text(encoding="utf-8") == "newer"
    assert (box / "a (1).jpg").read_text(encoding="utf-8") == "original"
    assert (box / "Images" / "keep.txt").read_text(encoding="utf-8") == "stay"
    assert not (box / "Images" / "a.jpg").exists()


def test_second_apply_log_and_empty_apply_preserves_it(box):
    (box / "a.jpg").write_text("a", encoding="utf-8")
    assert main(["--path", str(box), "--apply"]) == 0
    assert main(["--path", str(box), "--apply"]) == 0
    assert main(["--path", str(box), "--undo"]) == 0
    assert (box / "a.jpg").read_text(encoding="utf-8") == "a"

    assert main(["--path", str(box), "--apply"]) == 0
    (box / "b.pdf").write_text("b", encoding="utf-8")
    assert main(["--path", str(box), "--apply"]) == 0
    assert main(["--path", str(box), "--undo"]) == 0
    assert (box / "b.pdf").read_text(encoding="utf-8") == "b"
    assert (box / "Images" / "a.jpg").read_text(encoding="utf-8") == "a"


def test_undo_without_log_and_missing_file(box, capsys):
    assert main(["--path", str(box), "--undo"]) == 1
    assert "undo log" in capsys.readouterr().err
    (box / "a.jpg").write_text("a", encoding="utf-8")
    assert main(["--path", str(box), "--apply"]) == 0
    (box / "Images" / "a.jpg").unlink()
    assert main(["--path", str(box), "--undo"]) == 0
    assert "missing: Images/a.jpg" in capsys.readouterr().out
    assert not (box / LOG_FILENAME).exists()


def test_undo_rejects_bad_log(box, capsys):
    (box / LOG_FILENAME).write_text('{"version": 99, "moves": []}', encoding="utf-8")
    assert main(["--path", str(box), "--undo"]) == 1
    assert "error:" in capsys.readouterr().err


def test_folder_config_customizes_and_is_not_moved(box, capsys):
    (box / "tidy-downloads.toml").write_text(
        '[categories]\nEbooks = ["epub"]\n',
        encoding="utf-8",
    )
    (box / "book.epub").write_bytes(b"x")
    (box / "photo.jpg").write_bytes(b"x")
    assert main(["--path", str(box), "--apply"]) == 0
    assert (box / "tidy-downloads.toml").is_file()
    assert (box / "Ebooks" / "book.epub").is_file()
    assert (box / "Images" / "photo.jpg").is_file()
    assert "config file" in capsys.readouterr().out


def test_explicit_config_replaces_categories(box, tmp_path):
    config = tmp_path / "only.json"
    config.write_text(
        json.dumps(
            {
                "replace_categories": True,
                "others": "Misc",
                "categories": {"Ebooks": ["epub"]},
            }
        ),
        encoding="utf-8",
    )
    (box / "book.epub").write_bytes(b"x")
    (box / "photo.jpg").write_bytes(b"x")
    assert main(["--path", str(box), "--config", str(config), "--apply"]) == 0
    assert (box / "Ebooks" / "book.epub").is_file()
    assert (box / "Misc" / "photo.jpg").is_file()


def test_missing_config_file(box, capsys, tmp_path):
    assert main(["--path", str(box), "--config", str(tmp_path / "nope.toml")]) == 1
    assert "config file not found" in capsys.readouterr().err


def test_file_symlink_is_moved_directory_symlink_stays(box, tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("data", encoding="utf-8")
    try:
        (box / "link.txt").symlink_to(target)
        (box / "real").mkdir()
        (box / "real" / "a.jpg").write_text("x", encoding="utf-8")
        (box / "linkdir").symlink_to(box / "real", target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are not permitted")
    assert main(["--path", str(box), "--apply"]) == 0
    moved = box / "Documents" / "link.txt"
    assert moved.is_symlink()
    assert moved.read_text(encoding="utf-8") == "data"
    assert target.read_text(encoding="utf-8") == "data"
    assert (box / "linkdir").is_symlink()
    assert (box / "real" / "a.jpg").is_file()


def test_log_is_hidden_from_later_plans(box, capsys):
    (box / "a.jpg").write_bytes(b"x")
    assert main(["--path", str(box), "--apply"]) == 0
    assert main(["--path", str(box)]) == 0
    output = capsys.readouterr().out
    assert LOG_FILENAME not in output
    assert "Would move 0 files" in output
