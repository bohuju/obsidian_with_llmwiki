"""Utilities for running OpenCode workflows and extracting JSON results."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


JSON_START_MARKER = "__OPENCODE_JSON_START__"
JSON_END_MARKER = "__OPENCODE_JSON_END__"
_ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class OpenCodeError(RuntimeError):
    """Raised when an OpenCode invocation fails or returns invalid output."""


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


def _extract_json_block(stdout: str) -> str:
    clean = _strip_ansi(stdout)
    start = clean.find(JSON_START_MARKER)
    end = clean.find(JSON_END_MARKER)
    if start == -1 or end == -1 or end <= start:
        raise OpenCodeError(
            "OpenCode did not return the expected JSON markers. "
            f"Output was:\n{clean[-4000:]}"
        )

    json_text = clean[start + len(JSON_START_MARKER):end].strip()
    if not json_text:
        raise OpenCodeError("OpenCode returned empty JSON content.")
    return json_text


def run_opencode_json(prompt: str, *, files: list[str] | None = None) -> dict:
    """Run ``opencode`` and parse a JSON object from its stdout."""
    opencode_bin = os.getenv("OPENCODE_BIN", "opencode")
    project_dir = os.getenv("OPENCODE_PROJECT_DIR", str(_PROJECT_ROOT))
    timeout_sec = int(os.getenv("OPENCODE_TIMEOUT_SEC", "240"))
    model = os.getenv("OPENCODE_MODEL", "").strip()

    command = [opencode_bin, "run", "--dir", project_dir]
    if model:
        command.extend(["--model", model])

    for path in files or []:
        command.extend(["--file", path])

    command.append(prompt)

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:
        raise OpenCodeError(
            f"OpenCode binary not found: {opencode_bin}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        partial = _strip_ansi((exc.stdout or "") + "\n" + (exc.stderr or ""))
        raise OpenCodeError(
            "OpenCode timed out. "
            f"Timeout={timeout_sec}s. Partial output:\n{partial[-4000:]}"
        ) from exc

    combined_output = _strip_ansi(
        (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    ).strip()

    if completed.returncode != 0:
        raise OpenCodeError(
            f"OpenCode exited with code {completed.returncode}.\n{combined_output[-4000:]}"
        )

    json_text = _extract_json_block(completed.stdout or "")
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise OpenCodeError(
            f"OpenCode returned invalid JSON:\n{json_text}"
        ) from exc

    if not isinstance(payload, dict):
        raise OpenCodeError(f"OpenCode JSON result must be an object, got: {type(payload)!r}")
    return payload
