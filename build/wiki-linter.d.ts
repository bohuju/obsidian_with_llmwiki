import { WikiManager } from "./wiki-manager.js";
import { LinkEngine } from "./link-engine.js";
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
export declare class WikiLinter {
    private wikiManager;
    private linkEngine;
    constructor(wikiManager: WikiManager, linkEngine: LinkEngine);
    /**
     * 执行完整的 wiki 健康检查
     */
    lint(): LintReport;
    /**
     * 将 lint 报告写入文件
     */
    writeReport(report: LintReport): string;
}
