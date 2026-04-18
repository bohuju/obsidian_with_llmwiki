"""
Wiki Querier - searches the wiki knowledge base and builds query prompts.
Ported from obsidian-llm-wiki src/wiki-query.ts
"""

from __future__ import annotations

import re

from .link_engine import LinkEngine
from .utils import walk_markdown_files
from .wiki_manager import WikiManager


def extract_keywords(question: str) -> list[str]:
    """Extract keywords from a question by splitting on whitespace and punctuation.

    Filters out stop-words and tokens shorter than 2 characters.

    Parameters
    ----------
    question : str
        The user question.

    Returns
    -------
    list[str]
        Extracted keywords.
    """
    stop_words = {
        "的", "了", "是", "在", "有", "和", "与", "或", "不", "这", "那",
        "what", "how", "why", "is", "the", "a", "an", "of", "in", "to",
        "for", "and", "or", "not", "this", "that", "with",
    }

    tokens = re.split(
        r"[\s,，。？?！!、;；：:（）()\[\]「」【】]+",
        question,
    )
    return [w for w in tokens if len(w) >= 2 and w.lower() not in stop_words]


class WikiQuerier:
    """Search the wiki knowledge base and build query prompts for the LLM.

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

    def query(self, question: str) -> dict:
        """Search the wiki and return relevant context plus a prompt.

        Parameters
        ----------
        question : str
            The user's question.

        Returns
        -------
        dict
            Keys: question, relevant_pages, prompt.
        """
        wiki_base = self.wiki_manager._resolve_wiki("wiki")
        if not wiki_base.exists():
            return {
                "question": question,
                "relevant_pages": [],
                "prompt": "Wiki 未初始化，请先调用 wiki_init 初始化知识库。",
            }

        # Extract keywords from the question
        keywords = extract_keywords(question)

        # Search wiki directory for relevant pages
        all_wiki_files = walk_markdown_files(wiki_base, wiki_base)
        scored: list[dict] = []

        for file in all_wiki_files:
            abs_path = wiki_base / file
            content = abs_path.read_text(encoding="utf-8")
            lower = content.lower()

            score = 0
            for kw in keywords:
                matches = re.findall(re.escape(kw.lower()), lower)
                if matches:
                    score += len(matches)

            # Title match bonus
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else None
            if title:
                for kw in keywords:
                    if kw.lower() in title.lower():
                        score += 5

            if score > 0:
                scored.append({
                    "path": f"wiki/{file}",
                    "title": title,
                    "score": score,
                    "content": content,
                })

        # Sort by relevance, take top 5
        scored.sort(key=lambda p: p["score"], reverse=True)
        top_pages = scored[:5]

        relevant_pages = [
            {
                "path": p["path"],
                "title": p["title"],
                "relevance": f"匹配度: {p['score']}",
                "content": p["content"],
            }
            for p in top_pages
        ]

        # Build prompt context sections
        context_sections = "\n\n---\n\n".join(
            (
                f"### {p['title'] or p['path']}\n\n"
                f"{p['content'][:1500]}"
                + ("\n...（截断）" if len(p["content"]) > 1500 else "")
            )
            for p in top_pages
        )

        prompt = f"""## Wiki 知识查询

### 问题
{question}

### 相关 Wiki 页面

{context_sections or "（未找到相关 wiki 页面）"}

### 要求

1. 基于上述 wiki 页面内容回答问题
2. 引用具体来源时使用 [[wikilink]] 格式，如 "(来源: [[wiki/concepts/fuzzing]])"
3. 如果 wiki 中没有足够信息，明确说明，并建议调用 wiki_ingest 摄入相关源文件
4. 如果回答质量较高，建议归档为新 wiki 页面"""

        return {"question": question, "relevant_pages": relevant_pages, "prompt": prompt}
