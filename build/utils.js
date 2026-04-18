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
exports.parseFrontmatter = parseFrontmatter;
exports.extractTitle = extractTitle;
exports.normalizeNotePath = normalizeNotePath;
exports.relativePath = relativePath;
exports.walkMarkdownFiles = walkMarkdownFiles;
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
/**
 * 解析 frontmatter，返回 { frontmatter, content }
 */
function parseFrontmatter(raw) {
    const fm = {};
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
                    }
                    catch {
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
function extractTitle(content) {
    const match = content.match(/^#\s+(.+)$/m);
    return match ? match[1].trim() : null;
}
/**
 * 规范化 vault 内的路径（去掉开头的 / ，确保 .md 后缀）
 */
function normalizeNotePath(vaultRoot, notePath) {
    let p = notePath.startsWith("/") ? notePath.slice(1) : notePath;
    if (!p.endsWith(".md"))
        p += ".md";
    return path.resolve(vaultRoot, p);
}
/**
 * 获取 vault 相对路径
 */
function relativePath(vaultRoot, absPath) {
    return path.relative(vaultRoot, absPath);
}
/**
 * 递归获取 vault 中所有 .md 文件
 */
function walkMarkdownFiles(dir, vaultRoot) {
    const results = [];
    if (!fs.existsSync(dir))
        return results;
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
        // 跳过 .obsidian 和 .trash 目录
        if (entry.name.startsWith(".") || entry.name === ".trash")
            continue;
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            results.push(...walkMarkdownFiles(fullPath, vaultRoot));
        }
        else if (entry.name.endsWith(".md")) {
            results.push(path.relative(vaultRoot, fullPath));
        }
    }
    return results;
}
//# sourceMappingURL=utils.js.map