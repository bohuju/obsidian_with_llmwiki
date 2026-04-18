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
export declare class LinkEngine {
    private vaultPath;
    private titleCache;
    private cacheValid;
    constructor(vaultPath: string);
    /**
     * 刷新标题缓存：扫描 vault 所有笔记标题
     */
    refreshTitleCache(): void;
    /**
     * 获取所有笔记标题列表
     */
    getNoteTitles(folder?: string): Array<{
        path: string;
        title: string | null;
    }>;
    /**
     * 对内容自动注入 [[双向链接]]
     * 规则：
     *  1. 跳过已经在 [[...]] 内的文本
     *  2. 跳过 frontmatter 区域
     *  3. 匹配已知笔记标题 → [[路径]]
     *  4. 匹配日期 YYYY-MM-DD → [[310-Daily/YYYY-MM-DD]]
     */
    injectLinks(content: string): string;
    /**
     * 从内容中提取所有 [[wiki-link]] 目标
     */
    static extractLinks(content: string): string[];
    /**
     * 获取某笔记的所有正向链接（outgoing links）
     */
    getOutlinks(notePath: string): string[];
    /**
     * 获取某笔记的所有反向链接（backlinks）
     */
    getBacklinks(notePath: string): Array<{
        source: string;
        context: string;
    }>;
    /**
     * 构建完整的双向链接图谱
     */
    buildGraph(): Graph;
}
