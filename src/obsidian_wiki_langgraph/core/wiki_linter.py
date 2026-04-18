"""
Wiki Linter - health-check the wiki knowledge base.
Ported from obsidian-llm-wiki src/wiki-linter.ts
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .link_engine import LinkEngine
from .utils import walk_markdown_files
from .wiki_manager import WikiManager


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LintIssue:
    """A single lint finding."""

    severity: str  # "error" | "warning" | "info"
    type: str
    path: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class LintReport:
    """Aggregated lint report."""

    timestamp: str
    total_pages: int
    issue_count: int
    issues: list[LintIssue] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# WikiLinter
# ---------------------------------------------------------------------------


class WikiLinter:
    """Perform health checks on the wiki knowledge base.

    Parameters
    ----------
    wiki_manager : WikiManager
        Wiki structure manager.
    link_engine : LinkEngine
        Bidirectional link engine.
    """

    def __init__(self, wiki_manager: WikiManager, link_engine: LinkEngine) -> None:
        self.wiki_manager = wiki_manager
        self.link_engine = link_engine

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lint(self) -> LintReport:
        """Execute a full wiki health check.

        Runs 5 checks:
        1. Missing frontmatter
        2. Missing source annotations
        3. Dangling links
        4. Orphan pages
        5. Duplicate titles

        Returns
        -------
        LintReport
        """
        issues: list[LintIssue] = []
        wiki_base = self.wiki_manager._resolve_wiki("wiki")

        if not wiki_base.exists():
            return LintReport(
                timestamp=datetime.now(timezone.utc).isoformat(),
                total_pages=0,
                issue_count=1,
                issues=[
                    LintIssue(
                        severity="error",
                        type="not-initialized",
                        path="",
                        message="Wiki 未初始化",
                        suggestion="请先调用 wiki_init 初始化知识库",
                    )
                ],
                summary={"not-initialized": 1},
            )

        all_files = walk_markdown_files(wiki_base, wiki_base)
        file_contents: dict[str, str] = {}

        # Read all file contents
        for file in all_files:
            abs_path = wiki_base / file
            file_contents[file] = abs_path.read_text(encoding="utf-8")

        # Check 1: Missing frontmatter
        for file, content in file_contents.items():
            if file.startswith("indexes/"):
                continue  # Index pages are exempt
            if not content.startswith("---"):
                issues.append(
                    LintIssue(
                        severity="warning",
                        type="missing-frontmatter",
                        path=f"wiki/{file}",
                        message="缺少 frontmatter",
                        suggestion="添加包含 type, sources, created, tags, status 的 frontmatter",
                    )
                )

        # Check 2: Missing source annotations
        for file, content in file_contents.items():
            if file.startswith("indexes/"):
                continue
            if "summaries/" in file:
                # Summary pages must have sources
                if "sources:" not in content:
                    issues.append(
                        LintIssue(
                            severity="error",
                            type="missing-sources",
                            path=f"wiki/{file}",
                            message="Summary 页面缺少 sources 字段",
                            suggestion="在 frontmatter 中添加 sources: [[raw-filename]]",
                        )
                    )
            else:
                # Non-summary pages should have (source: ...) annotations
                if content.startswith("---"):
                    second_dash = content.find("---", 3)
                    body_content = content[second_dash + 3 :] if second_dash != -1 else content
                else:
                    body_content = content
                if (
                    len(body_content) > 200
                    and "source:" not in body_content
                    and "sources:" not in body_content
                ):
                    issues.append(
                        LintIssue(
                            severity="warning",
                            type="missing-source-annotation",
                            path=f"wiki/{file}",
                            message="页面内容缺少来源标注 (source: [[...]])",
                            suggestion="为每个内容段落添加 (source: [[summaries/xxx]]) 标注",
                        )
                    )

        # Check 3: Dangling links (references to non-existent pages)
        all_wiki_paths = {f.removesuffix(".md") for f in all_files}
        for file, content in file_contents.items():
            links = LinkEngine.extract_links(content)
            for link in links:
                # Normalise: strip leading wiki/ and ../
                normalized = link.lstrip("wiki/")
                # Strip any remaining ../ prefixes
                while normalized.startswith("../"):
                    normalized = normalized[3:]
                if (
                    normalized not in all_wiki_paths
                    and f"wiki/{normalized}" not in all_wiki_paths
                ):
                    # Only flag links that reference wiki-internal pages
                    wiki_internal = any(
                        segment in normalized
                        for segment in ("wiki/", "summaries/", "concepts/", "entities/", "methods/")
                    )
                    if wiki_internal:
                        issues.append(
                            LintIssue(
                                severity="warning",
                                type="dangling-link",
                                path=f"wiki/{file}",
                                message=f"引用了不存在的页面: [[{link}]]",
                                suggestion="创建缺失的页面或修正链接",
                            )
                        )

        # Check 4: Orphan pages (no inbound or outbound links)
        graph = self.link_engine.build_graph()
        linked_nodes: set[str] = set()
        for edge in graph.edges:
            linked_nodes.add(edge.source)
            linked_nodes.add(edge.target)

        for file in all_files:
            if file.startswith("indexes/"):
                continue
            full_path = f"wiki/{file}"
            if full_path not in linked_nodes and file not in linked_nodes:
                issues.append(
                    LintIssue(
                        severity="info",
                        type="orphan-page",
                        path=full_path,
                        message="孤立页面（无入链无出链）",
                        suggestion="添加 [[wikilink]] 与其他页面关联，或在索引中引用",
                    )
                )

        # Check 5: Suspected duplicate pages (identical titles)
        title_map: dict[str, list[str]] = {}
        for file, content in file_contents.items():
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip().lower()
                title_map.setdefault(title, []).append(file)

        for title, files in title_map.items():
            if len(files) > 1:
                issues.append(
                    LintIssue(
                        severity="warning",
                        type="duplicate-title",
                        path=", ".join(f"wiki/{f}" for f in files),
                        message=f'发现 {len(files)} 个页面使用相同标题 "{title}"',
                        suggestion="考虑合并重复页面",
                    )
                )

        # Sort by severity
        severity_order = {"error": 0, "warning": 1, "info": 2}
        issues.sort(key=lambda issue: severity_order.get(issue.severity, 99))

        # Build summary counts
        summary: dict[str, int] = {}
        for issue in issues:
            summary[issue.type] = summary.get(issue.type, 0) + 1

        return LintReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_pages=len(all_files),
            issue_count=len(issues),
            issues=issues,
            summary=summary,
        )

    def write_report(self, report: LintReport) -> str:
        """Write the lint report to ``wiki/indexes/lint-report.md``.

        Parameters
        ----------
        report : LintReport
            The report produced by :meth:`lint`.

        Returns
        -------
        str
            The vault-relative path of the written report.
        """
        wiki_base = self.wiki_manager._resolve_wiki("wiki")
        report_path = wiki_base / "indexes" / "lint-report.md"

        lines: list[str] = [
            f"---\ntype: index\ntags: [wiki, lint]\ncreated: {report.timestamp}\n---\n",
            f"# Wiki Lint Report\n",
            f"**时间**: {report.timestamp}",
            f"**总页面数**: {report.total_pages}",
            f"**问题数**: {report.issue_count}\n",
        ]

        if report.summary:
            lines.append("## 问题统计\n")
            for issue_type, count in report.summary.items():
                lines.append(f"- **{issue_type}**: {count}")
            lines.append("")

        if report.issues:
            severity_emoji = {"error": "🔴", "warning": "🟡", "info": "🔵"}
            lines.append("## 问题详情\n")
            for issue in report.issues:
                emoji = severity_emoji.get(issue.severity, "")
                lines.append(
                    f"{emoji} **[{issue.severity.upper()}]** {issue.type}"
                )
                lines.append(f"  - 路径: `{issue.path}`")
                lines.append(f"  - {issue.message}")
                if issue.suggestion:
                    lines.append(f"  - 建议: {issue.suggestion}")
                lines.append("")
        else:
            lines.append("**Wiki 状态良好，没有发现问题。**\n")

        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines), encoding="utf-8")

        return "wiki/indexes/lint-report.md"
