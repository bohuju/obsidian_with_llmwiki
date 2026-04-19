"""OpenCode-backed wiki retrieval and ingestion workflows."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .opencode_runner import (
    JSON_END_MARKER,
    JSON_START_MARKER,
    run_opencode_json,
)


def _derive_title(content: str, fallback: str = "untitled") -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
        if stripped:
            return stripped[:80]
    return fallback


def run_wiki_retrieve(question: str) -> dict:
    """Use OpenCode + MCP tools to query wiki and generate the final answer."""
    prompt = f"""你现在在执行一个“wiki 检索节点”。

必须遵守：
1. 必须调用 MCP server `obsidian-wiki` 的 `wiki_query` 工具。
2. 基于 `wiki_query` 返回的内容完成最终回答。
3. 不要使用 bash/read/edit/grep 等其他工具，除非 `wiki_query` 工具不可用。
4. 回答必须只基于 wiki 内容；如果 wiki 信息不足，要明确说明，并将 `needs_ingest` 设为 true。
5. 最终输出必须是一个 JSON 对象，并且只能放在下面两个 marker 之间，marker 外不能输出任何别的内容。

问题：
{question}

输出 JSON schema：
{{
  "question": "原问题",
  "answer": "基于 wiki 的最终回答",
  "context_summary": "本次检索到的上下文摘要",
  "sources": [
    {{
      "path": "wiki/...md",
      "title": "页面标题",
      "relevance": "匹配度说明"
    }}
  ],
  "needs_ingest": false,
  "suggested_sources_to_ingest": ["当 needs_ingest=true 时给出建议摄入主题"]
}}

严格按以下格式输出：
{JSON_START_MARKER}
<JSON>
{JSON_END_MARKER}
"""
    return run_opencode_json(prompt)


def run_wiki_learn(
    content: str,
    *,
    title: str | None = None,
    raw_folder_hint: str | None = None,
) -> dict:
    """Use OpenCode + MCP tools to store raw knowledge and update the wiki."""
    final_title = (title or "").strip() or _derive_title(content)
    normalized_hint = (raw_folder_hint or "").strip() or None

    attachment_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            prefix="wiki_learn_",
            delete=False,
            encoding="utf-8",
        ) as temp_file:
            temp_file.write(content)
            attachment_path = temp_file.name

        prompt = f"""你现在在执行一个“新知识摄入节点”。

已附加一个 markdown 文件，它就是要进入知识库的原始内容。你必须使用 MCP server `obsidian-wiki` 完成整个流程。

必须遵守：
1. 先判断 raw 存放目录，只能从 `tech`, `work`, `reading`, `general`, `assets` 中选择一个。
2. 如果 `raw_folder_hint` 非空且合理，优先采用；hint={normalized_hint or "null"}。
3. 基于标题生成规范文件名；标题是：`{final_title}`。
4. 原始内容必须保存到 `raw/<folder>/<filename>.md`。
5. 写 raw 文件时必须调用 `obsidian_write_note`，并设置 `autoLink=false`。
6. 不能覆盖已有 raw 文件；如果冲突，请改用带日期或序号的新文件名。
7. raw 文件写入后，必须调用 `wiki_ingest(sourcePath)`，其中 `sourcePath` 是相对 `raw/` 的路径，如 `tech/example.md`。
8. 然后根据 `wiki_ingest` 返回的 prompt 继续完成知识编译，并优先调用 `wiki_commit_ingest` 提交结果。
9. 除非 `wiki_commit_ingest` 明显不适合，否则不要改用 `wiki_create_page`。
10. 最终输出必须是一个 JSON 对象，并且只能放在下面两个 marker 之间，marker 外不能输出任何别的内容。

输出 JSON schema：
{{
  "title": "{final_title}",
  "raw_folder": "tech|work|reading|general|assets",
  "raw_folder_reason": "为什么放到这个目录",
  "raw_saved_path": "raw/...md",
  "source_path": "相对 raw/ 的路径，如 tech/example.md",
  "created_wiki_pages": ["wiki/...md"],
  "ingest_summary": "这次编译创建或更新了什么",
  "notes": "额外说明"
}}

严格按以下格式输出：
{JSON_START_MARKER}
<JSON>
{JSON_END_MARKER}
"""
        return run_opencode_json(prompt, files=[attachment_path])
    finally:
        if attachment_path:
            try:
                Path(attachment_path).unlink(missing_ok=True)
            except OSError:
                pass


def run_wiki_ingest_source(source_path: str) -> dict:
    """Use OpenCode + MCP tools to compile an existing raw source into wiki pages."""
    prompt = f"""你现在在执行一个“已有 raw 文件编译节点”。

必须遵守：
1. 必须使用 MCP server `obsidian-wiki`。
2. 必须调用 `wiki_ingest(sourcePath="{source_path}")`。
3. 根据 `wiki_ingest` 返回的 prompt 继续完成知识编译，并优先调用 `wiki_commit_ingest` 提交结果。
4. 不要修改 raw 文件本身。
5. 最终输出必须是一个 JSON 对象，并且只能放在下面两个 marker 之间，marker 外不能输出任何别的内容。

输出 JSON schema：
{{
  "source_path": "{source_path}",
  "created_wiki_pages": ["wiki/...md"],
  "ingest_summary": "这次编译创建或更新了什么",
  "notes": "额外说明"
}}

严格按以下格式输出：
{JSON_START_MARKER}
<JSON>
{JSON_END_MARKER}
"""
    return run_opencode_json(prompt)
