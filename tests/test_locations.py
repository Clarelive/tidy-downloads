"""Default Downloads folder detection."""

from pathlib import Path

from tidy_downloads.locations import _windows_downloads, default_downloads_dir


def test_windows_lookup_is_unavailable_elsewhere():
    assert _windows_downloads() is None


def test_fallback_is_home_downloads():
    assert default_downloads_dir() == Path.home() / "Downloads"


def test_xdg_download_dir_from_home_config():
    config_dir = Path.home() / ".config"
    config_dir.mkdir(parents=True)
    (config_dir / "user-dirs.dirs").write_text(
        "\n".join(
            [
                "# comment",
                'XDG_DESKTOP_DIR="$HOME/Desktop"',
                'XDG_DOWNLOAD_DIR="$HOME/My Downloads" # trailing comment',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert default_downloads_dir() == Path.home() / "My Downloads"


def test_xdg_accepts_single_quotes_and_braced_home(monkeypatch, tmp_path):
    config_home = tmp_path / "cfg"
    config_home.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    (config_home / "user-dirs.dirs").write_text(
        "XDG_DOWNLOAD_DIR='${HOME}/dl'\n",
        encoding="utf-8",
    )
    assert default_downloads_dir() == Path.home() / "dl"


def test_xdg_without_download_key_falls_back():
    config_dir = Path.home() / ".config"
    config_dir.mkdir(parents=True)
    (config_dir / "user-dirs.dirs").write_text(
        'XDG_DESKTOP_DIR="$HOME/Desktop"\n',
        encoding="utf-8",
    )
    assert default_downloads_dir() == Path.home() / "Downloads"
