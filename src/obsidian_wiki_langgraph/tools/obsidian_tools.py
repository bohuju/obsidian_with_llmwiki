import json
from langchain_core.tools import tool

from ..core.obsidian_client import ObsidianClient
from ..core.link_engine import LinkEngine
from ..core.wiki_manager import WikiManager
from ..config import VAULT_PATH, WIKI_ROOT

# Module-level singletons
_client: ObsidianClient | None = None
_link_engine: LinkEngine | None = None
_wiki_manager: WikiManager | None = None


def _get_client() -> ObsidianClient:
    global _client
    if _client is None:
        _client = ObsidianClient({"vault_path": str(VAULT_PATH)})
    return _client


def _get_link_engine() -> LinkEngine:
    global _link_engine
    if _link_engine is None:
        _link_engine = LinkEngine(str(VAULT_PATH))
        _link_engine.refresh_title_cache()
    return _link_engine


def _get_wiki_manager() -> WikiManager:
    global _wiki_manager
    if _wiki_manager is None:
        _wiki_manager = WikiManager(str(VAULT_PATH), WIKI_ROOT or None)
    return _wiki_manager


# ─── Obsidian Tools ────────────────────────────────

@tool
def obsidian_list_notes(folder: str | None = None, recursive: bool = False) -> str:
    """List all notes in the Obsidian vault. Optionally filter by folder and recursion."""
    notes = _get_client().list_notes(folder, recursive)
    return json.dumps({"count": len(notes), "notes": notes}, ensure_ascii=False)


@tool
def obsidian_read_note(path: str) -> str:
    """Read the content of a note from the Obsidian vault."""
    result = _get_client().read_note(path)
    if not result["exists"]:
        return f"Note not found: {path}"
    return result["content"]


@tool
def obsidian_write_note(path: str, content: str, auto_link: bool = True) -> str:
    """Create or update a note with optional auto [[wiki-link]] injection."""
    engine = _get_link_engine()
    final_content = engine.inject_links(content) if auto_link else content
    result = _get_client().write_note(path, final_content)
    engine.refresh_title_cache()
    action = "created" if result["created"] else "updated"
    return f"Note {action}: {result['path']}"


@tool
def obsidian_delete_note(path: str) -> str:
    """Delete a note from the Obsidian vault."""
    result = _get_client().delete_note(path)
    if not result["deleted"]:
        return f"Note not found: {path}"
    _get_link_engine().refresh_title_cache()
    return f"Note deleted: {result['path']}"


@tool
def obsidian_search_notes(query: str) -> str:
    """Search notes by keyword (case-insensitive text match)."""
    results = _get_client().search_notes(query)
    return json.dumps({"query": query, "count": len(results), "results": results}, ensure_ascii=False)


@tool
def obsidian_get_backlinks(path: str) -> str:
    """Get all notes that link TO a specific note (backlinks)."""
    backlinks = _get_link_engine().get_backlinks(path)
    return json.dumps({"note": path, "backlinkCount": len(backlinks), "backlinks": backlinks}, ensure_ascii=False)


@tool
def obsidian_get_outlinks(path: str) -> str:
    """Get all notes that a specific note links TO (outgoing links)."""
    outlinks = _get_link_engine().get_outlinks(path)
    return json.dumps({"note": path, "outlinkCount": len(outlinks), "outlinks": outlinks}, ensure_ascii=False)


@tool
def obsidian_get_graph(filter: str | None = None) -> str:
    """Get the complete bidirectional link graph of the vault."""
    graph = _get_link_engine().build_graph()
    g = graph
    if filter:
        lower_filter = filter.lower()
        matching = {n["path"] for n in g["nodes"] if lower_filter in n["path"].lower()}
        related = set(matching)
        for e in g["edges"]:
            if e["source"] in matching:
                related.add(e["target"])
            if e["target"] in matching:
                related.add(e["source"])
        g = {
            "nodes": [n for n in g["nodes"] if n["path"] in related],
            "edges": [e for e in g["edges"] if e["source"] in related and e["target"] in related],
        }
    return json.dumps(
        {"totalNodes": len(g["nodes"]), "totalEdges": len(g["edges"]), "nodes": g["nodes"], "edges": g["edges"]},
        ensure_ascii=False,
    )


@tool
def obsidian_inject_links(content: str) -> str:
    """Analyze content and inject [[wiki-links]] without writing to vault."""
    return _get_link_engine().inject_links(content)


@tool
def obsidian_get_note_titles(folder: str | None = None) -> str:
    """Get all note titles in the vault (for link reference)."""
    titles = _get_link_engine().get_note_titles(folder)
    return json.dumps({"count": len(titles), "titles": titles}, ensure_ascii=False)


@tool
def wiki_create_page(
    type: str,
    title: str,
    content: str,
    sources: list[str],
    auto_link: bool = True,
) -> str:
    """Create a single wiki page with proper frontmatter and bidirectional links."""
    import re
    from datetime import date

    page_types = ["summary", "concept", "entity", "method", "comparison", "analysis"]
    if type not in page_types:
        return f"Invalid type: {type}. Must be one of {page_types}"

    d = date.today().isoformat()
    filename = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff\-_]", "-", title) + ".md"
    page_path = f"wiki/{type}s/{filename}"

    frontmatter = [
        "---",
        f"type: {type}",
        f"sources: [{', '.join(f'[[{s}]]' for s in sources)}]",
        f"created: {d}",
        f"updated: {d}",
        f"tags: [wiki, {type}]",
        "status: draft",
        "---",
        "",
    ]

    full_content = "\n".join(frontmatter) + content
    if auto_link:
        full_content = _get_link_engine().inject_links(full_content)

    result = _get_client().write_note(page_path, full_content)
    _get_link_engine().refresh_title_cache()
    _get_wiki_manager().update_index([{"type": f"{type}s", "path": page_path, "title": title}])

    return f"Wiki page created: {result['path']} (type: {type})"


# All tools list for LangGraph ToolNode
all_tools = [
    obsidian_list_notes,
    obsidian_read_note,
    obsidian_write_note,
    obsidian_delete_note,
    obsidian_search_notes,
    obsidian_get_backlinks,
    obsidian_get_outlinks,
    obsidian_get_graph,
    obsidian_inject_links,
    obsidian_get_note_titles,
    wiki_create_page,
]
