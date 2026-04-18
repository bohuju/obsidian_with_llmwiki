"""
示例：将 Wiki 子图嵌入到父 LangGraph 工作流。

演示两种用法：
1. 独立 node 函数：直接 add_node 到父 graph
2. 子图模式：整体嵌入

运行方式：
    python examples/parent_workflow.py
"""

from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

# 导入 wiki 节点
from obsidian_wiki_langgraph.subgraph_state import WikiSubgraphState
from obsidian_wiki_langgraph.wiki_nodes import wiki_write_raw, wiki_auto_ingest, wiki_query
from obsidian_wiki_langgraph.subgraph import build_wiki_subgraph


# ═══════════════════════════════════════════════════
# 方式 1：使用独立 node 函数
# ═══════════════════════════════════════════════════

class MyWorkflowState(WikiSubgraphState, TypedDict, total=False):
    """父工作流 State — 继承 WikiSubgraphState 即可使用 wiki 节点。"""
    messages: Annotated[list[BaseMessage], add_messages]
    step: Optional[str]


def mock_scraper(state: MyWorkflowState) -> dict:
    """模拟上游节点：爬取/生成内容。"""
    return {
        "content": """# Rust Async Programming

## async/await

Rust 的 async/await 语法允许编写异步代码，看起来像同步代码。
async fn 返回一个 Future，.await 会暂停执行直到 Future 完成。

## Tokio Runtime

Tokio 是 Rust 最流行的异步运行时。提供：
- 异步 I/O（TCP, UDP, 文件系统）
- 任务调度（spawn, JoinHandle）
- 定时器和通道

## Pin 和 Unpin

Pin 确保 Future 不会被移动到内存中的其他位置，
这对于自引用结构体至关重要。
""",
        "content_title": "rust-async",
        "raw_folder": "tech",
    }


def mock_llm(state: MyWorkflowState) -> dict:
    """模拟下游节点：使用 wiki 查询结果。"""
    wiki_context = state.get("wiki_context", "")
    ingest_result = state.get("ingest_result", "")

    response_parts = []
    if ingest_result:
        response_parts.append(f"Wiki 摄入结果: {ingest_result}")
    if wiki_context:
        response_parts.append(f"Wiki 查询上下文:\n{wiki_context[:500]}")

    return {"response": "\n\n".join(response_parts) or "No wiki data."}


def build_parent_graph():
    """构建使用独立 node 函数的父工作流。"""
    g = StateGraph(MyWorkflowState)

    g.add_node("scraper", mock_scraper)
    g.add_node("save_to_raw", wiki_write_raw)
    g.add_node("ingest", wiki_auto_ingest)
    g.add_node("llm", mock_llm)

    g.add_edge(START, "scraper")
    g.add_edge("scraper", "save_to_raw")
    g.add_edge("save_to_raw", "ingest")
    g.add_edge("ingest", "llm")
    g.add_edge("llm", END)

    return g.compile()


# ═══════════════════════════════════════════════════
# 方式 2：使用子图
# ═══════════════════════════════════════════════════

def build_parent_with_subgraph():
    """构建使用 wiki 子图的父工作流。"""
    g = StateGraph(MyWorkflowState)

    wiki_sub = build_wiki_subgraph()

    g.add_node("scraper", mock_scraper)
    g.add_node("wiki", wiki_sub)           # 子图作为单个节点
    g.add_node("llm", mock_llm)

    g.add_edge(START, "scraper")
    g.add_edge("scraper", "wiki")
    g.add_edge("wiki", "llm")
    g.add_edge("llm", END)

    return g.compile()


# ═══════════════════════════════════════════════════
# 方式 3：查询模式（在下游节点前查询 wiki）
# ═══════════════════════════════════════════════════

def build_query_workflow():
    """构建查询模式工作流：先查 wiki，结果传给 LLM。"""

    class QueryState(WikiSubgraphState, TypedDict, total=False):
        response: Optional[str]

    def mock_downstream(state: QueryState) -> dict:
        wiki_context = state.get("wiki_context", "无 wiki 结果")
        return {"response": f"基于 wiki 知识回答:\n{wiki_context[:300]}"}

    g = StateGraph(QueryState)
    g.add_node("query_wiki", wiki_query)
    g.add_node("answer", mock_downstream)

    g.add_edge(START, "query_wiki")
    g.add_edge("query_wiki", "answer")
    g.add_edge("answer", END)

    return g.compile()


# ═══════════════════════════════════════════════════
# 运行演示
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("方式 1：独立 node 函数 — 写入 + 摄入流程")
    print("=" * 60)
    graph1 = build_parent_graph()
    result1 = graph1.invoke({})
    print(f"raw_saved_path: {result1.get('raw_saved_path')}")
    print(f"ingest_result: {result1.get('ingest_result')}")
    print()

    print("=" * 60)
    print("方式 3：查询模式 — 查 wiki 给下游节点")
    print("=" * 60)
    graph3 = build_query_workflow()
    result3 = graph3.invoke({"wiki_query": "什么是 Fuzzing"})
    print(result3.get("response", "")[:500])
