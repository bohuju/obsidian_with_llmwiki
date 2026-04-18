# CLAUDE.md — obsidian_with_llmwiki

> 本文件定义 OpenCode 在此项目中使用 obsidian-wiki MCP Server 的触发规则

## MCP Server

本项目的 MCP Server 名称: `obsidian-wiki`
Vault 路径: `/home/bohuju/ObsidianVault`

## 触发规则

### 1. 知识摄入触发

当用户提到以下内容时，主动调用 `wiki_ingest`：
- "把这个文件/文档加入 wiki"
- "摄入/编译这个资料"
- "学习这篇文章"
- 提供了一个 raw/ 中的文件路径

执行流程：
1. 调用 `wiki_ingest(sourcePath)` 获取摄入 prompt
2. 分析源文件内容，提取结构化知识
3. 调用 `wiki_commit_ingest` 批量创建 wiki 页面（summary + concepts + entities）
4. 报告创建了哪些页面

### 2. 知识查询触发

当用户提出知识性问题时，优先使用 wiki：
- "什么是 X"
- "关于 X wiki 里怎么说"
- "帮我查一下 X"
- 任何技术概念、方法、工具相关的问题

执行流程：
1. 调用 `wiki_query(question)` 搜索相关 wiki 页面
2. 基于返回的 wiki 内容回答问题
3. 引用来源时使用 `[[wikilink]]` 格式
4. 如果 wiki 中信息不足，告知用户并建议摄入相关源文件

### 3. 优质回答归档触发

当满足以下条件时，主动将 AI 回答归档为 wiki 页面：
- 回答了用户的知识性问题，且内容超过 200 字
- 回答涉及的技术概念在 wiki 中尚无对应页面
- 用户明确表示"保存这个回答"/"记下来"

执行方式：调用 `wiki_create_page` 创建页面：
- type 根据内容选择（concept/entity/method/comparison/analysis）
- sources 标注来源（如之前的对话上下文）
- 内容使用 `obsidian_inject_links` 自动注入双向链接

### 4. Wiki 维护触发

当用户提到以下内容时，执行 wiki 维护：
- "检查 wiki"/"wiki 健康检查" → 调用 `wiki_lint`
- "wiki 状态"/"wiki 里有几个页面" → 调用 `wiki_status`
- "列出源文件"/"哪些文件还没摄入" → 调用 `wiki_get_sources`

### 5. Obsidian 笔记操作触发

当用户需要读写 Obsidian 笔记时：
- "读一下 XXX 笔记" → `obsidian_read_note`
- "创建/写一个笔记" → `obsidian_write_note`（autoLink=true）
- "搜索笔记中包含 XXX 的" → `obsidian_search_notes`
- "谁引用了 XXX" → `obsidian_get_backlinks`
- "显示链接图谱" → `obsidian_get_graph`

### 6. 初始化触发

当用户首次使用 wiki 或在一个空 Vault 中工作时：
- 调用 `wiki_init` 创建目录结构
- 检查 `wiki_status` 确认是否已初始化

## 重要规则

1. `raw/` 目录只读，绝不修改其中的文件
2. 写入 wiki 时必须包含 frontmatter（type, sources, created, tags, status）
3. 所有交叉引用使用 `[[wikilink]]` 格式
4. 方法页面（method）需要通过质量门控：可执行、可迁移、非平凡
5. 优先使用 wiki 知识库回答问题，而非重新推导
