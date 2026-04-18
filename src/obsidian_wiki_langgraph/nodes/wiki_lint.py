"""Wiki Lint node — run health check on the wiki."""

import json
from ..state import WikiGraphState
from ..core.link_engine import LinkEngine
from ..core.wiki_manager import WikiManager
from ..core.wiki_linter import WikiLinter
from ..config import VAULT_PATH, WIKI_ROOT

_linter: WikiLinter | None = None


def _get_linter() -> WikiLinter:
    global _linter
    if _linter is None:
        manager = WikiManager(str(VAULT_PATH), WIKI_ROOT or None)
        engine = LinkEngine(str(VAULT_PATH))
        _linter = WikiLinter(manager, engine)
    return _linter


def wiki_lint_node(state: WikiGraphState) -> dict:
    """Run wiki health check."""
    linter = _get_linter()
    report = linter.lint()

    write = state.get("write_report", True)
    report_path = None
    if write and report.total_pages > 0:
        report_path = linter.write_report(report)

    summary_lines = [f"- {t}: {c}" for t, c in report.summary.items()]
    summary_str = "\n".join(summary_lines) or "No issues found!"

    issues_str = "\n".join(
        f"[{i.severity}] {i.type}: {i.message} ({i.path})"
        for i in report.issues[:20]
    )
    if report.issue_count > 20:
        issues_str += f"\n... and {report.issue_count - 20} more"

    response = (
        f"## Wiki Lint Report\n\n"
        f"- Total pages: {report.total_pages}\n"
        f"- Issues found: {report.issue_count}\n\n"
        f"### Issues by Type\n{summary_str}\n\n"
    )
    if issues_str:
        response += f"### Details\n{issues_str}\n"
    if report_path:
        response += f"\nReport saved to: {report_path}"

    return {
        "lint_result": {
            "timestamp": report.timestamp,
            "total_pages": report.total_pages,
            "issue_count": report.issue_count,
            "issues": [
                {"severity": i.severity, "type": i.type, "path": i.path, "message": i.message}
                for i in report.issues
            ],
            "summary": report.summary,
            "report_path": report_path,
        },
        "response": response,
    }
