import * as fs from "fs";
import * as path from "path";
import { normalizeNotePath, relativePath, walkMarkdownFiles } from "./utils.js";

export interface ObsidianClientConfig {
  vaultPath: string;
  apiEnabled?: boolean;
  apiUrl?: string;
  apiToken?: string;
}

export class ObsidianClient {
  public readonly vaultPath: string;
  private readonly apiEnabled: boolean;
  private readonly apiUrl: string;
  private readonly apiToken: string;

  constructor(config: ObsidianClientConfig) {
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
  listNotes(folder?: string, recursive?: boolean): string[] {
    const targetDir = folder
      ? path.join(this.vaultPath, folder)
      : this.vaultPath;
    const allFiles = walkMarkdownFiles(targetDir, this.vaultPath);
    if (recursive) return allFiles;

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
  readNote(notePath: string): { path: string; content: string; exists: boolean } {
    const absPath = normalizeNotePath(this.vaultPath, notePath);
    if (!fs.existsSync(absPath)) {
      return { path: notePath, content: "", exists: false };
    }
    const content = fs.readFileSync(absPath, "utf-8");
    return {
      path: relativePath(this.vaultPath, absPath),
      content,
      exists: true,
    };
  }

  /**
   * 写入笔记（自动创建目录）
   */
  writeNote(notePath: string, content: string): { path: string; created: boolean } {
    const absPath = normalizeNotePath(this.vaultPath, notePath);
    const dir = path.dirname(absPath);
    const existed = fs.existsSync(absPath);

    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(absPath, content, "utf-8");

    return {
      path: relativePath(this.vaultPath, absPath),
      created: !existed,
    };
  }

  /**
   * 删除笔记
   */
  deleteNote(notePath: string): { path: string; deleted: boolean } {
    const absPath = normalizeNotePath(this.vaultPath, notePath);
    if (!fs.existsSync(absPath)) {
      return { path: notePath, deleted: false };
    }
    fs.unlinkSync(absPath);
    return { path: relativePath(this.vaultPath, absPath), deleted: true };
  }

  /**
   * 搜索笔记（简单文本匹配）
   */
  searchNotes(query: string): Array<{
    path: string;
    matches: Array<{ line: number; context: string }>;
  }> {
    const files = walkMarkdownFiles(this.vaultPath, this.vaultPath);
    const results: Array<{
      path: string;
      matches: Array<{ line: number; context: string }>;
    }> = [];

    const lowerQuery = query.toLowerCase();

    for (const file of files) {
      const absPath = path.join(this.vaultPath, file);
      const content = fs.readFileSync(absPath, "utf-8");
      const lines = content.split("\n");
      const matches: Array<{ line: number; context: string }> = [];

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
  async pingApi(): Promise<boolean> {
    if (!this.apiEnabled) return false;
    try {
      const res = await fetch(`${this.apiUrl}/api/ping`, {
        headers: this.apiHeaders(),
      });
      const data = (await res.json()) as { status: string };
      return data.status === "ok";
    } catch {
      return false;
    }
  }

  private apiHeaders(): Record<string, string> {
    const h: Record<string, string> = {};
    if (this.apiToken) {
      h["Authorization"] = `Bearer ${this.apiToken}`;
    }
    return h;
  }
}
