"""Wiki Status node — report wiki status and list sources."""

import json
from ..state import WikiGraphState
from ..core.wiki_manager import WikiManager
from ..config import VAULT_PATH, WIKI_ROOT

_manager: WikiManager | None = None


def _get_manager() -> WikiManager:
    global _manager
    if _manager is None:
        _manager = WikiManager(str(VAULT_PATH), WIKI_ROOT or None)
    return _manager


def wiki_status_node(state: WikiGraphState) -> dict:
    """Report wiki status and optionally list sources."""
    manager = _get_manager()
    status = manager.status()

    result: dict = {
        "wiki_status": status,
        "response": json.dumps(status, ensure_ascii=False, indent=2),
    }

    # Also list sources if requested
    user_input = (state.get("user_input") or "").lower()
    if "source" in user_input or "源文件" in user_input:
        sources = manager.list_sources(state.get("folder"))
        result["sources_list"] = sources

    return result
