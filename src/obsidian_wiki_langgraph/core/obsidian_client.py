"""Obsidian vault file-system client."""

from __future__ import annotations

from pathlib import Path

from .utils import normalize_note_path, relative_path, walk_markdown_files


class ObsidianClient:
    """Provides read/write/list/search operations on an Obsidian vault."""

    def __init__(self, config: dict) -> None:
        self.vault_path: Path = Path(config["vault_path"]).resolve()
        self._api_enabled: bool = config.get("api_enabled", False)
        self._api_url: str = config.get("api_url", "http://localhost:19763")
        self._api_token: str = config.get("api_token", "")

        # Ensure vault directory exists
        self.vault_path.mkdir(parents=True, exist_ok=True)

    # --- File-system operations -----------------------------------------

    def list_notes(self, folder: str | None = None, recursive: bool = False) -> list[str]:
        """List note files, optionally filtered to *folder* and/or non-recursive."""
        target_dir = self.vault_path / folder if folder else self.vault_path
        all_files = walk_markdown_files(target_dir, self.vault_path)

        if recursive:
            return all_files

        # Non-recursive: only direct children of target directory
        prefix = folder + "/" if folder else ""
        return [
            f
            for f in all_files
            if "/" not in (f[len(prefix) :] if prefix else f)
        ]

    def read_note(self, note_path: str) -> dict:
        """Read a note, returning {path, content, exists}."""
        abs_path = normalize_note_path(self.vault_path, note_path)
        if not abs_path.exists():
            return {"path": note_path, "content": "", "exists": False}

        content = abs_path.read_text(encoding="utf-8")
        return {
            "path": relative_path(self.vault_path, abs_path),
            "content": content,
            "exists": True,
        }

    def write_note(self, note_path: str, content: str) -> dict:
        """Write a note (creates parent directories as needed)."""
        abs_path = normalize_note_path(self.vault_path, note_path)
        parent = abs_path.parent
        existed = abs_path.exists()

        parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")

        return {
            "path": relative_path(self.vault_path, abs_path),
            "created": not existed,
        }

    def delete_note(self, note_path: str) -> dict:
        """Delete a note."""
        abs_path = normalize_note_path(self.vault_path, note_path)
        if not abs_path.exists():
            return {"path": note_path, "deleted": False}

        abs_path.unlink()
        return {
            "path": relative_path(self.vault_path, abs_path),
            "deleted": True,
        }

    def search_notes(self, query: str) -> list[dict]:
        """Simple case-insensitive text search across all notes."""
        files = walk_markdown_files(self.vault_path, self.vault_path)
        results: list[dict] = []
        lower_query = query.lower()

        for file in files:
            abs_path = self.vault_path / file
            file_content = abs_path.read_text(encoding="utf-8")
            lines = file_content.split("\n")
            matches: list[dict] = []

            for i, line in enumerate(lines):
                if lower_query in line.lower():
                    matches.append({
                        "line": i + 1,
                        "context": line.strip()[:200],
                    })

            if matches:
                results.append({"path": file, "matches": matches})

        return results
