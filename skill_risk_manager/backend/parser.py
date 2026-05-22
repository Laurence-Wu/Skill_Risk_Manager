from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParsedMarkdown:
    header_text: str
    frontmatter: dict[str, Any] = field(default_factory=dict)


def read_markdown_header(path: Path, max_bytes: int = 8192, max_lines: int = 100) -> str:
    with path.open("rb") as markdown_file:
        raw_header = markdown_file.read(max_bytes)
    decoded_header = raw_header.decode("utf-8", errors="replace")
    return "\n".join(decoded_header.splitlines()[:max_lines])


def parse_markdown_header(path: Path) -> ParsedMarkdown:
    header_text = read_markdown_header(path)
    return ParsedMarkdown(header_text=header_text, frontmatter=parse_frontmatter(header_text))


def parse_frontmatter(header_text: str) -> dict[str, Any]:
    lines = header_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    frontmatter_lines: list[str] = []
    found_closing_delimiter = False
    for line in lines[1:]:
        if line.strip() == "---":
            found_closing_delimiter = True
            break
        frontmatter_lines.append(line)
    if not found_closing_delimiter:
        return {}

    frontmatter, _ = _parse_mapping(frontmatter_lines, 0, 0, top_level=True)
    return frontmatter


def has_skill_like_frontmatter(frontmatter: dict[str, Any]) -> bool:
    keys = set(frontmatter)
    return "name" in keys and ("description" in keys or "summary" in keys)


def _parse_mapping(
    lines: list[str],
    index: int,
    indent: int,
    *,
    top_level: bool,
) -> tuple[dict[str, Any], int]:
    mapping: dict[str, Any] = {}
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        current_indent = _indent_width(line)
        if current_indent < indent:
            break
        if current_indent > indent:
            break

        stripped_line = line.strip()
        if stripped_line.startswith("- ") or ":" not in stripped_line:
            break

        key, raw_value = stripped_line.split(":", 1)
        normalized_key = key.strip().lower() if top_level else key.strip()
        value = raw_value.strip()
        index += 1

        if value:
            mapping[normalized_key] = _parse_scalar(value)
            continue

        next_index = _next_content_index(lines, index)
        if next_index is None or _indent_width(lines[next_index]) <= current_indent:
            mapping[normalized_key] = {}
            continue

        next_indent = _indent_width(lines[next_index])
        if lines[next_index].strip().startswith("- "):
            nested_value, index = _parse_list(lines, index, next_indent)
        else:
            nested_value, index = _parse_mapping(lines, index, next_indent, top_level=False)
        mapping[normalized_key] = nested_value

    return mapping, index


def _parse_list(lines: list[str], index: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        current_indent = _indent_width(line)
        if current_indent < indent:
            break
        if current_indent > indent:
            break

        stripped_line = line.strip()
        if not stripped_line.startswith("- "):
            break

        item_text = stripped_line[2:].strip()
        index += 1

        if ":" in item_text:
            key, raw_value = item_text.split(":", 1)
            item: dict[str, Any] = {key.strip(): _parse_scalar(raw_value.strip())}
            next_index = _next_content_index(lines, index)
            if next_index is not None and _indent_width(lines[next_index]) > current_indent:
                continuation, index = _parse_mapping(
                    lines,
                    index,
                    _indent_width(lines[next_index]),
                    top_level=False,
                )
                item.update(continuation)
            items.append(item)
            continue

        items.append(_parse_scalar(item_text))

    return items, index


def _parse_scalar(value: str) -> Any:
    stripped_value = value.strip()
    if not stripped_value:
        return ""
    if stripped_value[0:1] in {"'", '"'} and stripped_value[-1:] == stripped_value[0]:
        return stripped_value[1:-1]
    lowered_value = stripped_value.lower()
    if lowered_value == "true":
        return True
    if lowered_value == "false":
        return False
    if lowered_value in {"null", "none"}:
        return None
    return stripped_value


def _indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _next_content_index(lines: list[str], index: int) -> int | None:
    for candidate_index in range(index, len(lines)):
        if lines[candidate_index].strip():
            return candidate_index
    return None
