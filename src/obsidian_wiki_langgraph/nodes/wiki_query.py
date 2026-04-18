"""Wiki Query node — search wiki knowledge base and build answer prompt."""

from ..state import WikiGraphState
from ..core.link_engine import LinkEngine
from ..core.wiki_manager import WikiManager
from ..core.wiki_querier import WikiQuerier
from ..config import VAULT_PATH, WIKI_ROOT

_querier: WikiQuerier | None = None


def _get_querier() -> WikiQuerier:
    global _querier
    if _querier is None:
        manager = WikiManager(str(VAULT_PATH), WIKI_ROOT or None)
        engine = LinkEngine(str(VAULT_PATH))
        _querier = WikiQuerier(manager, engine)
    return _querier


def wiki_query_node(state: WikiGraphState) -> dict:
    """Query the wiki knowledge base."""
    question = state.get("question") or state.get("user_input", "")
    if not question:
        return {"error": "No question provided", "response": "请提供查询问题"}

    querier = _get_querier()
    result = querier.query(question)

    pages_info = "\n".join(
        f"  - {p['path']} ({p.get('title', 'untitled')}) [{p.get('relevance', '')}]"
        for p in result.get("relevant_pages", [])
    ) or "No relevant pages found."

    return {
        "query_result": result,
        "response": (
            f"## Query: {question}\n\n"
            f"### Relevant Pages\n{pages_info}\n\n"
            f"### Answer Prompt\n\n{result['prompt']}"
        ),
    }
