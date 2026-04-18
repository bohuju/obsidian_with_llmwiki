import * as fs from "fs";
import * as path from "path";
import { generateClaudeMd } from "./templates/claude-md.js";
import { generateReadmeMd } from "./templates/readme-md.js";
import { walkMarkdownFiles } from "./utils.js";

export interface WikiConfig {
  wikiRoot: string; // wiki 子目录名，默认 ""
  pageTypes: string[];
}

const DEFAULT_PAGE_TYPES = [
  "summaries",
  "concepts",
  "entities",
  "methods",
  "comparisons",
  "analysis",
  "indexes",
];

const RAW_SUBDIRS = ["tech", "work", "reading", "general", "assets"];

export class WikiManager {
  private vaultPath: string;
  private wikiRoot: string;

  constructor(vaultPath: string, wikiRoot?: string) {
    this.vaultPath = path.resolve(vaultPath);
    this.wikiRoot = wikiRoot ?? "";
  }

  private resolveWiki(...segments: string[]): string {
    const base = this.wikiRoot
      ? path.join(this.vaultPath, this.wikiRoot)
      : this.vaultPath;
    return path.join(base, ...segments);
  }

  private resolveRaw(...segments: string[]): string {
    return this.resolveWiki("raw", ...segments);
  }

  /**
   * 检测 wiki 是否已初始化
   */
  detect(): {
    initialized: boolean;
    wikiRoot: string;
    rawDirs: string[];
    wikiDirs: string[];
  } {
    const rawDir = this.resolveRaw();
    const wikiDir = this.resolveWiki("wiki");

    const rawExists = fs.existsSync(rawDir);
    const wikiExists = fs.existsSync(wikiDir);

    const rawDirs = rawExists
      ? fs.readdirSync(rawDir).filter((d) =>
          fs.statSync(path.join(rawDir, d)).isDirectory()
        )
      : [];
    const wikiDirs = wikiExists
      ? fs.readdirSync(wikiDir).filter((d) =>
          fs.statSync(path.join(wikiDir, d)).isDirectory()
        )
      : [];

    return {
      initialized: rawExists && wikiExists,
      wikiRoot: this.wikiRoot,
      rawDirs,
      wikiDirs,
    };
  }

  /**
   * 初始化 wiki 目录结构
   */
  init(options?: { pageTypes?: string[] }): {
    created: string[];
    files: string[];
  } {
    const pageTypes = options?.pageTypes ?? DEFAULT_PAGE_TYPES;
    const created: string[] = [];
    const files: string[] = [];

    // 创建 raw 子目录
    for (const sub of RAW_SUBDIRS) {
      const dir = this.resolveRaw(sub);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
        created.push(`raw/${sub}`);
      }
    }

    // 创建 wiki 子目录
    for (const pt of pageTypes) {
      const dir = this.resolveWiki("wiki", pt);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
        created.push(`wiki/${pt}`);
      }
    }

    // 生成 CLAUDE.md
    const claudeMdPath = this.resolveWiki("CLAUDE.md");
    const vaultName = path.basename(this.vaultPath);
    const claudeMdContent = generateClaudeMd({
      vaultName,
      wikiRoot: this.wikiRoot ? `${this.wikiRoot}/` : "",
      pageTypes,
    });
    fs.writeFileSync(claudeMdPath, claudeMdContent, "utf-8");
    files.push("CLAUDE.md");

    // 生成 README.md
    const readmePath = this.resolveWiki("README.md");
    const readmeContent = generateReadmeMd({ vaultName, wikiRoot: this.wikiRoot });
    fs.writeFileSync(readmePath, readmeContent, "utf-8");
    files.push("README.md");

    // 创建索引
    const indexPath = this.resolveWiki("wiki", "indexes", "index.md");
    if (!fs.existsSync(indexPath)) {
      const indexContent = `---\ntype: index\ncreated: ${new Date().toISOString().slice(0, 10)}\ntags: [wiki, index]\n---\n\n# Wiki 索引\n\n> 所有 wiki 页面的目录\n\n## 按类型\n${pageTypes.map((t) => `- [[wiki/${t}/]]`).join("\n")}\n`;
      fs.mkdirSync(path.dirname(indexPath), { recursive: true });
      fs.writeFileSync(indexPath, indexContent, "utf-8");
      files.push("wiki/indexes/index.md");
    }

    // 创建日志
    const logPath = this.resolveWiki("wiki", "indexes", "log.md");
    if (!fs.existsSync(logPath)) {
      const logContent = `---\ntype: index\ntags: [wiki, log]\n---\n\n# 操作日志\n\n## ${new Date().toISOString().slice(0, 10)}\n\n- Wiki 初始化完成\n- 创建目录: ${created.join(", ")}\n`;
      fs.writeFileSync(logPath, logContent, "utf-8");
      files.push("wiki/indexes/log.md");
    }

    return { created, files };
  }

  /**
   * 获取 wiki 状态
   */
  status(): {
    initialized: boolean;
    totalPages: number;
    pageCounts: Record<string, number>;
    rawFiles: string[];
    ingestedSources: string[];
    orphanPages: string[];
  } {
    const detection = this.detect();
    if (!detection.initialized) {
      return {
        initialized: false,
        totalPages: 0,
        pageCounts: {},
        rawFiles: [],
        ingestedSources: [],
        orphanPages: [],
      };
    }

    // 统计各类型页面数
    const pageCounts: Record<string, number> = {};
    let totalPages = 0;
    for (const pt of DEFAULT_PAGE_TYPES) {
      const dir = this.resolveWiki("wiki", pt);
      const files = fs.existsSync(dir)
        ? fs.readdirSync(dir).filter((f) => f.endsWith(".md"))
        : [];
      pageCounts[pt] = files.length;
      totalPages += files.length;
    }

    // 列出 raw 文件
    const rawDir = this.resolveRaw();
    const rawFiles = fs.existsSync(rawDir)
      ? walkMarkdownFiles(rawDir, rawDir)
      : [];

    // 检查已摄入的源（通过 summaries 的 frontmatter sources 字段）
    const summariesDir = this.resolveWiki("wiki", "summaries");
    const ingestedSources: string[] = [];
    if (fs.existsSync(summariesDir)) {
      const summaryFiles = fs.readdirSync(summariesDir).filter((f) => f.endsWith(".md"));
      for (const sf of summaryFiles) {
        const content = fs.readFileSync(path.join(summariesDir, sf), "utf-8");
        const sourcesMatch = content.match(/sources:\s*\[(.+?)\]/);
        if (sourcesMatch) {
          ingestedSources.push(sf.replace(/\.md$/, ""));
        }
      }
    }

    return {
      initialized: true,
      totalPages,
      pageCounts,
      rawFiles,
      ingestedSources,
      orphanPages: [], // 将由 linter 填充
    };
  }

  /**
   * 列出 raw 目录中的源文件及摄入状态
   */
  listSources(folder?: string): Array<{
    path: string;
    ingested: boolean;
    size: number;
  }> {
    const targetDir = folder
      ? this.resolveRaw(folder)
      : this.resolveRaw();

    if (!fs.existsSync(targetDir)) return [];

    const rawBase = this.resolveRaw();
    const files = walkMarkdownFiles(targetDir, rawBase);
    const ingested = new Set(this.status().ingestedSources);

    return files.map((f) => {
      const absPath = path.join(rawBase, f);
      const stat = fs.statSync(absPath);
      const name = path.basename(f, ".md");
      return {
        path: f,
        ingested: ingested.has(name),
        size: stat.size,
      };
    });
  }

  /**
   * 追加操作日志
   */
  appendLog(entry: string): void {
    const logPath = this.resolveWiki("wiki", "indexes", "log.md");
    if (!fs.existsSync(logPath)) return;

    const date = new Date().toISOString().slice(0, 10);
    const content = fs.readFileSync(logPath, "utf-8");

    // 检查今天的日志段是否存在
    if (content.includes(`## ${date}`)) {
      // 追加到今天的段
      const updated = content.replace(
        `## ${date}\n`,
        `## ${date}\n\n- ${entry}\n`,
      );
      fs.writeFileSync(logPath, updated, "utf-8");
    } else {
      // 新增今天的段
      fs.writeFileSync(
        logPath,
        content.trimEnd() + `\n\n## ${date}\n\n- ${entry}\n`,
        "utf-8",
      );
    }
  }

  /**
   * 更新索引页面
   */
  updateIndex(newPages: Array<{ type: string; path: string; title: string }>): void {
    const indexPath = this.resolveWiki("wiki", "indexes", "index.md");
    if (!fs.existsSync(indexPath)) return;

    let content = fs.readFileSync(indexPath, "utf-8");

    for (const page of newPages) {
      const line = `- [[${page.path.replace(/\.md$/, "")}|${page.title}]]`;
      if (!content.includes(line)) {
        // 在对应类型的 section 下追加
        const sectionHeader = `### ${page.type}`;
        if (content.includes(sectionHeader)) {
          content = content.replace(
            sectionHeader + "\n",
            sectionHeader + "\n" + line + "\n",
          );
        } else {
          // 追加新类型 section
          content = content.trimEnd() + `\n\n### ${page.type}\n\n${line}\n`;
        }
      }
    }

    fs.writeFileSync(indexPath, content, "utf-8");
  }
}
