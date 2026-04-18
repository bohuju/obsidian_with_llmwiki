import { WikiManager } from "./wiki-manager.js";
import { LinkEngine } from "./link-engine.js";
/**
 * 知识查询器
 * 搜索 wiki 知识库，构建查询 prompt 返回给 LLM 执行
 */
export declare class WikiQuerier {
    private wikiManager;
    private linkEngine;
    constructor(wikiManager: WikiManager, linkEngine: LinkEngine);
    /**
     * 查询 wiki 知识库
     * 搜索相关页面，返回上下文 + prompt
     */
    query(question: string): {
        question: string;
        relevantPages: Array<{
            path: string;
            title: string | null;
            relevance: string;
            content: string;
        }>;
        prompt: string;
    };
}
