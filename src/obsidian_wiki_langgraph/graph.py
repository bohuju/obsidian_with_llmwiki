"""LangGraph StateGraph — Obsidian Wiki Knowledge Compilation System."""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from .state import WikiGraphState
from .router import router_node, route_decision
from .nodes.wiki_init import wiki_init_node
from .nodes.wiki_ingest import wiki_ingest_node
from .nodes.wiki_query import wiki_query_node
from .nodes.wiki_lint import wiki_lint_node
from .nodes.wiki_status import wiki_status_node
from .tools import all_tools


def _should_use_tools(state: WikiGraphState) -> str:
    """Check if the last LLM message contains tool calls."""
    messages = state.get("messages", [])
    if messages:
        last = messages[-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
    return "end"


def _tool_call_node(state: WikiGraphState) -> dict:
    """Execute a direct tool call from user input without requiring an LLM."""
    import json
    from langchain_core.messages import AIMessage, ToolCall
    from .tools.obsidian_tools import (
        obsidian_list_notes, obsidian_read_note, obsidian_write_note,
        obsidian_delete_note, obsidian_search_notes, obsidian_get_backlinks,
        obsidian_get_outlinks, obsidian_get_graph, obsidian_inject_links,
        obsidian_get_note_titles,
    )

    user_input = state.get("user_input", "").lower()
    response = ""

    if "backlink" in user_input:
        import re
        m = re.search(r"backlink[s]?\s+(\S+)", user_input)
        if m:
            path = m.group(1)
            response = obsidian_get_backlinks.invoke({"path": path})
    elif "outlink" in user_input:
        import re
        m = re.search(r"outlink[s]?\s+(\S+)", user_input)
        if m:
            path = m.group(1)
            response = obsidian_get_outlinks.invoke({"path": path})
    elif "graph" in user_input:
        response = obsidian_get_graph.invoke({})
    elif "search" in user_input:
        import re
        m = re.search(r"search\s+(.+)", user_input)
        if m:
            response = obsidian_search_notes.invoke({"query": m.group(1)})
    elif "read" in user_input or "读取" in user_input:
        import re
        m = re.search(r"(?:read|读取)\s+(\S+)", user_input)
        if m:
            response = obsidian_read_note.invoke({"path": m.group(1)})
    elif "list" in user_input or "列出" in user_input:
        response = obsidian_list_notes.invoke({"recursive": True})
    elif "title" in user_input:
        response = obsidian_get_note_titles.invoke({})

    if not response:
        response = "Obsidian tool operation. Provide more specific input (e.g., 'search fuzzing', 'backlinks path', 'read 300-Memory/MEMORY.md')."

    return {"response": response}


def build_graph():
    """Build and compile the LangGraph StateGraph.

    Returns a CompiledGraph that can be invoked with:
        result = graph.invoke({"user_input": "...", "messages": []})
    """
    g = StateGraph(WikiGraphState)

    # ─── Nodes ─────────────────────────────────────
    g.add_node("router", router_node)
    g.add_node("wiki_init", wiki_init_node)
    g.add_node("wiki_ingest", wiki_ingest_node)
    g.add_node("wiki_query", wiki_query_node)
    g.add_node("wiki_lint", wiki_lint_node)
    g.add_node("wiki_status", wiki_status_node)
    g.add_node("tool_call_handler", _tool_call_node)
    g.add_node("tool_executor", ToolNode(all_tools))
    g.add_node("end_node", lambda s: {"response": s.get("response", "Done.")})

    # ─── Edges ─────────────────────────────────────
    # Entry → router
    g.add_edge(START, "router")

    # Router → wiki operation nodes (conditional)
    g.add_conditional_edges("router", route_decision, {
        "init": "wiki_init",
        "ingest": "wiki_ingest",
        "query": "wiki_query",
        "lint": "wiki_lint",
        "status": "wiki_status",
        "tool_call": "tool_call_handler",
        "end": "end_node",
    })

    # Wiki operation nodes → END (each produces a response)
    for n in ["wiki_init", "wiki_ingest", "wiki_query", "wiki_lint", "wiki_status", "tool_call_handler"]:
        g.add_edge(n, "end_node")

    # Tool executor (for LLM-based tool calls) → END
    g.add_edge("tool_executor", "end_node")

    # End → END
    g.add_edge("end_node", END)

    return g.compile()


# Compiled graph instance
app = build_graph()


def main():
    """CLI entry point for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m obsidian_wiki_langgraph.graph <user_input>")
        print("Examples:")
        print('  python -m obsidian_wiki_langgraph.graph "初始化 wiki"')
        print('  python -m obsidian_wiki_langgraph.graph "wiki 状态"')
        print('  python -m obsidian_wiki_langgraph.graph "什么是 Fuzzing"')
        sys.exit(1)

    user_input = " ".join(sys.argv[1:])
    print(f"Input: {user_input}\n")

    result = app.invoke({"user_input": user_input, "messages": []})
    print(result.get("response", result.get("error", "No response")))


if __name__ == "__main__":
    main()
