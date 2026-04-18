"""Wiki Ingest node — ingest raw source files into wiki pages."""

from ..state import WikiGraphState
from ..core.obsidian_client import ObsidianClient
from ..core.link_engine import LinkEngine
from ..core.wiki_manager import WikiManager
from ..core.wiki_ingester import WikiIngester
from ..config import VAULT_PATH, WIKI_ROOT

_ingester: WikiIngester | None = None


def _get_ingester() -> WikiIngester:
    global _ingester
    if _ingester is None:
        client = ObsidianClient({"vault_path": str(VAULT_PATH)})
        engine = LinkEngine(str(VAULT_PATH))
        engine.refresh_title_cache()
        manager = WikiManager(str(VAULT_PATH), WIKI_ROOT or None)
        _ingester = WikiIngester(client, engine, manager)
    return _ingester


def wiki_ingest_node(state: WikiGraphState) -> dict:
    """Ingest a raw source file into wiki pages.

    Two modes:
    1. If summary is in state → commit mode (write pages)
    2. Otherwise → ingest mode (read source, return prompt)
    """
    ingester = _get_ingester()

    # Commit mode
    if state.get("summary"):
        try:
            created_files = ingester.commit_ingest({
                "source_path": state.get("source_path", ""),
                "summary": state["summary"],
                "concepts": state.get("concepts"),
                "entities": state.get("entities"),
                "methods": state.get("methods"),
            })
            files_str = "\n".join(f"  - {f}" for f in created_files)
            return {
                "response": f"Ingest committed! Created {len(created_files)} wiki pages:\n{files_str}",
                "ingest_result": {"created_files": created_files},
            }
        except Exception as e:
            return {"error": str(e), "response": f"Ingest commit error: {e}"}

    # Ingest mode
    source_path = state.get("source_path", "")
    if not source_path:
        return {"error": "No source_path provided", "response": "请指定要摄入的 raw 源文件路径"}

    try:
        result = ingester.ingest(source_path)
        pages_info = "\n".join(
            f"  - {p['path']} ({p.get('title', 'untitled')})"
            for p in result.get("existing_wiki_pages", [])
        )
        return {
            "ingest_result": result,
            "response": (
                f"## Source: {result['source']}\n\n"
                f"### Ingest Prompt\n\n{result['prompt']}\n\n"
                f"### Existing Wiki Pages\n{pages_info or 'None'}"
            ),
        }
    except Exception as e:
        return {"error": str(e), "response": f"Ingest error: {e}"}
