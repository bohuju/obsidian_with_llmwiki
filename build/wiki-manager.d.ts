export interface WikiConfig {
    wikiRoot: string;
    pageTypes: string[];
}
export declare class WikiManager {
    private vaultPath;
    private wikiRoot;
    constructor(vaultPath: string, wikiRoot?: string);
    private resolveWiki;
    private resolveRaw;
    /**
     * 检测 wiki 是否已初始化
     */
    detect(): {
        initialized: boolean;
        wikiRoot: string;
        rawDirs: string[];
        wikiDirs: string[];
    };
    /**
     * 初始化 wiki 目录结构
     */
    init(options?: {
        pageTypes?: string[];
    }): {
        created: string[];
        files: string[];
    };
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
    };
    /**
     * 列出 raw 目录中的源文件及摄入状态
     */
    listSources(folder?: string): Array<{
        path: string;
        ingested: boolean;
        size: number;
    }>;
    /**
     * 追加操作日志
     */
    appendLog(entry: string): void;
    /**
     * 更新索引页面
     */
    updateIndex(newPages: Array<{
        type: string;
        path: string;
        title: string;
    }>): void;
}
