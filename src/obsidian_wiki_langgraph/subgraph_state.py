"""通用 Wiki 子图 State — 父 graph 继承此 State 即可使用 wiki 节点。"""

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict


class WikiSubgraphState(TypedDict, total=False):
    """Wiki 子图的输入输出字段。

    父 graph 的 State 只需包含这些字段（或继承此类），
    即可直接使用 wiki_write_raw / wiki_auto_ingest / wiki_query 节点。

    输入字段（由上游节点填入）：
        content: 上游节点产出的内容
        content_title: 内容标题（用作 raw/ 文件名）
        raw_folder: 保存到 raw/ 的子目录（默认 "general"）
        wiki_query: 要查询 wiki 的问题

    输出字段（由 wiki 节点填入，传递给下游节点）：
        wiki_context: wiki 查询结果文本
        raw_saved_path: 内容保存到 raw/ 后的相对路径
        ingest_result: 摄入结果摘要
        wiki_route: 子图内部路由（"write" | "query" | "write_and_ingest"）
    """

    # ─── 输入 ──────────────────────────────────────
    content: Optional[str]
    content_title: Optional[str]
    raw_folder: Optional[str]       # "tech" | "work" | "reading" | "general"
    wiki_query: Optional[str]

    # ─── 输出 ──────────────────────────────────────
    wiki_context: Optional[str]
    raw_saved_path: Optional[str]
    ingest_result: Optional[str]

    # ─── 子图路由 ──────────────────────────────────
    wiki_route: Optional[str]       # "write" | "query" | "write_and_ingest"
