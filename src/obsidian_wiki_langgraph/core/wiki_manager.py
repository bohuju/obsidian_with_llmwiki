"""
Wiki Manager - manages wiki directory structure and metadata.
Ported from obsidian-llm-wiki src/wiki-manager.ts
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from ..config import DEFAULT_PAGE_TYPES, RAW_SUBDIRS
from ..templates.claude_md import generate_claude_md
from ..templates.readme_md import generate_readme_md
from .utils import walk_markdown_files


class WikiManager:
    """Manages the wiki directory structure, indexes, and logs."""

    def __init__(self, vault_path: str | Path, wiki_root: str | None = None) -> None:
        self.vault_path: Path = Path(vault_path).resolve()
        self.wiki_root: str = wiki_root if wiki_root is not None else ""

    # --- Private path helpers ------------------------------------------------

    def _resolve_wiki(self, *segments: str) -> Path:
        """Resolve a path relative to the wiki root."""
        base = self.vault_path / self.wiki_root if self.wiki_root else self.vault_path
        return base.joinpath(*segments)

    def _resolve_raw(self, *segments: str) -> Path:
        """Resolve a path relative to raw/ under the wiki root."""
        return self._resolve_wiki("raw", *segments)

    # --- Public API ----------------------------------------------------------

    def detect(self) -> dict:
        """Check whether the wiki has been initialised.

        Returns
        -------
        dict
            Keys: initialized, wiki_root, raw_dirs, wiki_dirs.
        """
        raw_dir = self._resolve_raw()
        wiki_dir = self._resolve_wiki("wiki")

        raw_exists = raw_dir.exists()
        wiki_exists = wiki_dir.exists()

        raw_dirs: list[str] = (
            [d.name for d in raw_dir.iterdir() if d.is_dir()]
            if raw_exists
            else []
        )
        wiki_dirs: list[str] = (
            [d.name for d in wiki_dir.iterdir() if d.is_dir()]
            if wiki_exists
            else []
        )

        return {
            "initialized": raw_exists and wiki_exists,
            "wiki_root": self.wiki_root,
            "raw_dirs": raw_dirs,
            "wiki_dirs": wiki_dirs,
        }

    def init(self, page_types: list[str] | None = None) -> dict:
        """Initialise the wiki directory structure.

        Parameters
        ----------
        page_types : list[str] | None
            Wiki page-type sub-directories to create under ``wiki/``.
            Defaults to :data:`DEFAULT_PAGE_TYPES`.

        Returns
        -------
        dict
            Keys: created (list[str]), files (list[str]).
        """
        if page_types is None:
            page_types = list(DEFAULT_PAGE_TYPES)

        created: list[str] = []
        files: list[str] = []

        # Create raw sub-directories
        for sub in RAW_SUBDIRS:
            dir_path = self._resolve_raw(sub)
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                created.append(f"raw/{sub}")

        # Create wiki sub-directories
        for pt in page_types:
            dir_path = self._resolve_wiki("wiki", pt)
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                created.append(f"wiki/{pt}")

        # Generate CLAUDE.md
        claude_md_path = self._resolve_wiki("CLAUDE.md")
        vault_name = self.vault_path.name
        claude_md_content = generate_claude_md({
            "vault_name": vault_name,
            "wiki_root": f"{self.wiki_root}/" if self.wiki_root else "",
            "page_types": page_types,
        })
        claude_md_path.write_text(claude_md_content, encoding="utf-8")
        files.append("CLAUDE.md")

        # Generate README.md
        readme_path = self._resolve_wiki("README.md")
        readme_content = generate_readme_md({
            "vault_name": vault_name,
            "wiki_root": self.wiki_root,
        })
        readme_path.write_text(readme_content, encoding="utf-8")
        files.append("README.md")

        # Create index page
        index_path = self._resolve_wiki("wiki", "indexes", "index.md")
        if not index_path.exists():
            today = date.today().isoformat()
            page_type_lines = "\n".join(
                f"- [[wiki/{t}/]]" for t in page_types
            )
            index_content = (
                f"---\n"
                f"type: index\n"
                f"created: {today}\n"
                f"tags: [wiki, index]\n"
                f"---\n\n"
                f"# Wiki 索引\n\n"
                f"> 所有 wiki 页面的目录\n\n"
                f"## 按类型\n"
                f"{page_type_lines}\n"
            )
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(index_content, encoding="utf-8")
            files.append("wiki/indexes/index.md")

        # Create log page
        log_path = self._resolve_wiki("wiki", "indexes", "log.md")
        if not log_path.exists():
            today = date.today().isoformat()
            log_content = (
                f"---\n"
                f"type: index\n"
                f"tags: [wiki, log]\n"
                f"---\n\n"
                f"# 操作日志\n\n"
                f"## {today}\n\n"
                f"- Wiki 初始化完成\n"
                f"- 创建目录: {', '.join(created)}\n"
            )
            log_path.write_text(log_content, encoding="utf-8")
            files.append("wiki/indexes/log.md")

        return {"created": created, "files": files}

    def status(self) -> dict:
        """Return the current wiki status.

        Returns
        -------
        dict
            Keys: initialized, total_pages, page_counts, raw_files,
            ingested_sources, orphan_pages.
        """
        detection = self.detect()
        if not detection["initialized"]:
            return {
                "initialized": False,
                "total_pages": 0,
                "page_counts": {},
                "raw_files": [],
                "ingested_sources": [],
                "orphan_pages": [],
            }

        # Count pages per type
        page_counts: dict[str, int] = {}
        total_pages = 0
        for pt in DEFAULT_PAGE_TYPES:
            dir_path = self._resolve_wiki("wiki", pt)
            if dir_path.exists():
                md_files = [f for f in dir_path.iterdir() if f.suffix == ".md"]
                count = len(md_files)
            else:
                count = 0
            page_counts[pt] = count
            total_pages += count

        # List raw files
        raw_dir = self._resolve_raw()
        raw_files: list[str] = (
            walk_markdown_files(raw_dir, raw_dir) if raw_dir.exists() else []
        )

        # Check ingested sources (via summaries frontmatter)
        summaries_dir = self._resolve_wiki("wiki", "summaries")
        ingested_sources: list[str] = []
        if summaries_dir.exists():
            for sf in summaries_dir.iterdir():
                if sf.suffix != ".md":
                    continue
                content = sf.read_text(encoding="utf-8")
                if re.search(r"sources:\s*\[.+?\]", content):
                    ingested_sources.append(sf.stem)

        return {
            "initialized": True,
            "total_pages": total_pages,
            "page_counts": page_counts,
            "raw_files": raw_files,
            "ingested_sources": ingested_sources,
            "orphan_pages": [],
        }

    def list_sources(self, folder: str | None = None) -> list[dict]:
        """List raw source files with their ingestion status.

        Parameters
        ----------
        folder : str | None
            Sub-directory of raw/ to list.  Lists all of raw/ when *None*.

        Returns
        -------
        list[dict]
            Each dict has keys: path, ingested, size.
        """
        target_dir = self._resolve_raw(folder) if folder else self._resolve_raw()

        if not target_dir.exists():
            return []

        raw_base = self._resolve_raw()
        files = walk_markdown_files(target_dir, raw_base)
        ingested = set(self.status()["ingested_sources"])

        result: list[dict] = []
        for f in files:
            abs_path = raw_base / f
            stat = abs_path.stat()
            name = Path(f).stem
            result.append({
                "path": f,
                "ingested": name in ingested,
                "size": stat.st_size,
            })
        return result

    def append_log(self, entry: str) -> None:
        """Append an entry to the wiki operation log.

        Parameters
        ----------
        entry : str
            The log message to append.
        """
        log_path = self._resolve_wiki("wiki", "indexes", "log.md")
        if not log_path.exists():
            return

        today = date.today().isoformat()
        content = log_path.read_text(encoding="utf-8")

        # Check whether today's section already exists
        section_header = f"## {today}"
        if section_header in content:
            # Append to today's section
            updated = content.replace(
                f"{section_header}\n",
                f"{section_header}\n\n- {entry}\n",
            )
            log_path.write_text(updated, encoding="utf-8")
        else:
            # Create a new section for today
            log_path.write_text(
                content.rstrip() + f"\n\n{section_header}\n\n- {entry}\n",
                encoding="utf-8",
            )

    def update_index(self, new_pages: list[dict]) -> None:
        """Update the wiki index with new pages.

        Parameters
        ----------
        new_pages : list[dict]
            Each dict must have keys: type, path, title.
        """
        index_path = self._resolve_wiki("wiki", "indexes", "index.md")
        if not index_path.exists():
            return

        content = index_path.read_text(encoding="utf-8")

        for page in new_pages:
            line = f"- [[{page['path'].removesuffix('.md')}|{page['title']}]]"
            if line in content:
                continue

            section_header = f"### {page['type']}"
            if section_header in content:
                content = content.replace(
                    f"{section_header}\n",
                    f"{section_header}\n{line}\n",
                )
            else:
                # Append a new type section
                content = content.rstrip() + f"\n\n{section_header}\n\n{line}\n"

        index_path.write_text(content, encoding="utf-8")
