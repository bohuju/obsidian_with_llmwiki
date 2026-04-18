"""预装配的 Wiki 子图 — 可整体嵌入到父 LangGraph 工作流。"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .subgraph_state import WikiSubgraphState
from .wiki_nodes import wiki_write_raw, wiki_auto_ingest, wiki_query


def _route_wiki(state: WikiSubgraphState) -> str:
    """根据 state 内容决定走写入流程还是查询流程。"""
    route = state.get("wiki_route")
    if route:
        return route

    # 自动推断：有 content → 写入，有 wiki_query → 查询
    if state.get("content"):
        return "write_and_ingest"
    if state.get("wiki_query"):
        return "query"
    return "query"


def build_wiki_subgraph():
    """构建 wiki 子图。

    两种流程：
    1. write_and_ingest: content → wiki_write_raw → wiki_auto_ingest → END
    2. query: wiki_query → END

    通过 wiki_route 字段或自动推断选择流程。

    用法：
        wiki_sub = build_wiki_subgraph()
        parent_graph.add_node("wiki", wiki_sub)
        parent_graph.add_edge("upstream", "wiki")
        parent_graph.add_edge("wiki", "downstream")
    """
    g = StateGraph(WikiSubgraphState)

    g.add_node("wiki_write_raw", wiki_write_raw)
    g.add_node("wiki_auto_ingest", wiki_auto_ingest)
    g.add_node("wiki_query", wiki_query)

    # 入口路由
    g.add_conditional_edges(START, _route_wiki, {
        "write": "wiki_write_raw",
        "write_and_ingest": "wiki_write_raw",
        "query": "wiki_query",
    })

    # 写入流程
    g.add_conditional_edges("wiki_write_raw", lambda s: (
        "ingest" if s.get("wiki_route") != "write" else "end"
    ), {
        "ingest": "wiki_auto_ingest",
        "end": END,
    })
    g.add_edge("wiki_auto_ingest", END)

    # 查询流程
    g.add_edge("wiki_query", END)

    return g.compile()


# 预编译子图实例
wiki_subgraph = build_wiki_subgraph()
