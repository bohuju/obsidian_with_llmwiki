import { ObsidianClient } from "./obsidian-client.js";
import { LinkEngine } from "./link-engine.js";
import { WikiManager } from "./wiki-manager.js";
/**
 * 知识摄入器
 * 读取 raw 源文件，构建摄入 prompt 返回给 LLM 执行
 */
export declare class WikiIngester {
    private client;
    private linkEngine;
    private wikiManager;
    constructor(client: ObsidianClient, linkEngine: LinkEngine, wikiManager: WikiManager);
    /**
     * 摄入一个 raw 源文件
     * 返回摄入 prompt 和源文件内容，由 MCP tool 返回给调用方（OpenCode/LLM）执行
     */
    ingest(sourcePath: string): {
        source: string;
        content: string;
        existingWikiPages: Array<{
            path: string;
            title: string | null;
        }>;
        prompt: string;
    };
    /**
     * 确认摄入结果：将生成的 wiki 页面写入文件系统
     */
    commitIngest(result: {
        summary: {
            path: string;
            content: string;
        };
        concepts?: Array<{
            path: string;
            content: string;
        }>;
        entities?: Array<{
            path: string;
            content: string;
        }>;
        methods?: Array<{
            path: string;
            content: string;
        }>;
        sourcePath: string;
    }): string[];
}
