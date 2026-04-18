import * as fs from "fs";
import * as path from "path";
import { ObsidianClient } from "./obsidian-client.js";
import { LinkEngine } from "./link-engine.js";
import { WikiManager } from "./wiki-manager.js";

/**
 * 知识摄入器
 * 读取 raw 源文件，构建摄入 prompt 返回给 LLM 执行
 */
export class WikiIngester {
  private client: ObsidianClient;
  private linkEngine: LinkEngine;
  private wikiManager: WikiManager;

  constructor(
    client: ObsidianClient,
    linkEngine: LinkEngine,
    wikiManager: WikiManager,
  ) {
    this.client = client;
    this.linkEngine = linkEngine;
    this.wikiManager = wikiManager;
  }

  /**
   * 摄入一个 raw 源文件
   * 返回摄入 prompt 和源文件内容，由 MCP tool 返回给调用方（OpenCode/LLM）执行
   */
  ingest(sourcePath: string): {
    source: string;
    content: string;
    existingWikiPages: Array<{ path: string; title: string | null }>;
    prompt: string;
  } {
    // 读取 raw 源文件
    const rawBase = this.wikiManager["resolveRaw"]();
    const absPath = path.join(rawBase, sourcePath);
    if (!fs.existsSync(absPath)) {
      throw new Error(`Source file not found: ${sourcePath}`);
    }

    const content = fs.readFileSync(absPath, "utf-8");
    const sourceName = path.basename(sourcePath, ".md");

    // 获取已有 wiki 页面（用于交叉引用）
    const existingPages = this.linkEngine.getNoteTitles();

    // 获取已有的 summaries（避免重复）
    const wikiBase = this.wikiManager["resolveWiki"]("wiki");
    const existingSummaries = fs.existsSync(path.join(wikiBase, "summaries"))
      ? fs.readdirSync(path.join(wikiBase, "summaries"))
          .filter((f) => f.endsWith(".md"))
          .map((f) => f.replace(/\.md$/, ""))
      : [];

    const prompt = buildIngestPrompt(sourceName, content, existingSummaries, existingPages);

    return {
      source: sourcePath,
      content,
      existingWikiPages: existingPages,
      prompt,
    };
  }

  /**
   * 确认摄入结果：将生成的 wiki 页面写入文件系统
   */
  commitIngest(result: {
    summary: { path: string; content: string };
    concepts?: Array<{ path: string; content: string }>;
    entities?: Array<{ path: string; content: string }>;
    methods?: Array<{ path: string; content: string }>;
    sourcePath: string;
  }): string[] {
    const createdFiles: string[] = [];
    const date = new Date().toISOString().slice(0, 10);

    // 写入 summary
    const summaryContent = ensureFrontmatter(result.summary.content, {
      type: "summary",
      sources: [`[[${path.basename(result.sourcePath, ".md")}]]`],
      created: date,
      updated: date,
      tags: ["wiki", "summary"],
      status: "stable",
    });
    const linkedSummary = this.linkEngine.injectLinks(summaryContent);
    const wikiBase = this.wikiManager["resolveWiki"]("wiki");
    const summaryPath = path.join(wikiBase, "summaries", result.summary.path);
    fs.mkdirSync(path.dirname(summaryPath), { recursive: true });
    fs.writeFileSync(summaryPath, linkedSummary, "utf-8");
    createdFiles.push(`wiki/summaries/${result.summary.path}`);

    // 写入 concepts
    for (const concept of result.concepts ?? []) {
      const conceptContent = ensureFrontmatter(concept.content, {
        type: "concept",
        sources: [`[[summaries/${path.basename(result.summary.path, ".md")}]]`],
        created: date,
        updated: date,
        tags: ["wiki", "concept"],
        status: "draft",
      });
      const linked = this.linkEngine.injectLinks(conceptContent);
      const conceptPath = path.join(wikiBase, "concepts", concept.path);
      fs.mkdirSync(path.dirname(conceptPath), { recursive: true });
      fs.writeFileSync(conceptPath, linked, "utf-8");
      createdFiles.push(`wiki/concepts/${concept.path}`);
    }

    // 写入 entities
    for (const entity of result.entities ?? []) {
      const entityContent = ensureFrontmatter(entity.content, {
        type: "entity",
        sources: [`[[summaries/${path.basename(result.summary.path, ".md")}]]`],
        created: date,
        updated: date,
        tags: ["wiki", "entity"],
        status: "draft",
      });
      const linked = this.linkEngine.injectLinks(entityContent);
      const entityPath = path.join(wikiBase, "entities", entity.path);
      fs.mkdirSync(path.dirname(entityPath), { recursive: true });
      fs.writeFileSync(entityPath, linked, "utf-8");
      createdFiles.push(`wiki/entities/${entity.path}`);
    }

    // 写入 methods
    for (const method of result.methods ?? []) {
      const methodContent = ensureFrontmatter(method.content, {
        type: "method",
        sources: [`[[summaries/${path.basename(result.summary.path, ".md")}]]`],
        created: date,
        updated: date,
        tags: ["wiki", "method"],
        status: "draft",
      });
      const linked = this.linkEngine.injectLinks(methodContent);
      const methodPath = path.join(wikiBase, "methods", method.path);
      fs.mkdirSync(path.dirname(methodPath), { recursive: true });
      fs.writeFileSync(methodPath, linked, "utf-8");
      createdFiles.push(`wiki/methods/${method.path}`);
    }

    // 刷新链接缓存
    this.linkEngine.refreshTitleCache();

    // 更新索引和日志
    const pagesForIndex = createdFiles.map((f) => {
      const type = f.split("/")[1]?.replace(/s$/, "") ?? "unknown";
      const name = path.basename(f, ".md");
      return { type, path: f, title: name };
    });
    this.wikiManager.updateIndex(pagesForIndex);
    this.wikiManager.appendLog(`摄入 raw/${result.sourcePath} → ${createdFiles.join(", ")}`);

    return createdFiles;
  }
}

/**
 * 构建摄入 prompt
 */
function buildIngestPrompt(
  sourceName: string,
  sourceContent: string,
  existingSummaries: string[],
  existingPages: Array<{ path: string; title: string | null }>,
): string {
  const conceptsList = existingPages
    .filter((p) => p.path.includes("concepts/"))
    .map((p) => `- ${p.title ?? p.path}`)
    .join("\n");

  const entitiesList = existingPages
    .filter((p) => p.path.includes("entities/"))
    .map((p) => `- ${p.title ?? p.path}`)
    .join("\n");

  return `## 知识摄入任务

请将以下 raw 源文件编译为结构化 wiki 页面。

### 源文件: ${sourceName}

\`\`\`markdown
${sourceContent.slice(0, 8000)}
\`\`\`

### 已有的 summary 页面（不要重复创建）
${existingSummaries.length > 0 ? existingSummaries.map((s) => `- ${s}`).join("\n") : "（无）"}

### 已有的概念页面（可以交叉引用）
${conceptsList || "（无）"}

### 已有的实体页面（可以交叉引用）
${entitiesList || "（无）"}

### 要求

请生成以下 wiki 页面，使用 [[wikilink]] 交叉引用：

1. **Summary 页面** (\`wiki/summaries/${sourceName}.md\`)
   - 源文件的核心要点摘要
   - frontmatter: type=summary, sources=["[[${sourceName}]]"]

2. **Concept 页面** (0-N 个, \`wiki/concepts/*.md\`)
   - 提取文档中的关键概念
   - 每个概念回答"什么是 X"
   - 用 (source: [[summaries/${sourceName}]]) 标注来源段落

3. **Entity 页面** (0-N 个, \`wiki/entities/*.md\`)
   - 提取文档中的人物、项目、组织等实体
   - 用 [[wikilink]] 与已有实体交叉引用

4. **Method 页面** (可选, 仅当满足质量门控时)
   - 提取可执行的方法/步骤
   - 必须满足：可执行、可迁移、非平凡

输出格式请使用 wiki_create_page 工具逐个创建页面，或使用 wiki_commit_ingest 一次性提交所有页面。`;
}

/**
 * 确保内容有 frontmatter
 */
function ensureFrontmatter(
  content: string,
  fm: Record<string, unknown>,
): string {
  if (content.startsWith("---")) {
    return content;
  }
  const fmLines = Object.entries(fm)
    .map(([k, v]) => {
      if (Array.isArray(v)) {
        return `${k}: [${v.map((i: string) => i.includes(" ") ? `"${i}"` : i).join(", ")}]`;
      }
      return `${k}: ${v}`;
    })
    .join("\n");
  return `---\n${fmLines}\n---\n\n${content}`;
}
