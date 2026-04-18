"""3 个独立的 Wiki Node 函数 — 可直接 add_node 到任何父 LangGraph。"""

from __future__ import annotations

import re
from pathlib import Path

from .subgraph_state import WikiSubgraphState
from .core.obsidian_client import ObsidianClient
from .core.link_engine import LinkEngine
from .core.wiki_manager import WikiManager
from .core.wiki_ingester import WikiIngester
from .core.wiki_querier import WikiQuerier
from .config import VAULT_PATH, WIKI_ROOT

# ─── 单例管理 ───────────────────────────────────────

_client: ObsidianClient | None = None
_engine: LinkEngine | None = None
_manager: WikiManager | None = None


def _get_client() -> ObsidianClient:
    global _client
    if _client is None:
        _client = ObsidianClient({"vault_path": str(VAULT_PATH)})
    return _client


def _get_engine() -> LinkEngine:
    global _engine
    if _engine is None:
        _engine = LinkEngine(str(VAULT_PATH))
        _engine.refresh_title_cache()
    return _engine


def _get_manager() -> WikiManager:
    global _manager
    if _manager is None:
        _manager = WikiManager(str(VAULT_PATH), WIKI_ROOT or None)
    return _manager


# ─── Node 1: wiki_write_raw ─────────────────────────

def wiki_write_raw(state: WikiSubgraphState) -> dict:
    """将上游节点产出的内容保存到 raw/ 目录。

    输入字段：
        content: 要保存的内容（必需）
        content_title: 标题，用作文件名（必需）
        raw_folder: raw/ 子目录，默认 "general"

    输出字段：
        raw_saved_path: 保存后的相对路径（如 "tech/rust-async.md"）
    """
    content = state.get("content")
    title = state.get("content_title", "untitled")

    if not content:
        return {"raw_saved_path": None, "ingest_result": "Error: no content provided"}

    folder = state.get("raw_folder") or "general"

    # 清理标题为合法文件名
    safe_title = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff\-_]", "-", title)
    filename = f"{safe_title}.md" if not safe_title.endswith(".md") else safe_title

    # 写入 raw/folder/filename
    raw_path = f"raw/{folder}/{filename}"
    client = _get_client()
    result = client.write_note(raw_path, content)

    return {"raw_saved_path": raw_path}


# ─── Node 2: wiki_auto_ingest ───────────────────────

def wiki_auto_ingest(state: WikiSubgraphState) -> dict:
    """自动摄入 raw 文件为 wiki 页面。

    输入字段：
        raw_saved_path: raw/ 中的文件路径（由 wiki_write_raw 输出）

    输出字段：
        ingest_result: 摄入结果摘要（创建了哪些页面）
    """
    raw_path = state.get("raw_saved_path")
    if not raw_path:
        return {"ingest_result": "Error: no raw_saved_path provided"}

    # raw_path 格式: "raw/tech/rust-async.md" → source_path: "tech/rust-async.md"
    source_path = raw_path.replace("raw/", "", 1) if raw_path.startswith("raw/") else raw_path

    client = _get_client()
    engine = _get_engine()
    manager = _get_manager()
    ingester = WikiIngester(client, engine, manager)

    try:
        # 读取源文件
        ingest_result = ingester.ingest(source_path)
        source_content = ingest_result.get("content", "")

        # 自动生成 summary
        title = state.get("content_title") or Path(source_path).stem
        date_str = Path(source_path).stem  # fallback

        from datetime import date
        date_str = date.today().isoformat()

        summary_content = (
            f"# {title} 摘要\n\n"
            f"自动摄入自 raw/{source_path}\n\n"
            f"## 核心要点\n\n"
            f"{source_content[:2000]}"
        )

        # 提取关键概念（简单版：从标题和前几段提取）
        concepts = _extract_concepts(source_content, title)

        # 提交摄入
        created_files = ingester.commit_ingest({
            "source_path": source_path,
            "summary": {"path": f"{Path(source_path).stem}.md", "content": summary_content},
            "concepts": concepts,
            "entities": [],
            "methods": [],
        })

        engine.refresh_title_cache()

        files_str = ", ".join(created_files)
        return {"ingest_result": f"Auto-ingested: {files_str}"}

    except Exception as e:
        return {"ingest_result": f"Ingest error: {e}"}


def _extract_concepts(content: str, source_title: str) -> list[dict]:
    """从内容中提取关键概念（简单版本，用于自动摄入）。"""
    concepts = []
    seen = set()

    # 提取 ## 标题作为概念
    for match in re.finditer(r"^##\s+(.+)$", content, re.MULTILINE):
        title = match.group(1).strip()
        if title not in seen and len(title) >= 2:
            seen.add(title)
            safe_name = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff\-_]", "-", title)
            concepts.append({
                "path": f"{safe_name}.md",
                "content": f"# {title}\n\n关于 {title} 的概念说明。(source: [[summaries/{re.sub(r'[^a-zA-Z0-9\\u4e00-\\u9fff\\-_]', '-', source_title)}]])\n",
            })

    return concepts[:5]  # 最多 5 个概念


# ─── Node 3: wiki_query ─────────────────────────────

def wiki_query(state: WikiSubgraphState) -> dict:
    """查询 wiki 知识库，结果输出给下游节点。

    输入字段：
        wiki_query: 查询问题

    输出字段：
        wiki_context: wiki 查询结果文本（给下游节点用）
    """
    question = state.get("wiki_query")
    if not question:
        return {"wiki_context": ""}

    engine = _get_engine()
    manager = _get_manager()
    querier = WikiQuerier(manager, engine)

    result = querier.query(question)

    relevant = result.get("relevant_pages", [])
    if not relevant:
        return {"wiki_context": f"Wiki 中未找到与 \"{question}\" 相关的内容。"}

    # 组装上下文给下游节点
    context_parts = []
    for page in relevant:
        title = page.get("title", page.get("path", "unknown"))
        content = page.get("content", "")
        context_parts.append(f"### {title}\n\n{content[:800]}")

    context = "\n\n---\n\n".join(context_parts)
    return {"wiki_context": context}
