"""Bidirectional link engine for Obsidian wiki-links.

Handles [[wiki-link]] injection, extraction, backlink queries, and graph
construction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .utils import extract_title, walk_markdown_files


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GraphNode:
    path: str
    title: str | None


@dataclass
class GraphEdge:
    source: str
    target: str


@dataclass
class Graph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)


# ---------------------------------------------------------------------------
# LinkEngine
# ---------------------------------------------------------------------------

class LinkEngine:
    """Bidirectional link engine for an Obsidian vault.

    Responsible for [[wiki-link]] injection, parsing, reverse lookups and
    graph construction.
    """

    def __init__(self, vault_path: str | Path) -> None:
        self.vault_path = Path(vault_path).resolve()
        self._title_cache: dict[str, str] = {}  # normalized_title -> path
        self._cache_valid: bool = False

    # --- Link injection ---------------------------------------------------

    def refresh_title_cache(self) -> None:
        """Scan the vault and rebuild the title cache."""
        self._title_cache.clear()
        files = walk_markdown_files(self.vault_path, self.vault_path)

        for file in files:
            abs_path = self.vault_path / file
            content = abs_path.read_text(encoding="utf-8")
            title = extract_title(content)

            # basename without .md
            basename = file.removesuffix(".md")
            name_only = Path(file).stem

            if title:
                self._title_cache[title.lower()] = file
            self._title_cache[name_only.lower()] = file
            # Also register full relative path
            self._title_cache[basename.lower()] = file

        self._cache_valid = True

    def get_note_titles(self, folder: str | None = None) -> list[dict]:
        """Return a list of {path, title} dicts for all (or folder-scoped) notes."""
        if not self._cache_valid:
            self.refresh_title_cache()

        if folder:
            files = walk_markdown_files(self.vault_path / folder, self.vault_path)
        else:
            files = walk_markdown_files(self.vault_path, self.vault_path)

        result: list[dict] = []
        for f in files:
            abs_path = self.vault_path / f
            content = abs_path.read_text(encoding="utf-8")
            result.append({"path": f, "title": extract_title(content)})
        return result

    def inject_links(self, content: str) -> str:
        """Auto-inject [[wiki-links]] into note content.

        Rules:
         1. Skip text already inside [[...]]
         2. Skip frontmatter region
         3. Match known note titles -> [[path]]
         4. Match dates YYYY-MM-DD -> [[310-Daily/YYYY-MM-DD]]
        """
        if not self._cache_valid:
            self.refresh_title_cache()

        # Separate frontmatter
        fm_part = ""
        body_part = content

        if content.startswith("---"):
            end_index = content.find("---", 3)
            if end_index != -1:
                fm_part = content[: end_index + 3]
                body_part = content[end_index + 3 :]

        # Collect all known titles, sorted by key length descending (longest first)
        sorted_titles = sorted(
            [
                {
                    "key": key,
                    "file_path": file_path,
                    "display": file_path.removesuffix(".md"),
                }
                for key, file_path in self._title_cache.items()
            ],
            key=lambda x: len(x["key"]),
            reverse=True,
        )

        result = body_part

        # Inject date links: YYYY-MM-DD not already inside [[...]]
        result = re.sub(
            r"(?<!\[\[)(\d{4}-\d{2}-\d{2})(?!\]\])",
            lambda m: f"[[310-Daily/{m.group(1)}]]",
            result,
        )

        # Inject known title links
        for entry in sorted_titles:
            key = entry["key"]
            display = entry["display"]
            if len(key) < 2:
                continue  # Skip very short titles

            # Escape regex special characters
            escaped = re.escape(key)
            # Match text not preceded by [[ or / and not followed by ]]
            pattern = rf"(?<!\[/)\b({escaped})\b(?!\])"
            result = re.sub(
                pattern,
                lambda m, _display=display: f"[[{_display}]]",
                result,
                flags=re.IGNORECASE,
            )

        # Clean nested links: [[[[a]]]] -> [[a]]
        result = re.sub(r"\[\[\[([^\]]+)\]\]\]", r"[[\1]]", result)

        return fm_part + result

    # --- Link extraction --------------------------------------------------

    @staticmethod
    def extract_links(content: str) -> list[str]:
        """Extract all [[wiki-link]] targets from content.

        Handles both [[target]] and [[target|alias]] forms. Strips leading
        ../ segments and removes .md suffixes. Returns unique links.
        """
        links: list[str] = []
        regex = r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]"
        for match in re.finditer(regex, content):
            target = match.group(1).strip()
            # Strip leading ../
            while target.startswith("../"):
                target = target[3:]
            if target.endswith(".md"):
                target = target.removesuffix(".md")
            links.append(target)

        return list(dict.fromkeys(links))  # unique, preserving order

    def get_outlinks(self, note_path: str) -> list[str]:
        """Get all outgoing links from a note."""
        abs_path = self.vault_path / note_path
        if not abs_path.exists():
            return []

        content = abs_path.read_text(encoding="utf-8")
        return LinkEngine.extract_links(content)

    def get_backlinks(self, note_path: str) -> list[dict]:
        """Get all backlinks pointing to *note_path*.

        Returns a list of {source, context} dicts.
        """
        files = walk_markdown_files(self.vault_path, self.vault_path)
        results: list[dict] = []

        # Possible reference forms for the target note
        basename = Path(note_path).stem
        targets = [
            note_path.removesuffix(".md"),
            basename,
            f"/{basename}",
            f"/{note_path.removesuffix('.md')}",
        ]

        for file in files:
            if file == note_path:
                continue
            abs_path = self.vault_path / file
            content = abs_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            for line in lines:
                links = LinkEngine.extract_links(line)
                has_match = any(
                    link.lower() == t.lower() or link.lower().endswith(t.lower())
                    for link in links
                    for t in targets
                )

                if has_match:
                    results.append({
                        "source": file,
                        "context": line.strip()[:200],
                    })
                    break  # Only first matching line per file

        return results

    # --- Graph construction -----------------------------------------------

    def build_graph(self) -> Graph:
        """Build the full bidirectional link graph."""
        files = walk_markdown_files(self.vault_path, self.vault_path)
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        for file in files:
            abs_path = self.vault_path / file
            content = abs_path.read_text(encoding="utf-8")

            nodes.append(GraphNode(path=file, title=extract_title(content)))

            outlinks = LinkEngine.extract_links(content)
            for target in outlinks:
                edges.append(GraphEdge(source=file, target=target))

        return Graph(nodes=nodes, edges=edges)
