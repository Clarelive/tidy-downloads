"""Config parsing, merging, and lookup order."""

import json
from pathlib import Path

import pytest

from tidy_downloads.categories import DEFAULT_CATEGORIES, DEFAULT_SKIP_EXTENSIONS
from tidy_downloads.config import (
    build_config,
    default_config,
    load_config,
    load_config_file,
    validate_category_name,
)
from tidy_downloads.errors import ConfigError
from tidy_downloads.toml_subset import parse_toml_subset

ROOT = Path(__file__).resolve().parents[1]


def test_default_extensions_are_unique():
    seen = {}
    for category, extensions in DEFAULT_CATEGORIES.items():
        for extension in extensions:
            assert extension == extension.lower()
            assert extension not in seen, f"{extension} is in {seen.get(extension)} and {category}"
            seen[extension] = category
    assert set(DEFAULT_SKIP_EXTENSIONS) == {"crdownload", "part", "tmp"}


def test_default_matching_is_case_insensitive():
    config = default_config()
    assert config.category_for("Photo.JPG") == "Images"
    assert config.category_for("archive.TAR.GZ") == "Archives"
    assert config.category_for("notes.tmp.txt") == "Documents"
    assert config.category_for("clip.TS") == "Video"
    assert config.category_for("README") == "Others"
    assert config.category_for("data.xyz") == "Others"
    assert config.is_partial("movie.mp4.PART")
    assert config.is_partial("file.CRDOWNLOAD")
    assert not config.is_partial("notes.tmp.txt")


def test_toml_subset_accepts_comments_arrays_and_quoted_keys():
    data = parse_toml_subset(
        """
        # comment
        replace_categories = false # inline
        limit = 3
        fraction = 1.5
        negative = -2

        skip_extensions = ["part"]

        [categories]
        Images = [
          "jpg", # still an image
          "png",
        ]
        "My Pics" = ["gif"]
        """
    )
    assert data["replace_categories"] is False
    assert data["limit"] == 3
    assert data["fraction"] == 1.5
    assert data["negative"] == -2
    assert data["skip_extensions"] == ["part"]
    assert data["categories"]["Images"] == ["jpg", "png"]
    assert data["categories"]["My Pics"] == ["gif"]


def test_toml_crlf_and_bom():
    text = "\ufeffreplace_categories = true\r\n\r\n[categories]\r\nEbooks = [\r\n  \"epub\",\r\n]\r\n"
    data = parse_toml_subset(text)
    assert data["replace_categories"] is True
    assert data["categories"]["Ebooks"] == ["epub"]


@pytest.mark.parametrize(
    "text",
    [
        'title = "unterminated',
        "limit = trueish\n",
        "[[categories]]\n",
        'name = "a"\nname = "b"\n',
        "not a line\n",
    ],
)
def test_toml_rejects_unsupported_syntax(text):
    with pytest.raises(ConfigError):
        parse_toml_subset(text)


def test_longest_extension_wins_and_empty_category_is_removed():
    config = build_config(
        {
            "categories": {
                "Tarballs": ["tar.gz", ".TAR.GZ"],
                "Images": [],
            }
        }
    )
    assert config.category_for("backup.tar.gz") == "Tarballs"
    assert config.category_for("plain.gz") == "Archives"
    assert config.category_for("photo.jpg") == "Others"
    assert "Images" not in config.categories


def test_later_category_steals_extension_and_skip_list_replaces():
    config = build_config(
        {
            "skip_extensions": ["part"],
            "categories": {
                "Images": ["jpg", "png"],
                "Photos": ["JPG"],
            },
        }
    )
    assert config.category_for("a.jpg") == "Photos"
    assert config.category_for("a.png") == "Images"
    assert config.is_partial("a.part")
    assert not config.is_partial("a.tmp")


def test_replace_categories_and_custom_fallback():
    config = build_config(
        {
            "replace_categories": True,
            "others": "Misc",
            "categories": {"Ebooks": ["epub"]},
        }
    )
    assert config.category_for("book.epub") == "Ebooks"
    assert config.category_for("photo.jpg") == "Misc"


@pytest.mark.parametrize(
    "data",
    [
        {"replace_categories": "yes"},
        {"others": "../Misc"},
        {"others": "CON"},
        {"categories": ["jpg"]},
        {"categories": {"../evil": ["jpg"]}},
        {"categories": {"Images": [1]}},
        {"categories": {"Images": ["has space"]}},
        {"skip_extensions": "tmp"},
    ],
)
def test_invalid_config_values(data):
    with pytest.raises(ConfigError):
        build_config(data)


def test_category_name_rules():
    assert validate_category_name("  E-books  ") == "E-books"
    with pytest.raises(ConfigError):
        validate_category_name("LPT1")


def test_json_and_toml_files_round_trip(tmp_path):
    payload = {"categories": {"E Books": ["epub"]}}
    json_path = tmp_path / "tidy.json"
    toml_path = tmp_path / "tidy.toml"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    toml_path.write_text('[categories]\n"E Books" = ["epub"]\n', encoding="utf-8")
    assert load_config_file(json_path).category_for("a.epub") == "E Books"
    assert load_config_file(toml_path).category_for("a.epub") == "E Books"


def test_json_bom_and_bad_suffix(tmp_path):
    path = tmp_path / "config.json"
    path.write_bytes(b'\xef\xbb\xbf{"categories": {"Ebooks": ["epub"]}}\n')
    assert load_config_file(path).category_for("a.epub") == "Ebooks"
    other = tmp_path / "config.txt"
    other.write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config_file(other)


def test_examples_agree():
    toml_config = load_config_file(ROOT / "examples" / "tidy-downloads.toml")
    json_config = load_config_file(ROOT / "examples" / "tidy-downloads.json")
    for config in (toml_config, json_config):
        assert config.category_for("book.epub") == "Ebooks"
        assert config.category_for("notes.pdf") == "Documents"
        assert config.category_for("pic.jpg") == "Images"
        assert config.is_partial("file.download")
        assert config.is_partial("file.tmp")


def test_config_search_order(box, monkeypatch, tmp_path):
    xdg = tmp_path / "xdg"
    (xdg / "tidy-downloads").mkdir(parents=True)
    (xdg / "tidy-downloads" / "config.toml").write_text(
        '[categories]\nEbooks = ["epub"]\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    assert load_config(box).category_for("a.epub") == "Ebooks"

    home_file = Path.home() / ".tidy-downloads.toml"
    home_file.write_text('[categories]\nHomeBooks = ["epub"]\n', encoding="utf-8")
    assert load_config(box).category_for("a.epub") == "Ebooks"

    (box / "tidy-downloads.json").write_text(
        json.dumps({"categories": {"JsonBooks": ["epub"]}}),
        encoding="utf-8",
    )
    assert load_config(box).category_for("a.epub") == "JsonBooks"

    (box / "tidy-downloads.toml").write_text(
        '[categories]\nFolderBooks = ["epub"]\n',
        encoding="utf-8",
    )
    assert load_config(box).category_for("a.epub") == "FolderBooks"

    env_file = tmp_path / "env.toml"
    env_file.write_text('[categories]\nEnvBooks = ["epub"]\n', encoding="utf-8")
    monkeypatch.setenv("TIDY_DOWNLOADS_CONFIG", str(env_file))
    assert load_config(box).category_for("a.epub") == "EnvBooks"

    explicit = tmp_path / "explicit.toml"
    explicit.write_text('[categories]\nExplicitBooks = ["epub"]\n', encoding="utf-8")
    assert load_config(box, explicit=explicit).category_for("a.epub") == "ExplicitBooks"


def test_missing_explicit_and_env_config_are_errors(box, monkeypatch, tmp_path):
    missing = tmp_path / "missing.toml"
    with pytest.raises(ConfigError):
        load_config(box, explicit=missing)
    monkeypatch.setenv("TIDY_DOWNLOADS_CONFIG", str(missing))
    with pytest.raises(ConfigError):
        load_config(box)


def test_version_matches_pyproject():
    from tidy_downloads import __version__

    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{__version__}"' in text
