import os
from pathlib import Path

VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", "/home/bohuju/ObsidianVault"))
WIKI_ROOT = os.getenv("WIKI_ROOT", "")
DEFAULT_PAGE_TYPES = ["summaries", "concepts", "entities", "methods", "comparisons", "analysis", "indexes"]
RAW_SUBDIRS = ["tech", "work", "reading", "general", "assets"]
