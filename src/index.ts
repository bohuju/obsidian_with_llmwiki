#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { ObsidianClient } from "./obsidian-client.js";
import { LinkEngine } from "./link-engine.js";
import { WikiManager } from "./wiki-manager.js";
import { WikiIngester } from "./wiki-ingester.js";
import { WikiQuerier } from "./wiki-query.js";
import { WikiLinter } from "./wiki-linter.js";

// ─── 配置 ─────────────────────────────────────────

const VAULT_PATH = process.env.OBSIDIAN_VAULT_PATH ?? "/home/bohuju/ObsidianVault";
const WIKI_ROOT = process.env.WIKI_ROOT ?? ""; // wiki 子目录，空表示 vault 根目录

// ─── 初始化 ───────────────────────────────────────

const client = new ObsidianClient({ vaultPath: VAULT_PATH });
const linkEngine = new LinkEngine(VAULT_PATH);
const wikiManager = new WikiManager(VAULT_PATH, WIKI_ROOT || undefined);
const ingester = new WikiIngester(client, linkEngine, wikiManager);
const querier = new WikiQuerier(wikiManager, linkEngine);
const linter = new WikiLinter(wikiManager, linkEngine);

// ─── MCP Server ───────────────────────────────────

const server = new McpServer({
  name: "obsidian-llm-wiki",
  version: "1.0.0",
});

// ═══════════════════════════════════════════════════
// Obsidian 基础工具
// ═══════════════════════════════════════════════════

server.tool(
  "obsidian_list_notes",
  "List all notes in the Obsidian vault. Optionally filter by folder and recursion.",
  {
    folder: z.string().optional().describe("Subfolder to list"),
    recursive: z.boolean().optional().default(false).describe("List recursively"),
  },
  async ({ folder, recursive }) => {
    const notes = client.listNotes(folder, recursive);
    return { content: [{ type: "text" as const, text: JSON.stringify({ count: notes.length, notes }, null, 2) }] };
  },
);

server.tool(
  "obsidian_read_note",
  "Read the content of a note from the Obsidian vault.",
  { path: z.string().describe("Note path relative to vault root") },
  async ({ path: notePath }) => {
    const result = client.readNote(notePath);
    if (!result.exists) {
      return { content: [{ type: "text" as const, text: `Note not found: ${notePath}` }], isError: true };
    }
    return { content: [{ type: "text" as const, text: result.content }] };
  },
);

server.tool(
  "obsidian_write_note",
  "Create or update a note. Optionally auto-inject [[wiki-links]].",
  {
    path: z.string().describe("Note path relative to vault root"),
    content: z.string().describe("Markdown content"),
    autoLink: z.boolean().optional().default(true).describe("Auto-inject [[wiki-links]]"),
  },
  async ({ path: notePath, content, autoLink }) => {
    const finalContent = autoLink ? linkEngine.injectLinks(content) : content;
    const result = client.writeNote(notePath, finalContent);
    linkEngine.refreshTitleCache();
    return { content: [{ type: "text" as const, text: `Note ${result.created ? "created" : "updated"}: ${result.path}` }] };
  },
);

server.tool(
  "obsidian_delete_note",
  "Delete a note from the Obsidian vault.",
  { path: z.string().describe("Note path relative to vault root") },
  async ({ path: notePath }) => {
    const result = client.deleteNote(notePath);
    if (!result.deleted) {
      return { content: [{ type: "text" as const, text: `Note not found: ${notePath}` }], isError: true };
    }
    linkEngine.refreshTitleCache();
    return { content: [{ type: "text" as const, text: `Note deleted: ${result.path}` }] };
  },
);

server.tool(
  "obsidian_search_notes",
  "Search notes by keyword (case-insensitive text match).",
  { query: z.string().describe("Search keyword") },
  async ({ query }) => {
    const results = client.searchNotes(query);
    return { content: [{ type: "text" as const, text: JSON.stringify({ query, count: results.length, results }, null, 2) }] };
  },
);

server.tool(
  "obsidian_get_backlinks",
  "Get all notes that link TO a specific note (backlinks).",
  { path: z.string().describe("Note path relative to vault root") },
  async ({ path: notePath }) => {
    const backlinks = linkEngine.getBacklinks(notePath);
    return { content: [{ type: "text" as const, text: JSON.stringify({ note: notePath, backlinkCount: backlinks.length, backlinks }, null, 2) }] };
  },
);

server.tool(
  "obsidian_get_outlinks",
  "Get all notes that a specific note links TO (outgoing links).",
  { path: z.string().describe("Note path relative to vault root") },
  async ({ path: notePath }) => {
    const outlinks = linkEngine.getOutlinks(notePath);
    return { content: [{ type: "text" as const, text: JSON.stringify({ note: notePath, outlinkCount: outlinks.length, outlinks }, null, 2) }] };
  },
);

server.tool(
  "obsidian_get_graph",
  "Get the complete bidirectional link graph of the vault.",
  { filter: z.string().optional().describe("Filter notes by path substring") },
  async ({ filter }) => {
    const graph = linkEngine.buildGraph();
    let filteredGraph = graph;
    if (filter) {
      const lowerFilter = filter.toLowerCase();
      const matchingNodes = new Set(graph.nodes.filter((n) => n.path.toLowerCase().includes(lowerFilter)).map((n) => n.path));
      const relatedNodes = new Set(matchingNodes);
      for (const edge of graph.edges) {
        if (matchingNodes.has(edge.source)) relatedNodes.add(edge.target);
        if (matchingNodes.has(edge.target)) relatedNodes.add(edge.source);
      }
      filteredGraph = {
        nodes: graph.nodes.filter((n) => relatedNodes.has(n.path)),
        edges: graph.edges.filter((e) => relatedNodes.has(e.source) && relatedNodes.has(e.target)),
      };
    }
    return { content: [{ type: "text" as const, text: JSON.stringify({ totalNodes: filteredGraph.nodes.length, totalEdges: filteredGraph.edges.length, nodes: filteredGraph.nodes, edges: filteredGraph.edges }, null, 2) }] };
  },
);

server.tool(
  "obsidian_inject_links",
  "Analyze content and inject [[wiki-links]] without writing to vault.",
  { content: z.string().describe("Markdown content to process") },
  async ({ content }) => {
    const linked = linkEngine.injectLinks(content);
    return { content: [{ type: "text" as const, text: linked }] };
  },
);

server.tool(
  "obsidian_get_note_titles",
  "Get all note titles in the vault (for link reference).",
  { folder: z.string().optional().describe("Optional subfolder filter") },
  async ({ folder }) => {
    const titles = linkEngine.getNoteTitles(folder);
    return { content: [{ type: "text" as const, text: JSON.stringify({ count: titles.length, titles }, null, 2) }] };
  },
);

// ═══════════════════════════════════════════════════
// Wiki 管理工具
// ═══════════════════════════════════════════════════

server.tool(
  "wiki_init",
  "Initialize the wiki directory structure (raw/ + wiki/ with subdirectories, CLAUDE.md, README.md, indexes).",
  {
    wikiRoot: z.string().optional().describe("Wiki root subfolder within vault (empty = vault root)"),
    pageTypes: z.array(z.string()).optional().describe("Wiki page type directories to create"),
  },
  async ({ wikiRoot, pageTypes }) => {
    const wm = wikiRoot ? new WikiManager(VAULT_PATH, wikiRoot) : wikiManager;
    const result = wm.init({ pageTypes });
    linkEngine.refreshTitleCache();
    return {
      content: [{
        type: "text" as const,
        text: `Wiki initialized!\n\nDirectories created: ${result.created.join(", ")}\nFiles created: ${result.files.join(", ")}`,
      }],
    };
  },
);

server.tool(
  "wiki_status",
  "Get the current wiki status: page counts, raw files, ingested sources, etc.",
  {},
  async () => {
    const status = wikiManager.status();
    return { content: [{ type: "text" as const, text: JSON.stringify(status, null, 2) }] };
  },
);

server.tool(
  "wiki_ingest",
  "Ingest a raw source file into wiki pages. Returns a prompt for the LLM to execute the knowledge compilation. The LLM should then use wiki_commit_ingest or wiki_create_page to create the actual pages.",
  {
    sourcePath: z.string().describe("Path to raw source file (relative to raw/ directory, e.g. 'tech/async-rust.md')"),
  },
  async ({ sourcePath }) => {
    try {
      const result = ingester.ingest(sourcePath);
      return {
        content: [{
          type: "text" as const,
          text: `## Source: ${result.source}\n\n### Ingest Prompt\n\n${result.prompt}\n\n### Existing Wiki Pages\n${result.existingWikiPages.map((p) => `- ${p.path} (${p.title ?? "untitled"})`).join("\n")}`,
        }],
      };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return { content: [{ type: "text" as const, text: `Ingest error: ${msg}` }], isError: true };
    }
  },
);

server.tool(
  "wiki_commit_ingest",
  "Commit the result of an ingest operation: write all generated wiki pages to the vault.",
  {
    sourcePath: z.string().describe("Original raw source file path"),
    summary: z.object({ path: z.string(), content: z.string() }).describe("Summary page"),
    concepts: z.array(z.object({ path: z.string(), content: z.string() })).optional().describe("Concept pages"),
    entities: z.array(z.object({ path: z.string(), content: z.string() })).optional().describe("Entity pages"),
    methods: z.array(z.object({ path: z.string(), content: z.string() })).optional().describe("Method pages"),
  },
  async ({ sourcePath, summary, concepts, entities, methods }) => {
    try {
      const createdFiles = ingester.commitIngest({ sourcePath, summary, concepts, entities, methods });
      return {
        content: [{
          type: "text" as const,
          text: `Ingest committed! Created ${createdFiles.length} wiki pages:\n${createdFiles.map((f) => `- ${f}`).join("\n")}`,
        }],
      };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return { content: [{ type: "text" as const, text: `Commit error: ${msg}` }], isError: true };
    }
  },
);

server.tool(
  "wiki_query",
  "Query the wiki knowledge base. Searches for relevant pages and returns a prompt for the LLM to answer.",
  {
    question: z.string().describe("Question to answer from wiki knowledge"),
  },
  async ({ question }) => {
    const result = querier.query(question);
    const pagesInfo = result.relevantPages.length > 0
      ? result.relevantPages.map((p) => `- ${p.path} (${p.title ?? "untitled"}) [${p.relevance}]`).join("\n")
      : "No relevant pages found.";
    return {
      content: [{
        type: "text" as const,
        text: `## Query: ${question}\n\n### Relevant Pages\n${pagesInfo}\n\n### Answer Prompt\n\n${result.prompt}`,
      }],
    };
  },
);

server.tool(
  "wiki_lint",
  "Run a health check on the wiki: detect duplicate pages, orphan pages, dangling links, missing source annotations, etc.",
  {
    writeReport: z.boolean().optional().default(true).describe("Write lint report to wiki/indexes/lint-report.md"),
  },
  async ({ writeReport }) => {
    const report = linter.lint();
    let reportPath: string | undefined;
    if (writeReport && report.totalPages > 0) {
      reportPath = linter.writeReport(report);
    }
    const summary = Object.entries(report.summary)
      .map(([type, count]) => `- ${type}: ${count}`)
      .join("\n");
    return {
      content: [{
        type: "text" as const,
        text: `## Wiki Lint Report\n\n- Total pages: ${report.totalPages}\n- Issues found: ${report.issueCount}\n\n### Issues by Type\n${summary || "No issues found!"}\n\n${report.issues.slice(0, 20).map((i) => `[${i.severity}] ${i.type}: ${i.message} (${i.path})`).join("\n")}${report.issueCount > 20 ? `\n... and ${report.issueCount - 20} more` : ""}${reportPath ? `\n\nReport saved to: ${reportPath}` : ""}`,
      }],
    };
  },
);

server.tool(
  "wiki_get_sources",
  "List all raw source files and their ingestion status.",
  {
    folder: z.string().optional().describe("Subfolder within raw/ to list"),
  },
  async ({ folder }) => {
    const sources = wikiManager.listSources(folder);
    return {
      content: [{
        type: "text" as const,
        text: JSON.stringify({ count: sources.length, sources }, null, 2),
      }],
    };
  },
);

server.tool(
  "wiki_create_page",
  "Create a single wiki page with proper frontmatter and bidirectional links.",
  {
    type: z.enum(["summary", "concept", "entity", "method", "comparison", "analysis"]).describe("Page type"),
    title: z.string().describe("Page title (also used as filename)"),
    content: z.string().describe("Page content in Markdown"),
    sources: z.array(z.string()).describe("Source references, e.g. ['raw-filename'] or ['summaries/xxx']"),
    autoLink: z.boolean().optional().default(true).describe("Auto-inject [[wiki-links]]"),
  },
  async ({ type, title, content, sources, autoLink }) => {
    const date = new Date().toISOString().slice(0, 10);
    const filename = title.replace(/[^a-zA-Z0-9\u4e00-\u9fff-_]/g, "-") + ".md";
    const wikiBase = WIKI_ROOT ? `${WIKI_ROOT}/wiki` : "wiki";
    const pagePath = `${wikiBase}/${type}s/${filename}`;

    const frontmatter = [
      "---",
      `type: ${type}`,
      `sources: [${sources.map((s) => `[[${s}]]`).join(", ")}]`,
      `created: ${date}`,
      `updated: ${date}`,
      `tags: [wiki, ${type}]`,
      `status: draft`,
      "---",
      "",
    ].join("\n");

    let fullContent = frontmatter + content;
    if (autoLink) {
      fullContent = linkEngine.injectLinks(fullContent);
    }

    const result = client.writeNote(pagePath, fullContent);
    linkEngine.refreshTitleCache();

    // 更新索引
    wikiManager.updateIndex([{ type: `${type}s`, path: pagePath, title }]);

    return {
      content: [{
        type: "text" as const,
        text: `Wiki page created: ${result.path} (type: ${type})`,
      }],
    };
  },
);

// ─── 启动 ─────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
