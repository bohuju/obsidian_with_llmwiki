/**
 * 解析 frontmatter，返回 { frontmatter, content }
 */
export declare function parseFrontmatter(raw: string): {
    frontmatter: Record<string, unknown>;
    content: string;
};
/**
 * 从内容中提取第一个标题 (# ...)
 */
export declare function extractTitle(content: string): string | null;
/**
 * 规范化 vault 内的路径（去掉开头的 / ，确保 .md 后缀）
 */
export declare function normalizeNotePath(vaultRoot: string, notePath: string): string;
/**
 * 获取 vault 相对路径
 */
export declare function relativePath(vaultRoot: string, absPath: string): string;
/**
 * 递归获取 vault 中所有 .md 文件
 */
export declare function walkMarkdownFiles(dir: string, vaultRoot: string): string[];
