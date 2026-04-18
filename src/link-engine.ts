import * as fs from "fs";
import * as path from "path";
import { walkMarkdownFiles, extractTitle } from "./utils.js";

export interface GraphNode {
  path: string;
  title: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

/**
 * 双向链接引擎
 * 负责 [[wiki-link]] 的注入、解析、反向查询和图谱构建
 */
export class LinkEngine {
  private vaultPath: string;
  private titleCache: Map<string, string> = new Map(); // normalizedTitle → path
  private cacheValid = false;

  constructor(vaultPath: string) {
    this.vaultPath = path.resolve(vaultPath);
  }

  // ─── 链接注入 ──────────────────────────────────

  /**
   * 刷新标题缓存：扫描 vault 所有笔记标题
   */
  refreshTitleCache(): void {
    this.titleCache.clear();
    const files = walkMarkdownFiles(this.vaultPath, this.vaultPath);

    for (const file of files) {
      const absPath = path.join(this.vaultPath, file);
      const content = fs.readFileSync(absPath, "utf-8");
      const title = extractTitle(content);

      // 用文件名（去掉 .md）作为 key
      const basename = file.replace(/\.md$/, "");
      const nameOnly = path.basename(file, ".md");

      if (title) {
        this.titleCache.set(title.toLowerCase(), file);
      }
      this.titleCache.set(nameOnly.toLowerCase(), file);
      // 也注册完整路径
      this.titleCache.set(basename.toLowerCase(), file);
    }

    this.cacheValid = true;
  }

  /**
   * 获取所有笔记标题列表
   */
  getNoteTitles(folder?: string): Array<{ path: string; title: string | null }> {
    if (!this.cacheValid) this.refreshTitleCache();

    const files = folder
      ? walkMarkdownFiles(path.join(this.vaultPath, folder), this.vaultPath)
      : walkMarkdownFiles(this.vaultPath, this.vaultPath);

    return files.map((f) => {
      const absPath = path.join(this.vaultPath, f);
      const content = fs.readFileSync(absPath, "utf-8");
      return { path: f, title: extractTitle(content) };
    });
  }

  /**
   * 对内容自动注入 [[双向链接]]
   * 规则：
   *  1. 跳过已经在 [[...]] 内的文本
   *  2. 跳过 frontmatter 区域
   *  3. 匹配已知笔记标题 → [[路径]]
   *  4. 匹配日期 YYYY-MM-DD → [[310-Daily/YYYY-MM-DD]]
   */
  injectLinks(content: string): string {
    if (!this.cacheValid) this.refreshTitleCache();

    // 分离 frontmatter
    let fmPart = "";
    let bodyPart = content;

    if (content.startsWith("---")) {
      const endIndex = content.indexOf("---", 3);
      if (endIndex !== -1) {
        fmPart = content.slice(0, endIndex + 3);
        bodyPart = content.slice(endIndex + 3);
      }
    }

    // 收集所有已知标题，按长度降序排列（长标题优先匹配）
    const sortedTitles = [...this.titleCache.entries()]
      .map(([key, filePath]) => ({
        key,
        filePath,
        display: filePath.replace(/\.md$/, ""),
      }))
      .sort((a, b) => b.key.length - a.key.length);

    let result = bodyPart;

    // 注入日期链接
    result = result.replace(
      /(?<!\[\[)(\d{4}-\d{2}-\d{2})(?!\]\])/g,
      (_, date) => {
        // 检查是否已经在链接中
        return `[[310-Daily/${date}]]`;
      }
    );

    // 注入已知标题链接
    for (const { key, display } of sortedTitles) {
      if (key.length < 2) continue; // 跳过太短的标题
      // 转义正则特殊字符
      const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      // 匹配不在 [[...]] 内的文本
      const regex = new RegExp(`(?<![\\[/])\\b(${escaped})\\b(?![\\]])`, "gi");
      result = result.replace(regex, () => `[[${display}]]`);
    }

    // 清理嵌套链接：[[[[a]]]] → [[a]]
    result = result.replace(/\[\[\[([^\]]+)\]\]\]/g, "[[$1]]");

    return fmPart + result;
  }

  // ─── 链接解析 ──────────────────────────────────

  /**
   * 从内容中提取所有 [[wiki-link]] 目标
   */
  static extractLinks(content: string): string[] {
    const links: string[] = [];
    const regex = /\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]/g;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(content)) !== null) {
      let target = match[1].trim();
      // 去掉开头的 ../
      while (target.startsWith("../")) {
        target = target.slice(3);
      }
      if (!target.endsWith(".md")) {
        // 尝试解析为路径
        links.push(target);
      } else {
        links.push(target.replace(/\.md$/, ""));
      }
    }

    return [...new Set(links)];
  }

  /**
   * 获取某笔记的所有正向链接（outgoing links）
   */
  getOutlinks(notePath: string): string[] {
    const absPath = path.join(this.vaultPath, notePath);
    if (!fs.existsSync(absPath)) return [];

    const content = fs.readFileSync(absPath, "utf-8");
    return LinkEngine.extractLinks(content);
  }

  /**
   * 获取某笔记的所有反向链接（backlinks）
   */
  getBacklinks(notePath: string): Array<{
    source: string;
    context: string;
  }> {
    const files = walkMarkdownFiles(this.vaultPath, this.vaultPath);
    const results: Array<{ source: string; context: string }> = [];

    // 目标笔记的各种可能引用形式
    const basename = path.basename(notePath, ".md");
    const targets = [
      notePath.replace(/\.md$/, ""),
      basename,
      `/${basename}`,
      `/${notePath.replace(/\.md$/, "")}`,
    ];

    for (const file of files) {
      if (file === notePath) continue;
      const absPath = path.join(this.vaultPath, file);
      const content = fs.readFileSync(absPath, "utf-8");
      const lines = content.split("\n");

      for (const line of lines) {
        const links = LinkEngine.extractLinks(line);
        const hasMatch = links.some((link) =>
          targets.some(
            (t) => link.toLowerCase() === t.toLowerCase()
              || link.toLowerCase().endsWith(t.toLowerCase()),
          )
        );

        if (hasMatch) {
          results.push({
            source: file,
            context: line.trim().slice(0, 200),
          });
          break; // 每个文件只取第一个匹配行
        }
      }
    }

    return results;
  }

  // ─── 图谱构建 ──────────────────────────────────

  /**
   * 构建完整的双向链接图谱
   */
  buildGraph(): Graph {
    const files = walkMarkdownFiles(this.vaultPath, this.vaultPath);
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];

    for (const file of files) {
      const absPath = path.join(this.vaultPath, file);
      const content = fs.readFileSync(absPath, "utf-8");

      nodes.push({
        path: file,
        title: extractTitle(content),
      });

      const outlinks = LinkEngine.extractLinks(content);
      for (const target of outlinks) {
        edges.push({ source: file, target });
      }
    }

    return { nodes, edges };
  }
}
