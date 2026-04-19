"""Wiki Ingest node — use OpenCode to learn new knowledge or ingest raw files."""

from ..core.opencode_runner import OpenCodeError
from ..core.opencode_workflows import run_wiki_ingest_source, run_wiki_learn
from ..state import WikiGraphState


def wiki_ingest_node(state: WikiGraphState) -> dict:
    """Learn new content or compile an existing raw source through OpenCode."""
    content = state.get("content")
    source_path = state.get("source_path", "")

    if not content and not source_path:
        return {"error": "No content or source_path provided", "response": "请提供 content 或 raw 源文件路径"}

    try:
        if content:
            result = run_wiki_learn(
                content,
                title=state.get("content_title"),
                raw_folder_hint=state.get("raw_folder"),
            )
            return {
                "raw_saved_path": result.get("raw_saved_path"),
                "created_wiki_pages": result.get("created_wiki_pages", []),
                "learn_result": result,
                "ingest_result": result.get("ingest_summary", ""),
                "response": result.get("ingest_summary", ""),
            }

        result = run_wiki_ingest_source(source_path)
        return {
            "created_wiki_pages": result.get("created_wiki_pages", []),
            "ingest_result": result.get("ingest_summary", ""),
            "response": result.get("ingest_summary", ""),
        }
    except OpenCodeError as exc:
        return {"error": str(exc), "response": f"Ingest error: {exc}"}
