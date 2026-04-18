"""
Wiki Ingester - reads raw source files and builds ingestion prompts.
Ported from obsidian-llm-wiki src/wiki-ingester.ts
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .link_engine import LinkEngine
from .wiki_manager import WikiManager


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def build_ingest_prompt(
    source_name: str,
    source_content: str,
    existing_summaries: list[str],
    existing_pages: list[dict],
) -> str:
    """Build the ingestion prompt for the LLM.

    Parameters
    ----------
    source_name : str
        Name of the raw source file (without extension).
    source_content : str
        Full text content of the source file.
    existing_summaries : list[str]
        Names of already-existing summary pages.
    existing_pages : list[dict]
        Each dict has keys: path, title.

    Returns
    -------
    str
        The ingestion prompt to send to the LLM.
    """
    concepts_list = "\n".join(
        f"- {p.get('title') or p['path']}"
        for p in existing_pages
        if "concepts/" in p["path"]
    )

    entities_list = "\n".join(
        f"- {p.get('title') or p['path']}"
        for p in existing_pages
        if "entities/" in p["path"]
    )

    summaries_list = (
        "\n".join(f"- {s}" for s in existing_summaries)
        if existing_summaries
        else "（无）"
    )

    # Truncate source content to 8000 characters (same as TS version)
    truncated = source_content[:8000]

    return f"""## 知识摄入任务

请将以下 raw 源文件编译为结构化 wiki 页面。

### 源文件: {source_name}

```markdown
{truncated}
```

### 已有的 summary 页面（不要重复创建）
{summaries_list}

### 已有的概念页面（可以交叉引用）
{concepts_list or "（无）"}

### 已有的实体页面（可以交叉引用）
{entities_list or "（无）"}

### 要求

请生成以下 wiki 页面，使用 [[wikilink]] 交叉引用：

1. **Summary 页面** (`wiki/summaries/{source_name}.md`)
   - 源文件的核心要点摘要
   - frontmatter: type=summary, sources=["[[{source_name}]]"]

2. **Concept 页面** (0-N 个, `wiki/concepts/*.md`)
   - 提取文档中的关键概念
   - 每个概念回答"什么是 X"
   - 用 (source: [[summaries/{source_name}]]) 标注来源段落

3. **Entity 页面** (0-N 个, `wiki/entities/*.md`)
   - 提取文档中的人物、项目、组织等实体
   - 用 [[wikilink]] 与已有实体交叉引用

4. **Method 页面** (可选, 仅当满足质量门控时)
   - 提取可执行的方法/步骤
   - 必须满足：可执行、可迁移、非平凡

输出格式请使用 wiki_create_page 工具逐个创建页面，或使用 wiki_commit_ingest 一次性提交所有页面。"""


def ensure_frontmatter(content: str, fm: dict[str, Any]) -> str:
    """Prepend YAML frontmatter to *content* if it does not already have one.

    Parameters
    ----------
    content : str
        Markdown content.
    fm : dict
        Frontmatter fields to write.

    Returns
    -------
    str
        Content guaranteed to start with ``---`` frontmatter.
    """
    if content.startswith("---"):
        return content

    fm_lines: list[str] = []
    for key, value in fm.items():
        if isinstance(value, list):
            items = ", ".join(
                f'"{item}"' if " " in item else str(item) for item in value
            )
            fm_lines.append(f"{key}: [{items}]")
        else:
            fm_lines.append(f"{key}: {value}")

    fm_text = "\n".join(fm_lines)
    return f"---\n{fm_text}\n---\n\n{content}"


# ---------------------------------------------------------------------------
# WikiIngester
# ---------------------------------------------------------------------------


class WikiIngester:
    """Reads raw source files and builds ingestion prompts for the LLM.

    Parameters
    ----------
    client : ObsidianClient
        Obsidian vault client (kept for API parity).
    link_engine : LinkEngine
        Bidirectional link engine.
    wiki_manager : WikiManager
        Wiki structure manager.
    """

    def __init__(
        self,
        client: Any,
        link_engine: LinkEngine,
        wiki_manager: WikiManager,
    ) -> None:
        self.client = client
        self.link_engine = link_engine
        self.wiki_manager = wiki_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, source_path: str) -> dict:
        """Ingest a single raw source file.

        Parameters
        ----------
        source_path : str
            Vault-relative path under ``raw/``.

        Returns
        -------
        dict
            Keys: source, content, existing_wiki_pages, prompt.

        Raises
        ------
        FileNotFoundError
            If the source file does not exist.
        """
        # Read the raw source file
        raw_base = self.wiki_manager._resolve_raw()
        abs_path = raw_base / source_path
        if not abs_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        content = abs_path.read_text(encoding="utf-8")
        source_name = Path(source_path).stem

        # Get existing wiki pages (for cross-referencing)
        existing_pages = self.link_engine.get_note_titles()

        # Get existing summaries (to avoid duplicates)
        wiki_base = self.wiki_manager._resolve_wiki("wiki")
        summaries_dir = wiki_base / "summaries"
        existing_summaries: list[str] = []
        if summaries_dir.exists():
            existing_summaries = [
                f.stem
                for f in summaries_dir.iterdir()
                if f.suffix == ".md"
            ]

        prompt = build_ingest_prompt(
            source_name, content, existing_summaries, existing_pages
        )

        return {
            "source": source_path,
            "content": content,
            "existing_wiki_pages": existing_pages,
            "prompt": prompt,
        }

    def commit_ingest(self, result: dict) -> list[str]:
        """Write the ingestion result to the wiki file system.

        Parameters
        ----------
        result : dict
            Must contain keys:
            - summary: {path, content}
            - concepts (optional): list[{path, content}]
            - entities (optional): list[{path, content}]
            - methods (optional): list[{path, content}]
            - source_path: str

        Returns
        -------
        list[str]
            Paths of created wiki files.
        """
        created_files: list[str] = []
        today = date.today().isoformat()
        wiki_base = self.wiki_manager._resolve_wiki("wiki")

        # --- Write summary --------------------------------------------------
        summary_source_name = Path(result["source_path"]).stem
        summary_content = ensure_frontmatter(
            result["summary"]["content"],
            {
                "type": "summary",
                "sources": [f"[[{summary_source_name}]]"],
                "created": today,
                "updated": today,
                "tags": ["wiki", "summary"],
                "status": "stable",
            },
        )
        linked_summary = self.link_engine.inject_links(summary_content)
        summary_path = wiki_base / "summaries" / result["summary"]["path"]
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(linked_summary, encoding="utf-8")
        created_files.append(f"wiki/summaries/{result['summary']['path']}")

        # Helper to write typed pages (concepts, entities, methods)
        summary_ref = Path(result["summary"]["path"]).stem

        def _write_pages(
            entries: list[dict] | None,
            page_type: str,
            tag: str,
        ) -> None:
            if not entries:
                return
            for entry in entries:
                page_content = ensure_frontmatter(
                    entry["content"],
                    {
                        "type": page_type,
                        "sources": [f"[[summaries/{summary_ref}]]"],
                        "created": today,
                        "updated": today,
                        "tags": ["wiki", page_type],
                        "status": "draft",
                    },
                )
                linked = self.link_engine.inject_links(page_content)
                page_path = wiki_base / page_type / entry["path"]
                page_path.parent.mkdir(parents=True, exist_ok=True)
                page_path.write_text(linked, encoding="utf-8")
                created_files.append(f"wiki/{page_type}/{entry['path']}")

        _write_pages(result.get("concepts"), "concepts", "concept")
        _write_pages(result.get("entities"), "entities", "entity")
        _write_pages(result.get("methods"), "methods", "method")

        # Refresh link cache
        self.link_engine.refresh_title_cache()

        # Update index and log
        pages_for_index: list[dict] = []
        for f in created_files:
            parts = f.split("/")
            page_type = parts[1].rstrip("s") if len(parts) > 1 else "unknown"
            name = Path(f).stem
            pages_for_index.append({"type": page_type, "path": f, "title": name})

        self.wiki_manager.update_index(pages_for_index)
        self.wiki_manager.append_log(
            f"摄入 raw/{result['source_path']} → {', '.join(created_files)}"
        )

        return created_files
