# CLAUDE.md — Wiki 操作规范

> 本文件定义 LLM 操作 Wiki 知识库的规则和流程

## 核心原则

**知识编译 vs RAG**：本系统采用知识编译模式，而非传统的 RAG 检索模式。

- RAG：每次查询都从原始文档检索、重新推导 → 浪费 token，结果不稳定
- 知识编译：LLM 一次性将原始资料编译为结构化 wiki → 查询时直接查 wiki，结果稳定且高效

## 所有权

| 区域 | LLM | 人类 |
|------|-----|------|
| `raw/` | **只读** | 可读写 |
| `wiki/` | 可读写 | **只读** |

**绝对禁止**修改 `raw/` 中的任何文件。

## Wiki 页面类型

### summary（摘要）
- 与 `raw/` 文件 **1:1 对应**
- 提炼源文件核心要点
- frontmatter `sources` 指向 raw 文件

### concept（概念）
- 回答 **"什么是 X"**
- 每个段落标注来源 `(source: [[summaries/xxx]])`

### entity（实体）
- 描述人物、组织、项目、工具等
- 用 `[[wikilink]]` 与其他实体交叉引用

### method（方法）
- 回答 **"如何做 X"**
- **必须通过质量门控**：
  1. 可执行性：读者能按步骤复现
  2. 可迁移性：方法适用于多个场景
  3. 非平凡性：不是显而易见的操作

### comparison（对比）
- 比较两个或多个方案/工具/概念的优劣
- 列出各自的适用场景

### analysis（分析）
- 对特定主题的深入分析
- 可以跨多个源文件综合分析

## Frontmatter 规范

```yaml
---
type: summary | concept | entity | method | comparison | analysis | index
sources: ["[[raw-filename]]"]
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [wiki, <type>]
status: draft | stable | reviewed
---
```

## 来源标注规则

1. **Summary 页面**：frontmatter 的 `sources` 指向 raw 文件
   ```yaml
   sources: ["[[async-rust]]"]
   ```

2. **其他页面**：每个内容段落标注来源
   ```markdown
   Async/await 是 Rust 的异步编程模型。(source: [[summaries/async-rust]])
   ```

3. **引用格式**：只用文件名，不带路径和 `.md` 后缀

## 操作流程

### Ingest 流程

```
1. 用户指定 raw/ 中的源文件
2. 调用 wiki_ingest → 获取源内容 + 已有 wiki 上下文
3. LLM 分析源文件，提取结构化知识
4. 创建页面（优先用 wiki_commit_ingest 批量提交）：
   a. summary 页面（必须）
   b. concept 页面（按需）
   c. entity 页面（按需）
   d. method 页面（需通过质量门控）
5. 自动注入 [[双向链接]]
6. 更新索引和日志
```

### Query 流程

```
1. 调用 wiki_query(question)
2. 获取相关 wiki 页面内容
3. 基于知识库回答，标注 [[来源]]
4. 如果 wiki 中信息不足，建议摄入相关源文件
5. 优质回答可归档为新 wiki 页面
```

### Lint 流程

```
1. 调用 wiki_lint
2. 检查：
   - 重复页面（标题相似 → 建议合并）
   - 孤立页面（无入链无出链）
   - 悬空链接（引用了不存在的页面）
   - 缺失来源标注
   - 方法页面质量
3. 生成 lint-report.md
```

## 双向链接机制

所有 wiki 页面使用 Obsidian `[[wikilink]]` 格式：

- **正向链接**：当前页面引用了谁
- **反向链接**：谁引用了当前页面（通过 `obsidian_get_backlinks` 查询）
- **知识图谱**：`obsidian_get_graph` 返回完整链接网络

MCP Server 会自动在写入时注入已知笔记标题的链接。

---

*本规范由 obsidian-llm-wiki MCP Server 维护*
