"""Wiki Query node — use OpenCode to retrieve wiki context and final answer."""

from ..core.opencode_runner import OpenCodeError
from ..core.opencode_workflows import run_wiki_retrieve
from ..state import WikiGraphState


def wiki_query_node(state: WikiGraphState) -> dict:
    """Query the wiki knowledge base through OpenCode + MCP."""
    question = state.get("question") or state.get("user_input", "")
    if not question:
        return {"error": "No question provided", "response": "请提供查询问题"}

    try:
        result = run_wiki_retrieve(question)
    except OpenCodeError as exc:
        return {
            "error": str(exc),
            "response": f"Wiki query failed: {exc}",
        }

    return {
        "query_result": result,
        "wiki_answer": result.get("answer", ""),
        "wiki_context": result.get("context_summary", ""),
        "wiki_sources": result.get("sources", []),
        "response": result.get("answer", ""),
    }
