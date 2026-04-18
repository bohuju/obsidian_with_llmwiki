"""Utility functions for Obsidian vault operations."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from raw note content.

    Returns a tuple of (frontmatter_dict, body_content).
    """
    fm: dict = {}
    content = raw

    if raw.startswith("---"):
        end_index = raw.find("---", 3)
        if end_index != -1:
            fm_text = raw[3:end_index].strip()
            content = raw[end_index + 3 :].strip()
            for line in fm_text.split("\n"):
                colon_idx = line.find(":")
                if colon_idx > 0:
                    key = line[:colon_idx].strip()
                    val = line[colon_idx + 1 :].strip()
                    try:
                        fm[key] = json.loads(val)
                    except (ValueError, TypeError):
                        fm[key] = val

    return fm, content


def extract_title(content: str) -> str | None:
    """Extract the first markdown heading (# ...) from content."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else None


def normalize_note_path(vault_root: Path, note_path: str) -> Path:
    """Normalize a note path within the vault.

    Strips leading slash, ensures .md suffix, and resolves to absolute path.
    """
    p = note_path.lstrip("/")
    if not p.endswith(".md"):
        p += ".md"
    return (vault_root / p).resolve()


def relative_path(vault_root: Path, abs_path: Path) -> str:
    """Get the vault-relative path as a string."""
    return os.path.relpath(str(abs_path), str(vault_root))


def walk_markdown_files(directory: Path, vault_root: Path) -> list[str]:
    """Recursively find all .md files, returning vault-relative paths.

    Skips dot-prefixed directories and .trash.
    """
    results: list[str] = []
    if not directory.exists():
        return results

    for entry in sorted(directory.iterdir()):
        # Skip hidden dirs and .trash
        if entry.name.startswith(".") or entry.name == ".trash":
            continue
        if entry.is_dir():
            results.extend(walk_markdown_files(entry, vault_root))
        elif entry.name.endswith(".md"):
            results.append(relative_path(vault_root, entry))

    return results
