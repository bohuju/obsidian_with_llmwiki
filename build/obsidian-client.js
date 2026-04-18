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
exports.ObsidianClient = void 0;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const utils_js_1 = require("./utils.js");
class ObsidianClient {
    vaultPath;
    apiEnabled;
    apiUrl;
    apiToken;
    constructor(config) {
        this.vaultPath = path.resolve(config.vaultPath);
        this.apiEnabled = config.apiEnabled ?? false;
        this.apiUrl = config.apiUrl ?? "http://localhost:19763";
        this.apiToken = config.apiToken ?? "";
        // 确保 vault 目录存在
        if (!fs.existsSync(this.vaultPath)) {
            fs.mkdirSync(this.vaultPath, { recursive: true });
        }
    }
    // ─── 文件系统操作 ──────────────────────────────
    /**
     * 列出笔记文件
     */
    listNotes(folder, recursive) {
        const targetDir = folder
            ? path.join(this.vaultPath, folder)
            : this.vaultPath;
        const allFiles = (0, utils_js_1.walkMarkdownFiles)(targetDir, this.vaultPath);
        if (recursive)
            return allFiles;
        // 非递归只返回目标目录直接子文件
        const prefix = folder ? folder + "/" : "";
        return allFiles.filter((f) => {
            const rel = prefix ? f.slice(prefix.length) : f;
            return !rel.includes("/");
        });
    }
    /**
     * 读取笔记
     */
    readNote(notePath) {
        const absPath = (0, utils_js_1.normalizeNotePath)(this.vaultPath, notePath);
        if (!fs.existsSync(absPath)) {
            return { path: notePath, content: "", exists: false };
        }
        const content = fs.readFileSync(absPath, "utf-8");
        return {
            path: (0, utils_js_1.relativePath)(this.vaultPath, absPath),
            content,
            exists: true,
        };
    }
    /**
     * 写入笔记（自动创建目录）
     */
    writeNote(notePath, content) {
        const absPath = (0, utils_js_1.normalizeNotePath)(this.vaultPath, notePath);
        const dir = path.dirname(absPath);
        const existed = fs.existsSync(absPath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        fs.writeFileSync(absPath, content, "utf-8");
        return {
            path: (0, utils_js_1.relativePath)(this.vaultPath, absPath),
            created: !existed,
        };
    }
    /**
     * 删除笔记
     */
    deleteNote(notePath) {
        const absPath = (0, utils_js_1.normalizeNotePath)(this.vaultPath, notePath);
        if (!fs.existsSync(absPath)) {
            return { path: notePath, deleted: false };
        }
        fs.unlinkSync(absPath);
        return { path: (0, utils_js_1.relativePath)(this.vaultPath, absPath), deleted: true };
    }
    /**
     * 搜索笔记（简单文本匹配）
     */
    searchNotes(query) {
        const files = (0, utils_js_1.walkMarkdownFiles)(this.vaultPath, this.vaultPath);
        const results = [];
        const lowerQuery = query.toLowerCase();
        for (const file of files) {
            const absPath = path.join(this.vaultPath, file);
            const content = fs.readFileSync(absPath, "utf-8");
            const lines = content.split("\n");
            const matches = [];
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].toLowerCase().includes(lowerQuery)) {
                    matches.push({
                        line: i + 1,
                        context: lines[i].trim().slice(0, 200),
                    });
                }
            }
            if (matches.length > 0) {
                results.push({ path: file, matches });
            }
        }
        return results;
    }
    // ─── REST API 操作（可选） ─────────────────────
    /**
     * 通过 REST API ping Obsidian
     */
    async pingApi() {
        if (!this.apiEnabled)
            return false;
        try {
            const res = await fetch(`${this.apiUrl}/api/ping`, {
                headers: this.apiHeaders(),
            });
            const data = (await res.json());
            return data.status === "ok";
        }
        catch {
            return false;
        }
    }
    apiHeaders() {
        const h = {};
        if (this.apiToken) {
            h["Authorization"] = `Bearer ${this.apiToken}`;
        }
        return h;
    }
}
exports.ObsidianClient = ObsidianClient;
//# sourceMappingURL=obsidian-client.js.map