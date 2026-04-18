import * as fs from "fs";
import * as path from "path";
import { WikiManager } from "./wiki-manager.js";
import { LinkEngine } from "./link-engine.js";
import { walkMarkdownFiles } from "./utils.js";

export interface LintIssue {
  severity: "error" | "warning" | "info";
  type: string;
  path: string;
  message: string;
  suggestion?: string;
}

export interface LintReport {
  timestamp: string;
  totalPages: number;
  issueCount: number;
  issues: LintIssue[];
  summary: Record<string, number>;
}

/**
 * Wiki 健康检查器
 */
export class WikiLinter {
  private wikiManager: WikiManager;
  private linkEngine: LinkEngine;

  constructor(wikiManager: WikiManager, linkEngine: LinkEngine) {
    this.wikiManager = wikiManager;
    this.linkEngine = linkEngine;
  }

  /**
   * 执行完整的 wiki 健康检查
   */
  lint(): LintReport {
    const issues: LintIssue[] = [];
    const wikiBase = this.wikiManager["resolveWiki"]("wiki");

    if (!fs.existsSync(wikiBase)) {
      return {
        timestamp: new Date().toISOString(),
        totalPages: 0,
        issueCount: 1,
        issues: [
          {
            severity: "error",
            type: "not-initialized",
            path: "",
            message: "Wiki 未初始化",
            suggestion: "请先调用 wiki_init 初始化知识库",
          },
        ],
        summary: { "not-initialized": 1 },
      };
    }

    const allFiles = walkMarkdownFiles(wikiBase, wikiBase);
    const fileContents = new Map<string, string>();

    // 读取所有文件内容
    for (const file of allFiles) {
      const absPath = path.join(wikiBase, file);
      fileContents.set(file, fs.readFileSync(absPath, "utf-8"));
    }

    // 检查 1: 缺失 frontmatter
    for (const [file, content] of fileContents) {
      if (file.startsWith("indexes/")) continue; // 索引页面可豁免
      if (!content.startsWith("---")) {
        issues.push({
          severity: "warning",
          type: "missing-frontmatter",
          path: `wiki/${file}`,
          message: "缺少 frontmatter",
          suggestion: `添加包含 type, sources, created, tags, status 的 frontmatter`,
        });
      }
    }

    // 检查 2: 缺失来源标注
    for (const [file, content] of fileContents) {
      if (file.startsWith("indexes/")) continue;
      if (file.includes("summaries/")) {
        // Summary 页面必须有 sources
        if (!content.includes("sources:")) {
          issues.push({
            severity: "error",
            type: "missing-sources",
            path: `wiki/${file}`,
            message: "Summary 页面缺少 sources 字段",
            suggestion: "在 frontmatter 中添加 sources: [[raw-filename]]",
          });
        }
      } else {
        // 非 summary 页面应有 (source: ...) 标注
        const bodyContent = content.startsWith("---")
          ? content.slice(content.indexOf("---", 3) + 3)
          : content;
        if (bodyContent.length > 200 && !bodyContent.includes("source:") && !bodyContent.includes("sources:")) {
          issues.push({
            severity: "warning",
            type: "missing-source-annotation",
            path: `wiki/${file}`,
            message: "页面内容缺少来源标注 (source: [[...]])",
            suggestion: "为每个内容段落添加 (source: [[summaries/xxx]]) 标注",
          });
        }
      }
    }

    // 检查 3: 悬空链接（引用了不存在的页面）
    const allWikiPaths = new Set(allFiles.map((f) => f.replace(/\.md$/, "")));
    for (const [file, content] of fileContents) {
      const links = LinkEngine.extractLinks(content);
      for (const link of links) {
        // 只检查 wiki/ 内部的链接
        const normalizedLink = link
          .replace(/^wiki\//, "")
          .replace(/^\\.\\./g, "");
        if (
          !allWikiPaths.has(normalizedLink) &&
          !allWikiPaths.has(`wiki/${normalizedLink}`)
        ) {
          // 可能是外部链接（非 wiki 页面），只标记 wiki/ 内的
          if (normalizedLink.includes("wiki/") || normalizedLink.includes("summaries/") || normalizedLink.includes("concepts/") || normalizedLink.includes("entities/") || normalizedLink.includes("methods/")) {
            issues.push({
              severity: "warning",
              type: "dangling-link",
              path: `wiki/${file}`,
              message: `引用了不存在的页面: [[${link}]]`,
              suggestion: `创建缺失的页面或修正链接`,
            });
          }
        }
      }
    }

    // 检查 4: 孤立页面（没有入链也没有出链）
    const graph = this.linkEngine.buildGraph();
    const linkedNodes = new Set<string>();
    for (const edge of graph.edges) {
      linkedNodes.add(edge.source);
      linkedNodes.add(edge.target);
    }
    for (const file of allFiles) {
      if (file.startsWith("indexes/")) continue;
      const fullPath = `wiki/${file}`;
      if (!linkedNodes.has(fullPath) && !linkedNodes.has(file)) {
        issues.push({
          severity: "info",
          type: "orphan-page",
          path: fullPath,
          message: "孤立页面（无入链无出链）",
          suggestion: "添加 [[wikilink]] 与其他页面关联，或在索引中引用",
        });
      }
    }

    // 检查 5: 疑似重复页面（标题高度相似）
    const titleMap = new Map<string, string[]>();
    for (const [file, content] of fileContents) {
      const titleMatch = content.match(/^#\s+(.+)$/m);
      if (titleMatch) {
        const title = titleMatch[1].trim().toLowerCase();
        if (!titleMap.has(title)) titleMap.set(title, []);
        titleMap.get(title)!.push(file);
      }
    }
    for (const [title, files] of titleMap) {
      if (files.length > 1) {
        issues.push({
          severity: "warning",
          type: "duplicate-title",
          path: files.map((f) => `wiki/${f}`).join(", "),
          message: `发现 ${files.length} 个页面使用相同标题 "${title}"`,
          suggestion: "考虑合并重复页面",
        });
      }
    }

    // 按严重程度排序
    issues.sort((a, b) => {
      const order = { error: 0, warning: 1, info: 2 };
      return order[a.severity] - order[b.severity];
    });

    // 统计
    const summary: Record<string, number> = {};
    for (const issue of issues) {
      summary[issue.type] = (summary[issue.type] ?? 0) + 1;
    }

    return {
      timestamp: new Date().toISOString(),
      totalPages: allFiles.length,
      issueCount: issues.length,
      issues,
      summary,
    };
  }

  /**
   * 将 lint 报告写入文件
   */
  writeReport(report: LintReport): string {
    const wikiBase = this.wikiManager["resolveWiki"]("wiki");
    const reportPath = path.join(wikiBase, "indexes", "lint-report.md");

    let content = `---\ntype: index\ntags: [wiki, lint]\ncreated: ${report.timestamp}\n---\n\n# Wiki Lint Report\n\n`;
    content += `**时间**: ${report.timestamp}\n`;
    content += `**总页面数**: ${report.totalPages}\n`;
    content += `**问题数**: ${report.issueCount}\n\n`;

    if (Object.keys(report.summary).length > 0) {
      content += `## 问题统计\n\n`;
      for (const [type, count] of Object.entries(report.summary)) {
        content += `- **${type}**: ${count}\n`;
      }
      content += "\n";
    }

    if (report.issues.length > 0) {
      content += `## 问题详情\n\n`;
      const severityEmoji = { error: "🔴", warning: "🟡", info: "🔵" };
      for (const issue of report.issues) {
        content += `${severityEmoji[issue.severity]} **[${issue.severity.toUpperCase()}]** ${issue.type}\n`;
        content += `  - 路径: \`${issue.path}\`\n`;
        content += `  - ${issue.message}\n`;
        if (issue.suggestion) {
          content += `  - 建议: ${issue.suggestion}\n`;
        }
        content += "\n";
      }
    } else {
      content += `**Wiki 状态良好，没有发现问题。**\n`;
    }

    fs.mkdirSync(path.dirname(reportPath), { recursive: true });
    fs.writeFileSync(reportPath, content, "utf-8");

    return `wiki/indexes/lint-report.md`;
  }
}
