"""预装配的 Wiki 子图 — 可整体嵌入到父 LangGraph 工作流。"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .subgraph_state import WikiSubgraphState
from .wiki_nodes import wiki_learn, wiki_retrieve


def _route_wiki(state: WikiSubgraphState) -> str:
    """根据 state 内容决定走学习流程还是检索流程。"""
    route = state.get("wiki_route")
    if route:
        if route in {"write", "write_and_ingest", "learn"}:
            return "learn"
        if route in {"query", "retrieve"}:
            return "retrieve"

    # 自动推断：有 content → 学习，有 wiki_query → 检索
    if state.get("content"):
        return "learn"
    if state.get("wiki_query"):
        return "retrieve"
    return "retrieve"


def build_wiki_subgraph():
    """构建 wiki 子图。

    两种流程：
    1. learn: content → wiki_learn → END
    2. retrieve: wiki_query → wiki_retrieve → END

    通过 wiki_route 字段或自动推断选择流程。

    用法：
        wiki_sub = build_wiki_subgraph()
        parent_graph.add_node("wiki", wiki_sub)
        parent_graph.add_edge("upstream", "wiki")
        parent_graph.add_edge("wiki", "downstream")
    """
    g = StateGraph(WikiSubgraphState)

    g.add_node("wiki_learn", wiki_learn)
    g.add_node("wiki_retrieve", wiki_retrieve)

    # 入口路由
    g.add_conditional_edges(START, _route_wiki, {
        "learn": "wiki_learn",
        "retrieve": "wiki_retrieve",
    })

    g.add_edge("wiki_learn", END)
    g.add_edge("wiki_retrieve", END)

    return g.compile()


# 预编译子图实例
wiki_subgraph = build_wiki_subgraph()
