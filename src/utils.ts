import * as path from "path";
import * as fs from "fs";

/**
 * 解析 frontmatter，返回 { frontmatter, content }
 */
export function parseFrontmatter(raw: string): {
  frontmatter: Record<string, unknown>;
  content: string;
} {
  const fm: Record<string, unknown> = {};
  let content = raw;

  if (raw.startsWith("---")) {
    const endIndex = raw.indexOf("---", 3);
    if (endIndex !== -1) {
      const fmText = raw.slice(3, endIndex).trim();
      content = raw.slice(endIndex + 3).trim();
      for (const line of fmText.split("\n")) {
        const colonIdx = line.indexOf(":");
        if (colonIdx > 0) {
          const key = line.slice(0, colonIdx).trim();
          const val = line.slice(colonIdx + 1).trim();
          try {
            fm[key] = JSON.parse(val);
          } catch {
            fm[key] = val;
          }
        }
      }
    }
  }

  return { frontmatter: fm, content };
}

/**
 * 从内容中提取第一个标题 (# ...)
 */
export function extractTitle(content: string): string | null {
  const match = content.match(/^#\s+(.+)$/m);
  return match ? match[1].trim() : null;
}

/**
 * 规范化 vault 内的路径（去掉开头的 / ，确保 .md 后缀）
 */
export function normalizeNotePath(vaultRoot: string, notePath: string): string {
  let p = notePath.startsWith("/") ? notePath.slice(1) : notePath;
  if (!p.endsWith(".md")) p += ".md";
  return path.resolve(vaultRoot, p);
}

/**
 * 获取 vault 相对路径
 */
export function relativePath(vaultRoot: string, absPath: string): string {
  return path.relative(vaultRoot, absPath);
}

/**
 * 递归获取 vault 中所有 .md 文件
 */
export function walkMarkdownFiles(dir: string, vaultRoot: string): string[] {
  const results: string[] = [];
  if (!fs.existsSync(dir)) return results;

  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    // 跳过 .obsidian 和 .trash 目录
    if (entry.name.startsWith(".") || entry.name === ".trash") continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walkMarkdownFiles(fullPath, vaultRoot));
    } else if (entry.name.endsWith(".md")) {
      results.push(path.relative(vaultRoot, fullPath));
    }
  }
  return results;
}
