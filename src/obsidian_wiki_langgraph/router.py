"""Router node — analyzes user input and determines which wiki operation to execute."""

from __future__ import annotations

from .state import WikiGraphState

# Keyword → route mapping (from CLAUDE.md trigger rules)
ROUTE_KEYWORDS: dict[str, list[str]] = {
    "init": ["wiki_init", "初始化 wiki", "初始化知识库", "init wiki"],
    "ingest": ["wiki_ingest", "摄入", "编译", "学习这篇", "加入 wiki", "raw/", "ingest"],
    "query": ["wiki_query", "什么是", "怎么说", "帮我查", "wiki 里", "query"],
    "lint": ["wiki_lint", "健康检查", "检查 wiki", "lint"],
    "status": ["wiki_status", "wiki 状态", "几个页面", "列出源文件", "status", "get_sources"],
}


def router_node(state: WikiGraphState) -> dict:
    """Route user input to the appropriate wiki operation node."""
    user_input = state.get("user_input", "")
    if not user_input and state.get("messages"):
        last = state["messages"][-1]
        if hasattr(last, "content"):
            user_input = str(last.content)

    lower_input = user_input.lower()

    # Keyword matching
    for route, keywords in ROUTE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in lower_input:
                result: dict = {"route": route}

                # Extract parameters based on route
                if route == "ingest":
                    # Try to extract source path
                    import re
                    m = re.search(r"raw/(\S+\.md)", user_input)
                    if m:
                        result["source_path"] = m.group(1)
                    else:
                        m = re.search(r"['\"]?(\w+/\S+\.md)['\"]?", user_input)
                        if m:
                            result["source_path"] = m.group(1)

                elif route == "query":
                    result["question"] = user_input

                return result

    # Check for general obsidian operations
    obsidian_keywords = ["笔记", "note", "read", "write", "search", "backlink", "graph", "链接"]
    for kw in obsidian_keywords:
        if kw in lower_input:
            return {"route": "tool_call"}

    return {"route": "end"}


def route_decision(state: WikiGraphState) -> str:
    """Conditional edge function: returns the route from state."""
    route = state.get("route", "end")
    return route if route else "end"
