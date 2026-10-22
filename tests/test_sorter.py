"""Move planning, collisions, and undo safety."""

import json
import os

import pytest

from tidy_downloads.config import default_config
from tidy_downloads.errors import UndoError
from tidy_downloads.sorter import (
    LOG_FILENAME,
    apply_plan,
    build_plan,
    undo,
    unique_destination,
)


def test_case_insensitive_reservation_appends_suffix(box):
    reserved = set()
    first = unique_destination(box, "Photo.JPG", reserved, True)
    second = unique_destination(box, "photo.jpg", reserved, True)
    assert first.name == "Photo.JPG"
    assert second.name == "photo (1).jpg"

    sensitive = set()
    assert unique_destination(box, "Photo.JPG", sensitive, False).name == "Photo.JPG"
    assert unique_destination(box, "photo.jpg", sensitive, False).name == "photo.jpg"


def test_numbered_names_continue(box):
    (box / "a (1).jpg").write_text("taken", encoding="utf-8")
    reserved = set()
    chosen = unique_destination(box, "a (1).jpg", reserved, False)
    assert chosen.name == "a (2).jpg"


def test_plan_skips_directories_hidden_partial_and_config(box):
    (box / "subdir").mkdir()
    (box / "subdir" / "nested.jpg").write_text("x", encoding="utf-8")
    (box / ".secret.png").write_text("x", encoding="utf-8")
    (box / "movie.mp4.part").write_bytes(b"x")
    (box / "tidy-downloads.toml").write_text("", encoding="utf-8")
    (box / "photo.jpg").write_bytes(b"x")
    (box / LOG_FILENAME).write_text("{}", encoding="utf-8")
    plan = build_plan(box, default_config())
    assert [move.source.name for move in plan.moves] == ["photo.jpg"]
    reasons = {skip.path.name: skip.reason for skip in plan.skips}
    assert reasons[".secret.png"] == "hidden"
    assert reasons["movie.mp4.part"] == "partial download"
    assert reasons["tidy-downloads.toml"] == "config file"
    assert "subdir" not in reasons
    assert LOG_FILENAME not in reasons


def test_fifo_is_reported_and_not_moved(box):
    fifo = box / "pipe"
    try:
        os.mkfifo(fifo)
    except (AttributeError, OSError):
        pytest.skip("this platform cannot create a fifo")
    (box / "photo.jpg").write_bytes(b"x")
    plan = build_plan(box, default_config())
    assert [move.source.name for move in plan.moves] == ["photo.jpg"]
    assert any(skip.path.name == "pipe" and skip.reason == "not a regular file" for skip in plan.skips)
    apply_plan(plan)
    assert fifo.exists()
    assert not fifo.is_symlink()
    assert (box / "Images" / "photo.jpg").is_file()


def test_undo_rejects_paths_that_escape(box, tmp_path):
    outside = tmp_path / "outside.txt"
    (box / LOG_FILENAME).write_text(
        json.dumps({"version": 1, "moves": [{"from": "../outside.txt", "to": "Images/a.jpg"}]}),
        encoding="utf-8",
    )
    with pytest.raises(UndoError):
        undo(box, dry_run=False)
    assert not outside.exists()

    (box / LOG_FILENAME).write_text(
        json.dumps({"version": 1, "moves": [{"from": ".", "to": "a.jpg"}]}),
        encoding="utf-8",
    )
    with pytest.raises(UndoError):
        undo(box, dry_run=True)


def test_undo_rejects_symlink_that_points_outside(box, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "a.jpg").write_text("secret", encoding="utf-8")
    try:
        (box / "Images").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are not permitted")
    (box / LOG_FILENAME).write_text(
        json.dumps({"version": 1, "moves": [{"from": "a.jpg", "to": "Images/a.jpg"}]}),
        encoding="utf-8",
    )
    with pytest.raises(UndoError):
        undo(box, dry_run=False)
    assert (outside / "a.jpg").read_text(encoding="utf-8") == "secret"
    assert not (box / "a.jpg").exists()


def test_partial_apply_records_only_completed_moves(box, monkeypatch):
    (box / "a.jpg").write_text("a", encoding="utf-8")
    (box / "b.pdf").write_text("b", encoding="utf-8")
    original = type(box).rename
    calls = {"n": 0}

    def flaky(self, target):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise OSError("disk full")
        return original(self, target)

    monkeypatch.setattr(type(box), "rename", flaky)
    plan = build_plan(box, default_config())
    with pytest.raises(Exception, match="disk full"):
        apply_plan(plan)
    assert (box / "Images" / "a.jpg").read_text(encoding="utf-8") == "a"
    assert (box / "b.pdf").is_file()
    log = json.loads((box / LOG_FILENAME).read_text(encoding="utf-8"))
    assert log["version"] == 1
    assert log["moves"] == [{"from": "a.jpg", "to": "Images/a.jpg"}]
