export interface ObsidianClientConfig {
    vaultPath: string;
    apiEnabled?: boolean;
    apiUrl?: string;
    apiToken?: string;
}
export declare class ObsidianClient {
    readonly vaultPath: string;
    private readonly apiEnabled;
    private readonly apiUrl;
    private readonly apiToken;
    constructor(config: ObsidianClientConfig);
    /**
     * 列出笔记文件
     */
    listNotes(folder?: string, recursive?: boolean): string[];
    /**
     * 读取笔记
     */
    readNote(notePath: string): {
        path: string;
        content: string;
        exists: boolean;
    };
    /**
     * 写入笔记（自动创建目录）
     */
    writeNote(notePath: string, content: string): {
        path: string;
        created: boolean;
    };
    /**
     * 删除笔记
     */
    deleteNote(notePath: string): {
        path: string;
        deleted: boolean;
    };
    /**
     * 搜索笔记（简单文本匹配）
     */
    searchNotes(query: string): Array<{
        path: string;
        matches: Array<{
            line: number;
            context: string;
        }>;
    }>;
    /**
     * 通过 REST API ping Obsidian
     */
    pingApi(): Promise<boolean>;
    private apiHeaders;
}
