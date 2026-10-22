"""A small TOML reader for tidy-downloads config files.

The standard library has no TOML parser until Python 3.11, and this tool
stays dependency-free on Python 3.9+. Config files only need comments,
strings, booleans, numbers, arrays, and tables, so the parser accepts that
subset and rejects everything else with a line number.

Not supported: multiline strings, inline tables, dates, and arrays of tables.
"""

from __future__ import annotations

import re

from tidy_downloads.errors import ConfigError

_BARE_KEY = re.compile(r"[A-Za-z0-9_-]+")
_TABLE_NAME = re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*")


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.length = len(text)
        self.index = 0
        self.line = 1

    def parse(self) -> dict:
        root: dict = {}
        current = root
        while True:
            self._skip()
            if self.index >= self.length:
                return root
            if self._peek() == "[":
                parts = self._read_table_header()
                current = _enter_table(root, parts, self.line)
                continue
            key_line = self.line
            key = self._read_key()
            self._skip()
            self._expect("=")
            self._skip()
            value = self._read_value()
            if key in current:
                raise ConfigError(f"line {key_line}: duplicate key {key!r}")
            current[key] = value

    def _peek(self) -> str:
        if self.index >= self.length:
            return ""
        return self.text[self.index]

    def _bump(self) -> str:
        character = self._peek()
        if not character:
            raise ConfigError(f"line {self.line}: unexpected end of file")
        self.index += 1
        if character == "\n":
            self.line += 1
        return character

    def _skip(self) -> None:
        while self.index < self.length:
            character = self._peek()
            if character in " \t\r\n":
                self._bump()
                continue
            if character == "#":
                while self.index < self.length and self._peek() != "\n":
                    self._bump()
                continue
            break

    def _expect(self, token: str) -> None:
        if self._peek() != token:
            found = self._peek() or "end of file"
            raise ConfigError(f"line {self.line}: expected {token!r}, found {found!r}")
        self._bump()

    def _read_table_header(self) -> list[str]:
        start_line = self.line
        self._expect("[")
        if self._peek() == "[":
            raise ConfigError(f"line {start_line}: arrays of tables are not supported")
        start = self.index
        while self.index < self.length and self._peek() not in "]\n":
            self._bump()
        if self._peek() != "]":
            raise ConfigError(f"line {start_line}: unclosed table header")
        header = self.text[start : self.index].strip()
        self._expect("]")
        if not _TABLE_NAME.fullmatch(header):
            raise ConfigError(
                f"line {start_line}: unsupported table name {header!r}. "
                "Use bare keys such as [categories]."
            )
        return header.split(".")

    def _read_key(self) -> str:
        self._skip()
        if self._peek() in "\"'":
            return self._read_string()
        start = self.index
        start_line = self.line
        while self.index < self.length and self._peek() not in " \t\r\n=#[]":
            self._bump()
        if self.index == start:
            raise ConfigError(f"line {start_line}: expected a key")
        key = self.text[start : self.index]
        if not _BARE_KEY.fullmatch(key):
            raise ConfigError(
                f"line {start_line}: invalid key {key!r}. "
                "Quote keys that contain spaces or other characters."
            )
        return key

    def _read_value(self):
        character = self._peek()
        if character in "\"'":
            return self._read_string()
        if character == "[":
            return self._read_array()
        if self._keyword("true"):
            return True
        if self._keyword("false"):
            return False
        if character.isdigit() or character == "-":
            return self._read_number()
        found = character or "end of file"
        raise ConfigError(f"line {self.line}: unsupported value starting with {found!r}")

    def _keyword(self, word: str) -> bool:
        end = self.index + len(word)
        if self.text.startswith(word, self.index) and self._at_boundary(end):
            self.index = end
            return True
        return False

    def _at_boundary(self, index: int) -> bool:
        if index >= self.length:
            return True
        return self.text[index] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"

    def _read_string(self) -> str:
        quote = self._bump()
        if self._peek() == quote:
            # "" is empty. """ would be a multiline string.
            if self.text.startswith(quote * 2, self.index):
                raise ConfigError(f"line {self.line}: multiline strings are not supported")
            self._bump()
            return ""
        characters: list[str] = []
        start_line = self.line
        while self.index < self.length:
            character = self._bump()
            if character == "\n":
                raise ConfigError(f"line {start_line}: unclosed string")
            if quote == '"' and character == "\\":
                if self.index >= self.length:
                    raise ConfigError(f"line {start_line}: unclosed string escape")
                escaped = self._bump()
                mapped = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "/": "/"}.get(escaped)
                if mapped is None:
                    raise ConfigError(f"line {self.line}: unsupported escape \\{escaped}")
                characters.append(mapped)
                continue
            if character == quote:
                return "".join(characters)
            characters.append(character)
        raise ConfigError(f"line {start_line}: unclosed string")

    def _read_array(self) -> list:
        start_line = self.line
        self._expect("[")
        items: list = []
        while True:
            self._skip()
            if self.index >= self.length:
                raise ConfigError(f"line {start_line}: unclosed array")
            if self._peek() == "]":
                self._bump()
                return items
            items.append(self._read_value())
            self._skip()
            if self._peek() == ",":
                self._bump()
                continue
            if self._peek() == "]":
                self._bump()
                return items
            raise ConfigError(f"line {self.line}: expected ',' or ']' in array")

    def _read_number(self):
        start = self.index
        start_line = self.line
        if self._peek() == "-":
            self._bump()
        if not self._peek().isdigit():
            raise ConfigError(f"line {start_line}: invalid number")
        while self._peek().isdigit():
            self._bump()
        if self._peek() == ".":
            self._bump()
            if not self._peek().isdigit():
                raise ConfigError(f"line {start_line}: invalid number")
            while self._peek().isdigit():
                self._bump()
            return float(self.text[start : self.index])
        return int(self.text[start : self.index])


def _enter_table(root: dict, parts: list[str], line: int) -> dict:
    node = root
    for part in parts:
        existing = node.get(part)
        if existing is None:
            child: dict = {}
            node[part] = child
            node = child
            continue
        if not isinstance(existing, dict):
            raise ConfigError(f"line {line}: {part!r} is already a value, not a table")
        node = existing
    return node


def parse_toml_subset(text: str) -> dict:
    """Parse the supported TOML subset into nested dicts and lists."""
    if text.startswith("\ufeff"):
        text = text[1:]
    try:
        return _Parser(text).parse()
    except ConfigError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ConfigError(f"could not parse TOML: {exc}") from exc
