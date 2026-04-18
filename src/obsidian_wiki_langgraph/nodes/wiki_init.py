"""Wiki Init node — initialize wiki directory structure."""

from ..state import WikiGraphState
from ..core.wiki_manager import WikiManager
from ..core.link_engine import LinkEngine
from ..config import VAULT_PATH, WIKI_ROOT

_manager: WikiManager | None = None
_engine: LinkEngine | None = None


def _get_manager() -> WikiManager:
    global _manager
    if _manager is None:
        _manager = WikiManager(str(VAULT_PATH), WIKI_ROOT or None)
    return _manager


def _get_engine() -> LinkEngine:
    global _engine
    if _engine is None:
        _engine = LinkEngine(str(VAULT_PATH))
    return _engine


def wiki_init_node(state: WikiGraphState) -> dict:
    """Initialize the wiki directory structure."""
    manager = _get_manager()
    engine = _get_engine()

    result = manager.init()
    engine.refresh_title_cache()

    created = ", ".join(result["created"])
    files = ", ".join(result["files"])

    return {
        "response": f"Wiki initialized!\n\nDirectories created: {created}\nFiles created: {files}",
    }
