from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class WikiGraphState(TypedDict, total=False):
    """State passed between LangGraph nodes."""

    # LLM conversation
    messages: Annotated[list[BaseMessage], add_messages]

    # Routing
    user_input: str
    route: Literal[
        "init", "ingest", "query", "lint", "status",
        "tool_call", "end",
    ]

    # Wiki operation parameters
    source_path: Optional[str]
    question: Optional[str]
    write_report: Optional[bool]
    folder: Optional[str]

    # Wiki operation results
    wiki_status: Optional[dict]
    ingest_result: Optional[dict]
    query_result: Optional[dict]
    lint_result: Optional[dict]
    sources_list: Optional[list]

    # Commit ingest payload
    summary: Optional[dict]
    concepts: Optional[list[dict]]
    entities: Optional[list[list[dict]]]
    methods: Optional[list[list[dict]]]

    # Response
    response: Optional[str]
    error: Optional[str]
