"""2 个 OpenCode 驱动的 Wiki Node 函数。"""

from __future__ import annotations

from .core.opencode_runner import OpenCodeError
from .core.opencode_workflows import run_wiki_learn, run_wiki_retrieve
from .subgraph_state import WikiSubgraphState


def wiki_retrieve(state: WikiSubgraphState) -> dict:
    """检索 wiki 并由 OpenCode 直接生成最终结果。

    输入字段：
        wiki_query: 查询问题

    输出字段：
        wiki_answer: 最终回答
        wiki_context: 检索上下文摘要
        wiki_sources: 命中的 wiki 页面
        wiki_needs_ingest: 是否建议补充摄入
        wiki_result: 完整结构化结果
    """
    question = (state.get("wiki_query") or "").strip()
    if not question:
        return {
            "wiki_answer": "",
            "wiki_context": "",
            "wiki_sources": [],
            "wiki_needs_ingest": False,
        }

    try:
        result = run_wiki_retrieve(question)
    except OpenCodeError as exc:
        return {
            "wiki_answer": f"Wiki 检索失败: {exc}",
            "wiki_context": "",
            "wiki_sources": [],
            "wiki_needs_ingest": True,
            "wiki_result": {"error": str(exc)},
        }

    return {
        "wiki_answer": result.get("answer", ""),
        "wiki_context": result.get("context_summary", ""),
        "wiki_sources": result.get("sources", []),
        "wiki_needs_ingest": bool(result.get("needs_ingest", False)),
        "wiki_result": result,
    }


def wiki_learn(state: WikiSubgraphState) -> dict:
    """获取新知识，交给 OpenCode 规范 raw 并更新 wiki 编译层。

    输入字段：
        content: 新知识原文
        content_title: 内容标题
        raw_folder: 可选目录 hint

    输出字段：
        raw_folder: OpenCode 选择的 raw 目录
        raw_saved_path: 写入后的 raw 路径
        ingest_result: 编译结果摘要
        created_wiki_pages: 本次创建的 wiki 页面
        learn_result: 完整结构化结果
    """
    content = state.get("content")
    if not content:
        return {
            "ingest_result": "Error: no content provided",
            "created_wiki_pages": [],
        }

    try:
        result = run_wiki_learn(
            content,
            title=state.get("content_title"),
            raw_folder_hint=state.get("raw_folder"),
        )
    except OpenCodeError as exc:
        return {
            "ingest_result": f"OpenCode learn failed: {exc}",
            "created_wiki_pages": [],
            "learn_result": {"error": str(exc)},
        }

    return {
        "raw_folder": result.get("raw_folder"),
        "raw_saved_path": result.get("raw_saved_path"),
        "ingest_result": result.get("ingest_summary", ""),
        "created_wiki_pages": result.get("created_wiki_pages", []),
        "learn_result": result,
    }
