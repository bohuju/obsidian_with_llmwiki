"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.LinkEngine = void 0;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const utils_js_1 = require("./utils.js");
/**
 * 双向链接引擎
 * 负责 [[wiki-link]] 的注入、解析、反向查询和图谱构建
 */
class LinkEngine {
    vaultPath;
    titleCache = new Map(); // normalizedTitle → path
    cacheValid = false;
    constructor(vaultPath) {
        this.vaultPath = path.resolve(vaultPath);
    }
    // ─── 链接注入 ──────────────────────────────────
    /**
     * 刷新标题缓存：扫描 vault 所有笔记标题
     */
    refreshTitleCache() {
        this.titleCache.clear();
        const files = (0, utils_js_1.walkMarkdownFiles)(this.vaultPath, this.vaultPath);
        for (const file of files) {
            const absPath = path.join(this.vaultPath, file);
            const content = fs.readFileSync(absPath, "utf-8");
            const title = (0, utils_js_1.extractTitle)(content);
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
    getNoteTitles(folder) {
        if (!this.cacheValid)
            this.refreshTitleCache();
        const files = folder
            ? (0, utils_js_1.walkMarkdownFiles)(path.join(this.vaultPath, folder), this.vaultPath)
            : (0, utils_js_1.walkMarkdownFiles)(this.vaultPath, this.vaultPath);
        return files.map((f) => {
            const absPath = path.join(this.vaultPath, f);
            const content = fs.readFileSync(absPath, "utf-8");
            return { path: f, title: (0, utils_js_1.extractTitle)(content) };
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
    injectLinks(content) {
        if (!this.cacheValid)
            this.refreshTitleCache();
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
        result = result.replace(/(?<!\[\[)(\d{4}-\d{2}-\d{2})(?!\]\])/g, (_, date) => {
            // 检查是否已经在链接中
            return `[[310-Daily/${date}]]`;
        });
        // 注入已知标题链接
        for (const { key, display } of sortedTitles) {
            if (key.length < 2)
                continue; // 跳过太短的标题
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
    static extractLinks(content) {
        const links = [];
        const regex = /\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]/g;
        let match;
        while ((match = regex.exec(content)) !== null) {
            let target = match[1].trim();
            // 去掉开头的 ../
            while (target.startsWith("../")) {
                target = target.slice(3);
            }
            if (!target.endsWith(".md")) {
                // 尝试解析为路径
                links.push(target);
            }
            else {
                links.push(target.replace(/\.md$/, ""));
            }
        }
        return [...new Set(links)];
    }
    /**
     * 获取某笔记的所有正向链接（outgoing links）
     */
    getOutlinks(notePath) {
        const absPath = path.join(this.vaultPath, notePath);
        if (!fs.existsSync(absPath))
            return [];
        const content = fs.readFileSync(absPath, "utf-8");
        return LinkEngine.extractLinks(content);
    }
    /**
     * 获取某笔记的所有反向链接（backlinks）
     */
    getBacklinks(notePath) {
        const files = (0, utils_js_1.walkMarkdownFiles)(this.vaultPath, this.vaultPath);
        const results = [];
        // 目标笔记的各种可能引用形式
        const basename = path.basename(notePath, ".md");
        const targets = [
            notePath.replace(/\.md$/, ""),
            basename,
            `/${basename}`,
            `/${notePath.replace(/\.md$/, "")}`,
        ];
        for (const file of files) {
            if (file === notePath)
                continue;
            const absPath = path.join(this.vaultPath, file);
            const content = fs.readFileSync(absPath, "utf-8");
            const lines = content.split("\n");
            for (const line of lines) {
                const links = LinkEngine.extractLinks(line);
                const hasMatch = links.some((link) => targets.some((t) => link.toLowerCase() === t.toLowerCase()
                    || link.toLowerCase().endsWith(t.toLowerCase())));
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
    buildGraph() {
        const files = (0, utils_js_1.walkMarkdownFiles)(this.vaultPath, this.vaultPath);
        const nodes = [];
        const edges = [];
        for (const file of files) {
            const absPath = path.join(this.vaultPath, file);
            const content = fs.readFileSync(absPath, "utf-8");
            nodes.push({
                path: file,
                title: (0, utils_js_1.extractTitle)(content),
            });
            const outlinks = LinkEngine.extractLinks(content);
            for (const target of outlinks) {
                edges.push({ source: file, target });
            }
        }
        return { nodes, edges };
    }
}
exports.LinkEngine = LinkEngine;
//# sourceMappingURL=link-engine.js.map