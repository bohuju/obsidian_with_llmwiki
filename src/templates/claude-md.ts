/**
 * Wiki CLAUDE.md 操作规范模板
 * 基于 obsidian-llm-wiki 项目的 CLAUDE.md 迁移
 */

export function generateClaudeMd(config: {
  vaultName: string;
  wikiRoot: string;
  pageTypes: string[];
}): string {
  return `# Wiki 操作规范 — ${config.vaultName}

> 本文件由 obsidian-llm-wiki MCP Server 自动生成，定义 wiki 知识库的操作规则。

---

## 目录结构

\`\`\`
${config.wikiRoot}/
├── raw/                    # 原始源文件（不可变，只读）
│   ├── tech/               # 技术文档
│   ├── work/               # 工作文档
│   ├── reading/            # 阅读笔记
│   ├── general/            # 通用
│   └── assets/             # 资源文件
├── wiki/                   # 编译后的知识（LLM 拥有，人类只读）
│   ├── summaries/          # 源文件摘要（与 raw/ 1:1 对应）
│   ├── concepts/           # 概念页面（"什么是 X"）
│   ├── entities/           # 实体页面（人物/组织/项目）
│   ├── methods/            # 方法页面（"如何做 X"，需质量门控）
│   ├── comparisons/        # 对比分析
│   ├── analysis/           # 深度分析
│   └── indexes/            # 索引页面
│       ├── index.md        # 总索引
│       └── log.md          # 操作日志
\`\`\`

## 所有权规则

| 区域 | LLM | 人类 |
|------|-----|------|
| \`raw/\` | 只读 | 可读写 |
| \`wiki/\` | 可读写 | 只读 |

**绝对禁止**修改 \`raw/\` 中的任何文件。

## 页面类型说明

${config.pageTypes.map((t) => `- **${t}/**: ${pageTypeDesc(t)}`).join("\n")}

## Frontmatter 规范

每个 wiki 页面 **必须** 包含以下 frontmatter：

\`\`\`yaml
---
type: summary | concept | entity | method | comparison | analysis | index
sources: ["[[raw-filename]]"]    # 来源引用（使用 Obsidian [[wikilink]]）
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [wiki, <type>]
status: draft | stable | reviewed
---
\`\`\`

## 来源标注规则

- **Summary 页面**：frontmatter 的 \`sources\` 字段指向对应的 raw 文件
- **其他页面**：每个内容段落必须标注来源，格式为 \`(source: [[summaries/filename]])\`
- 所有引用使用 Obsidian \`[[wikilink]]\` 格式，只用文件名（不带路径和 .md 后缀）

## 操作流程

### Ingest（知识摄入）

1. 读取 \`raw/\` 中的源文件
2. 生成 summary 页面 → \`wiki/summaries/<source-name>.md\`
3. 提取概念 → 创建/更新 \`wiki/concepts/*.md\`
4. 提取实体 → 创建/更新 \`wiki/entities/*.md\`
5. （可选）提取方法 → \`wiki/methods/*.md\`（需通过质量门控）
6. 添加交叉引用 \`[[wikilink]]\`
7. 更新 \`wiki/indexes/index.md\`
8. 追加 \`wiki/indexes/log.md\`

### Query（知识查询）

1. 在 \`wiki/\` 中搜索相关页面
2. 读取匹配内容
3. 汇总回答，标注 \`[[来源引用]]\`
4. 优质回答可归档为新 wiki 页面

### Lint（健康检查）

检查项：重复页面、孤立页面、缺失引用、缺失来源标注、矛盾内容、方法页面质量、文件名规范

## 方法页面质量门控

创建 methods 页面前必须确认：
1. **可执行性**：读者能按步骤复现
2. **可迁移性**：方法适用于多个场景
3. **非平凡性**：不是显而易见的操作

---

*本规范由 obsidian-llm-wiki MCP Server 维护，请勿手动修改。*
`;
}

function pageTypeDesc(type: string): string {
  const desc: Record<string, string> = {
    summaries: "源文件摘要，与 raw/ 中的文件一一对应",
    concepts: "概念解释页面，回答'什么是 X'",
    entities: "实体页面，描述人物、组织、项目等",
    methods: "方法页面，回答'如何做 X'（需通过质量门控）",
    comparisons: "对比分析页面，比较不同方案的优劣",
    analysis: "深度分析页面，对特定主题的深入探讨",
    indexes: "索引页面，维护 wiki 的目录和日志",
  };
  return desc[type] ?? type;
}
