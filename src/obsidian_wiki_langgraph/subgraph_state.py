"""通用 Wiki 子图 State — 父 graph 继承此 State 即可使用两个 OpenCode 节点。"""

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict


class WikiSubgraphState(TypedDict, total=False):
    """Wiki 子图的输入输出字段。

    父 graph 的 State 只需包含这些字段（或继承此类），
    即可直接使用 wiki_learn / wiki_retrieve 节点。

    输入字段（由上游节点填入）：
        content: 上游节点产出的内容
        content_title: 内容标题（供 OpenCode 规范文件名）
        raw_folder: 保存到 raw/ 的子目录 hint
        wiki_query: 要查询 wiki 的问题

    输出字段（由 wiki 节点填入，传递给下游节点）：
        wiki_answer: 基于 wiki 生成的最终回答
        wiki_context: 检索上下文摘要
        wiki_sources: 本次命中的 wiki 页面
        wiki_needs_ingest: 是否建议继续补充摄入
        raw_saved_path: 内容保存到 raw/ 后的相对路径
        created_wiki_pages: 编译后创建的 wiki 页面
        ingest_result: 摄入结果摘要
        wiki_route: 子图内部路由（"learn" | "retrieve"）
    """

    # ─── 输入 ──────────────────────────────────────
    content: Optional[str]
    content_title: Optional[str]
    raw_folder: Optional[str]       # "tech" | "work" | "reading" | "general" | "assets"
    wiki_query: Optional[str]

    # ─── 输出 ──────────────────────────────────────
    wiki_context: Optional[str]
    wiki_answer: Optional[str]
    wiki_sources: Optional[list[dict]]
    wiki_needs_ingest: Optional[bool]
    raw_saved_path: Optional[str]
    created_wiki_pages: Optional[list[str]]
    ingest_result: Optional[str]
    learn_result: Optional[dict]
    wiki_result: Optional[dict]

    # ─── 子图路由 ──────────────────────────────────
    wiki_route: Optional[str]       # "learn" | "retrieve"
