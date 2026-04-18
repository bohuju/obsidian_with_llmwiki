# obsidian_with_llmwiki

基于 MCP (Model Context Protocol) 的 Obsidian 知识编译系统，将 [obsidian-llm-wiki](https://github.com/gusibi/obsidian-llm-wiki) 的知识编译能力与 Obsidian 双向链接机制整合为 MCP Server，让 AI Agent（OpenCode、Claude Code 等）能够构建和维护结构化的知识库。

## 核心理念

**知识编译 vs RAG**：传统的 RAG 每次查询都从原始文档检索、重新推导，浪费 token 且结果不稳定。本系统采用**知识编译**模式——LLM 一次性将原始资料编译为结构化 wiki，查询时直接查 wiki，结果稳定且高效。

```
raw/  ──[LLM 编译]──>  wiki/
(源文件, 只读)          (结构化知识, LLM 维护, 带 [[双向链接]])
```

## 功能

### Obsidian 基础工具（10 个）

| Tool | 功能 |
|------|------|
| `obsidian_list_notes` | 列出笔记 |
| `obsidian_read_note` | 读取笔记内容 |
| `obsidian_write_note` | 创建/更新笔记（带自动 `[[双向链接]]` 注入） |
| `obsidian_delete_note` | 删除笔记 |
| `obsidian_search_notes` | 关键词搜索 |
| `obsidian_get_backlinks` | 查询反向链接（谁引用了这篇笔记） |
| `obsidian_get_outlinks` | 查询正向链接（这篇笔记引用了谁） |
| `obsidian_get_graph` | 获取完整链接图谱 |
| `obsidian_inject_links` | 对内容注入双向链接（不写入文件） |
| `obsidian_get_note_titles` | 获取所有笔记标题 |

### Wiki 知识编译工具（8 个）

| Tool | 功能 |
|------|------|
| `wiki_init` | 初始化 wiki 目录结构（`raw/` + `wiki/`） |
| `wiki_status` | 查看 wiki 状态（页面数、摄入进度等） |
| `wiki_ingest` | 将 raw 源文件编译为结构化 wiki 页面 |
| `wiki_commit_ingest` | 批量提交摄入结果 |
| `wiki_create_page` | 创建单个 wiki 页面（带 frontmatter 和来源标注） |
| `wiki_query` | 基于 wiki 知识库回答问题 |
| `wiki_lint` | Wiki 健康检查（重复/孤立/悬空链接/缺失来源等） |
| `wiki_get_sources` | 列出 raw 源文件及摄入状态 |

## Wiki 目录结构

```
~/ObsidianVault/
├── raw/                    # 原始源文件（不可变，LLM 只读）
│   ├── tech/               # 技术文档
│   ├── work/               # 工作文档
│   ├── reading/            # 阅读笔记
│   ├── general/            # 通用
│   └── assets/             # 资源
├── wiki/                   # LLM 编译后的知识（LLM 拥有）
│   ├── summaries/          # 源文件摘要（与 raw/ 1:1 对应）
│   ├── concepts/           # 概念页面（"什么是 X"）
│   ├── entities/           # 实体页面（人物/项目/工具）
│   ├── methods/            # 方法页面（"如何做 X"，需质量门控）
│   ├── comparisons/        # 对比分析
│   ├── analysis/           # 深度分析
│   └── indexes/            # 索引和日志
│       ├── index.md
│       ├── log.md
│       └── lint-report.md
├── CLAUDE.md               # Wiki 操作规范（自动生成）
└── README.md               # Wiki 说明（自动生成）
```

## 双向链接

所有 wiki 页面使用 Obsidian `[[wikilink]]` 格式互相关联：

- **自动注入**：写入笔记时自动匹配已有笔记标题，将关键词转换为 `[[链接]]`
- **反向链接**：通过 `obsidian_get_backlinks` 查询谁引用了当前笔记
- **知识图谱**：`obsidian_get_graph` 返回完整的节点-边数据
- **来源追踪**：每个 wiki 段落标注 `(source: [[summaries/xxx]])`

## 安装

```bash
git clone https://github.com/bohuju/obsidian_with_llmwiki.git
cd obsidian_with_llmwiki
npm install
npm run build
```

## 配置

### OpenCode

在 `~/.config/opencode/opencode.json` 中添加：

```json
{
  "mcp": {
    "obsidian-wiki": {
      "type": "local",
      "command": ["node", "/path/to/obsidian_with_llmwiki/build/index.js"],
      "environment": {
        "OBSIDIAN_VAULT_PATH": "/path/to/your/ObsidianVault",
        "WIKI_ROOT": ""
      },
      "enabled": true,
      "timeout": 15000
    }
  }
}
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OBSIDIAN_VAULT_PATH` | `/home/bohuju/ObsidianVault` | Obsidian Vault 路径 |
| `WIKI_ROOT` | `""` | Wiki 子目录（空 = Vault 根目录） |

## 使用

### 1. 初始化 Wiki

```
> call wiki_init
```

### 2. 摄入知识

将原始资料放入 `raw/` 目录，然后：

```
> call wiki_ingest with sourcePath "tech/my-document.md"
> （LLM 分析源文件后）
> call wiki_commit_ingest with summary, concepts, entities...
```

### 3. 查询知识

```
> call wiki_query with question "什么是 Fuzzing？有哪些分类？"
```

### 4. 健康检查

```
> call wiki_lint
```

## 项目结构

```
src/
├── index.ts                # MCP Server 入口，注册 18 个 tools
├── obsidian-client.ts      # Obsidian 文件系统交互层
├── link-engine.ts          # 双向链接引擎（注入/解析/backlinks/图谱）
├── wiki-manager.ts         # Wiki 生命周期管理（init/status/detect）
├── wiki-ingester.ts        # 知识摄入（构建摄入 prompt + 提交）
├── wiki-query.ts           # 知识查询（关键词搜索 + prompt 构建）
├── wiki-linter.ts          # 健康检查（重复/孤立/悬空链接/来源标注）
├── utils.ts                # 工具函数
└── templates/
    ├── claude-md.ts        # Wiki CLAUDE.md 操作规范模板
    └── readme-md.ts        # Wiki README.md 模板
skills/
└── llm-wiki/
    ├── SKILL.md            # OpenCode Skill 定义
    └── CLAUDE.md           # Wiki 操作规范
```

## 所有权规则

| 区域 | LLM | 人类 |
|------|-----|------|
| `raw/` | 只读 | 可读写 |
| `wiki/` | 可读写 | 只读 |

## 致谢

- [obsidian-llm-wiki](https://github.com/gusibi/obsidian-llm-wiki) — 原始知识编译理念和 Claude Code Skill 设计
- [Obsidian](https://obsidian.md) — 本地知识管理工具
- [MCP](https://modelcontextprotocol.io/) — Model Context Protocol

## License

MIT
