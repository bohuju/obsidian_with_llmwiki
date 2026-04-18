import * as fs from "fs";
import * as path from "path";
import { WikiManager } from "./wiki-manager.js";
import { LinkEngine } from "./link-engine.js";
import { walkMarkdownFiles } from "./utils.js";

/**
 * 知识查询器
 * 搜索 wiki 知识库，构建查询 prompt 返回给 LLM 执行
 */
export class WikiQuerier {
  private wikiManager: WikiManager;
  private linkEngine: LinkEngine;

  constructor(wikiManager: WikiManager, linkEngine: LinkEngine) {
    this.wikiManager = wikiManager;
    this.linkEngine = linkEngine;
  }

  /**
   * 查询 wiki 知识库
   * 搜索相关页面，返回上下文 + prompt
   */
  query(question: string): {
    question: string;
    relevantPages: Array<{
      path: string;
      title: string | null;
      relevance: string;
      content: string;
    }>;
    prompt: string;
  } {
    const wikiBase = this.wikiManager["resolveWiki"]("wiki");
    if (!fs.existsSync(wikiBase)) {
      return {
        question,
        relevantPages: [],
        prompt: `Wiki 未初始化，请先调用 wiki_init 初始化知识库。`,
      };
    }

    // 提取问题中的关键词
    const keywords = extractKeywords(question);

    // 搜索 wiki 目录中的相关页面
    const allWikiFiles = walkMarkdownFiles(wikiBase, wikiBase);
    const scored: Array<{
      path: string;
      title: string | null;
      score: number;
      content: string;
    }> = [];

    for (const file of allWikiFiles) {
      const absPath = path.join(wikiBase, file);
      const content = fs.readFileSync(absPath, "utf-8");
      const lower = content.toLowerCase();

      let score = 0;
      for (const kw of keywords) {
        const regex = new RegExp(kw.toLowerCase(), "gi");
        const matches = lower.match(regex);
        if (matches) score += matches.length;
      }

      // 标题匹配加权
      const titleMatch = content.match(/^#\s+(.+)$/m);
      const title = titleMatch ? titleMatch[1].trim() : null;
      if (title) {
        for (const kw of keywords) {
          if (title.toLowerCase().includes(kw.toLowerCase())) score += 5;
        }
      }

      if (score > 0) {
        scored.push({ path: `wiki/${file}`, title, score, content });
      }
    }

    // 按相关度排序，取 top 5
    scored.sort((a, b) => b.score - a.score);
    const topPages = scored.slice(0, 5);

    const relevantPages = topPages.map((p) => ({
      path: p.path,
      title: p.title,
      relevance: `匹配度: ${p.score}`,
      content: p.content,
    }));

    // 构建 prompt
    const contextSections = topPages
      .map(
        (p) =>
          `### ${p.title ?? p.path}\n\n${p.content.slice(0, 1500)}${p.content.length > 1500 ? "\n...（截断）" : ""}`,
      )
      .join("\n\n---\n\n");

    const prompt = `## Wiki 知识查询

### 问题
${question}

### 相关 Wiki 页面

${contextSections || "（未找到相关 wiki 页面）"}

### 要求

1. 基于上述 wiki 页面内容回答问题
2. 引用具体来源时使用 [[wikilink]] 格式，如 "(来源: [[wiki/concepts/fuzzing]])"
3. 如果 wiki 中没有足够信息，明确说明，并建议调用 wiki_ingest 摄入相关源文件
4. 如果回答质量较高，建议归档为新 wiki 页面`;

    return { question, relevantPages, prompt };
  }
}

/**
 * 从问题中提取关键词
 */
function extractKeywords(question: string): string[] {
  // 简单分词：按空格和标点拆分，过滤停用词和短词
  const stopWords = new Set([
    "的", "了", "是", "在", "有", "和", "与", "或", "不", "这", "那",
    "what", "how", "why", "is", "the", "a", "an", "of", "in", "to",
    "for", "and", "or", "not", "this", "that", "with",
  ]);

  return question
    .split(/[\s,，。？?！!、;；：:（）()「」【】\[\]]+/)
    .filter((w) => w.length >= 2 && !stopWords.has(w.toLowerCase()));
}
