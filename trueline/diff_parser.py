from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from unidiff import PatchSet


class ChangeKind(str, Enum):
    DROP = "DROP"
    ADD = "ADD"
    TYPE_CHANGE = "TYPE_CHANGE"


@dataclass(frozen=True)
class ChangedColumn:
    name: str
    kind: ChangeKind


@dataclass(frozen=True)
class ChangedFile:
    file_path: str
    columns: tuple[ChangedColumn, ...]
    is_sql: bool = False


_SKIP = frozenset(
    {
        "select", "from", "where", "join", "left", "right", "inner", "outer", "full",
        "on", "and", "or", "as", "by", "group", "order", "having", "limit", "offset",
        "create", "table", "alter", "drop", "column", "add", "modify", "change", "if",
        "not", "exists", "primary", "key", "foreign", "references", "constraint",
        "unique", "index", "with", "union", "all", "distinct", "case", "when", "then",
        "else", "end", "values", "into", "insert", "update", "delete", "set", "null",
        "default", "comment", "partition", "using", "external", "overwrite", "merge",
        "count", "sum", "avg", "min", "max", "cast", "coalesce", "row_number", "rank",
        "over", "partitioned", "clustered", "sorted", "properties", "tblproperties",
        "stored", "location", "format", "engine", "charset", "returns", "return",
    }
)

_IDENT = re.compile(r"^[+-]?\s*([A-Za-z_][A-Za-z0-9_]*)\b(.*)$")
_TOKENS = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _words(line: str) -> list[str]:
    return _TOKENS.findall(line)


def _column_name(name: str, rest: str) -> str:
    """Resolve the output column from a SQL fragment.

    Handles `table.column as alias` → alias, `table.column` → column.
    """
    m = re.match(r"\.([A-Za-z_][A-Za-z0-9_]*)\b", rest)
    if m:
        name = m.group(1)
    m = re.search(r"\bas\s+([A-Za-z_][A-Za-z0-9_]*)\b", rest)
    if m:
        name = m.group(1)
    return name


def _classify(removed: list[str], added: list[str]) -> list[ChangedColumn]:
    changes: list[ChangedColumn] = []

    def _key(m: re.Match) -> str:
        return _column_name(m.group(1), m.group(2))

    removed_map = {_key(m): m for m in (_IDENT.match(l) for l in removed) if m}
    added_map = {_key(m): m for m in (_IDENT.match(l) for l in added) if m}
    for name in sorted(set(removed_map) - set(added_map)):
        changes.append(ChangedColumn(name=name, kind=ChangeKind.DROP))
    for name in sorted(set(added_map) - set(removed_map)):
        changes.append(ChangedColumn(name=name, kind=ChangeKind.ADD))
    for name in sorted(set(removed_map) & set(added_map)):
        if name.lower() in _SKIP:
            continue
        removed_words = _words(removed_map[name].group(2))
        added_words = _words(added_map[name].group(2))
        if removed_words and added_words and removed_words != added_words:
            changes.append(ChangedColumn(name=name, kind=ChangeKind.TYPE_CHANGE))
    return changes


def parse_diff(diff_text: str) -> list[ChangedFile]:
    files: list[ChangedFile] = []
    for patched in PatchSet(diff_text):
        if not patched.is_modified_file or not patched.path.endswith(".sql"):
            continue
        removed: list[str] = []
        added: list[str] = []
        for hunk in patched:
            for line in hunk:
                if line.is_removed:
                    removed.append(line.value.rstrip("\n"))
                elif line.is_added:
                    added.append(line.value.rstrip("\n"))
        columns = tuple(c for c in _classify(removed, added) if c.name.lower() not in _SKIP)
        files.append(ChangedFile(file_path=patched.path, columns=columns, is_sql=True))
    return files