# LLM Wiki Skill for OpenCode

> 通过 MCP Tools 将 Obsidian Vault 变为 LLM 驱动的知识编译系统

## 概述

本 skill 让 OpenCode 能够操作一个 **LLM Wiki** 知识库，核心思想是 **知识编译**（而非 RAG）：
- `raw/` 存放原始源文件（不可变）
- `wiki/` 存放 LLM 编译后的结构化知识（带 [[双向链接]]）
- 每次摄入让知识库更丰富，无需重复推导

## MCP Tools

### Wiki 管理

| Tool | 用途 | 何时使用 |
|------|------|---------|
| `wiki_init` | 初始化 wiki 目录结构 | 首次使用时 |
| `wiki_status` | 查看 wiki 状态 | 想了解当前知识库概况 |
| `wiki_get_sources` | 列出 raw 源文件及摄入状态 | 想知道哪些文件已/未摄入 |

### 知识操作

| Tool | 用途 | 何时使用 |
|------|------|---------|
| `wiki_ingest` | 摄入 raw 源文件 → 生成 wiki 页面 | 有新资料需要编译 |
| `wiki_commit_ingest` | 提交摄入结果（批量写入页面） | LLM 完成编译后 |
| `wiki_create_page` | 创建单个 wiki 页面 | 手动创建特定页面 |
| `wiki_query` | 查询 wiki 知识库 | 需要基于知识回答问题 |
| `wiki_lint` | Wiki 健康检查 | 定期维护知识库质量 |

### Obsidian 基础

| Tool | 用途 |
|------|------|
| `obsidian_list_notes` | 列出笔记 |
| `obsidian_read_note` | 读取笔记 |
| `obsidian_write_note` | 写入笔记（带自动链接） |
| `obsidian_search_notes` | 搜索笔记 |
| `obsidian_get_backlinks` | 查询反向链接 |
| `obsidian_get_graph` | 获取链接图谱 |

## 典型工作流

### 1. 初始化
```
用户: "帮我初始化 wiki 知识库"
→ 调用 wiki_init
→ 创建 raw/ + wiki/ 目录结构
```

### 2. 摄入知识
```
用户: "把 raw/tech/async-rust.md 编译进 wiki"
→ 调用 wiki_ingest(sourcePath: "tech/async-rust.md")
→ 获取摄入 prompt + 已有页面上下文
→ LLM 分析源文件，生成结构化页面
→ 调用 wiki_commit_ingest 提交结果
→ 或用 wiki_create_page 逐个创建
```

### 3. 查询知识
```
用户: "什么是 async/await? wiki 里怎么说的?"
→ 调用 wiki_query(question: "什么是 async/await")
→ 搜索相关 wiki 页面
→ 基于知识库内容回答，标注 [[来源引用]]
```

### 4. 健康检查
```
用户: "检查一下 wiki 有没有问题"
→ 调用 wiki_lint
→ 检测重复/孤立/缺失引用等
→ 生成 lint-report.md
```

## 规则

1. **raw/ 目录不可变** — 绝不修改 raw/ 中的文件
2. **来源标注必须** — 每个 wiki 页面必须标注 sources
3. **方法页面需质量门控** — 只有可执行、可迁移、非平凡的方法才创建
4. **双向链接** — 所有交叉引用使用 [[wikilink]] 格式
5. **增量编译** — 每次摄入让知识库更丰富，不重复推导

## 目录结构

```
raw/
├── tech/           # 技术文档
├── work/           # 工作文档
├── reading/        # 阅读笔记
├── general/        # 通用
└── assets/         # 资源

wiki/
├── summaries/      # 源文件摘要（与 raw/ 1:1）
├── concepts/       # 概念（"什么是 X"）
├── entities/       # 实体（人物/项目/组织）
├── methods/        # 方法（"如何做 X"）
├── comparisons/    # 对比分析
├── analysis/       # 深度分析
└── indexes/        # 索引 + 日志
    ├── index.md
    ├── log.md
    └── lint-report.md
```

---

*MCP Server: obsidian-llm-wiki | 使用 OpenCode MCP 协议通信*
