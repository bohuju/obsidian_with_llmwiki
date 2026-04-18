# obsidian_with_llmwiki

基于 MCP / LangGraph 的 Obsidian 知识编译系统，将 [obsidian-llm-wiki](https://github.com/gusibi/obsidian-llm-wiki) 的知识编译能力与 Obsidian 双向链接机制整合，支持两种运行模式：

- **`main` 分支**：TypeScript MCP Server，通过 OpenCode / Claude Code 使用
- **`langgraph_node` 分支**：Python LangGraph 节点，可嵌入到任何 LangGraph 工作流

## 核心理念

**知识编译 vs RAG**：传统的 RAG 每次查询都从原始文档检索、重新推导，浪费 token 且结果不稳定。本系统采用**知识编译**模式——LLM 一次性将原始资料编译为结构化 wiki，查询时直接查 wiki，结果稳定且高效。

```
raw/  ──[LLM 编译]──>  wiki/
(源文件, 只读)          (结构化知识, LLM 维护, 带 [[双向链接]])
```

---

## main 分支：MCP Server 模式

适用于 OpenCode / Claude Code 等 AI Agent。

### 安装

```bash
git clone https://github.com/bohuju/obsidian_with_llmwiki.git
cd obsidian_with_llmwiki
npm install
npm run build
```

### 配置 OpenCode

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

### MCP Tools（18 个）

**Obsidian 基础工具（10 个）**

| Tool | 功能 |
|------|------|
| `obsidian_list_notes` | 列出笔记 |
| `obsidian_read_note` | 读取笔记内容 |
| `obsidian_write_note` | 创建/更新笔记（带自动 `[[双向链接]]` 注入） |
| `obsidian_delete_note` | 删除笔记 |
| `obsidian_search_notes` | 关键词搜索 |
| `obsidian_get_backlinks` | 查询反向链接 |
| `obsidian_get_outlinks` | 查询正向链接 |
| `obsidian_get_graph` | 获取完整链接图谱 |
| `obsidian_inject_links` | 对内容注入双向链接（不写入文件） |
| `obsidian_get_note_titles` | 获取所有笔记标题 |

**Wiki 知识编译工具（8 个）**

| Tool | 功能 |
|------|------|
| `wiki_init` | 初始化 wiki 目录结构 |
| `wiki_status` | 查看 wiki 状态 |
| `wiki_ingest` | 将 raw 源文件编译为 wiki 页面 |
| `wiki_commit_ingest` | 批量提交摄入结果 |
| `wiki_create_page` | 创建单个 wiki 页面 |
| `wiki_query` | 基于 wiki 知识库回答问题 |
| `wiki_lint` | Wiki 健康检查 |
| `wiki_get_sources` | 列出 raw 源文件及摄入状态 |

---

## langgraph_node 分支：LangGraph 节点模式

适用于将 Wiki 知识编译作为节点嵌入到其他 LangGraph 工作流。

### 核心能力

- **其他节点的产出 → 放入 raw/ → 自动摄入为 wiki 页面**
- **下游节点运行前 → 查询 wiki → 输出结果给下一个节点**

### 安装

```bash
git clone -b langgraph_node https://github.com/bohuju/obsidian_with_llmwiki.git
cd obsidian_with_llmwiki
pip install -e .
```

依赖：`langgraph`, `langchain-core`, `langchain-anthropic`（自动安装）

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OBSIDIAN_VAULT_PATH` | `/home/bohuju/ObsidianVault` | Obsidian Vault 路径 |
| `WIKI_ROOT` | `""` | Wiki 子目录（空 = Vault 根目录） |

### 3 个独立 Node 函数

可直接 `add_node` 到任何父 LangGraph：

```python
from obsidian_wiki_langgraph.wiki_nodes import wiki_write_raw, wiki_auto_ingest, wiki_query
```

| Node | 功能 | 输入 → 输出 |
|------|------|-------------|
| `wiki_write_raw` | 将上游产出保存到 raw/ | `content` + `content_title` → `raw_saved_path` |
| `wiki_auto_ingest` | 自动摄入 raw 文件为 wiki 页面 | `raw_saved_path` → `ingest_result` |
| `wiki_query` | 查询 wiki 知识库 | `wiki_query` → `wiki_context` |

### State 定义

父 graph 的 State 只需继承 `WikiSubgraphState`：

```python
from obsidian_wiki_langgraph.subgraph_state import WikiSubgraphState

class MyState(WikiSubgraphState, TypedDict, total=False):
    # 加上你自己的字段
    messages: Annotated[list, add_messages]
    your_field: str
```

`WikiSubgraphState` 包含的字段：

| 字段 | 方向 | 说明 |
|------|------|------|
| `content` | 输入 | 上游节点产出的内容 |
| `content_title` | 输入 | 内容标题（用作文件名） |
| `raw_folder` | 输入 | raw/ 子目录（默认 `"general"`） |
| `wiki_query` | 输入 | 要查询 wiki 的问题 |
| `wiki_context` | 输出 | wiki 查询结果（给下游节点用） |
| `raw_saved_path` | 输出 | 内容保存到 raw/ 后的路径 |
| `ingest_result` | 输出 | 摄入结果摘要 |

### 用法 1：独立节点（最灵活）

```python
from langgraph.graph import StateGraph, START, END
from obsidian_wiki_langgraph.subgraph_state import WikiSubgraphState
from obsidian_wiki_langgraph.wiki_nodes import wiki_write_raw, wiki_auto_ingest, wiki_query

class MyState(WikiSubgraphState, TypedDict, total=False):
    messages: Annotated[list, add_messages]

g = StateGraph(MyState)

# 你的节点
g.add_node("scraper", my_scraper_node)     # 产出 content
g.add_node("save", wiki_write_raw)          # content → raw/
g.add_node("ingest", wiki_auto_ingest)      # raw/ → wiki 页面
g.add_node("query", wiki_query)             # wiki → wiki_context
g.add_node("llm", my_llm_node)              # 使用 wiki_context

g.add_edge(START, "scraper")
g.add_edge("scraper", "save")
g.add_edge("save", "ingest")
g.add_edge("ingest", "llm")
g.add_edge("llm", END)

app = g.compile()

# 运行：上游产出内容 → 自动保存到 raw → 摄入 wiki
result = app.invoke({
    "content": "一篇技术文章内容...",
    "content_title": "rust-async",
    "raw_folder": "tech",
})
print(result["raw_saved_path"])   # "raw/tech/rust-async.md"
print(result["ingest_result"])    # "Auto-ingested: wiki/summaries/..."

# 运行：查询 wiki 知识传给下游
result = app.invoke({"wiki_query": "什么是 Fuzzing"})
print(result["wiki_context"])     # wiki 中相关页面内容
```

### 用法 2：子图模式（一行搞定）

```python
from obsidian_wiki_langgraph.subgraph import build_wiki_subgraph

g = StateGraph(MyState)
g.add_node("scraper", my_scraper_node)
g.add_node("wiki", build_wiki_subgraph())  # 子图作为单个节点
g.add_node("llm", my_llm_node)

g.add_edge(START, "scraper")
g.add_edge("scraper", "wiki")    # 有 content → 自动写入+摄入
g.add_edge("wiki", "llm")        # 结果传给下游
g.add_edge("llm", END)
```

子图内部根据 State 自动选择流程：
- State 有 `content` → 执行 `wiki_write_raw` → `wiki_auto_ingest`
- State 有 `wiki_query` → 执行 `wiki_query`
- 也可通过 `wiki_route` 字段强制指定：`"write"` / `"write_and_ingest"` / `"query"`

### 用法 3：CLI 独立运行

```bash
python -m obsidian_wiki_langgraph.graph "初始化 wiki"
python -m obsidian_wiki_langgraph.graph "wiki 状态"
python -m obsidian_wiki_langgraph.graph "什么是 Fuzzing"
python -m obsidian_wiki_langgraph.graph "检查 wiki"
```

### 完整示例

见 `examples/parent_workflow.py`，包含三种使用方式的完整可运行代码。

---

## 项目结构

```
# main 分支（TypeScript MCP）
src/
├── index.ts                # MCP Server 入口，18 个 tools
├── obsidian-client.ts      # Obsidian 文件系统交互
├── link-engine.ts          # 双向链接引擎
├── wiki-manager.ts         # Wiki 生命周期管理
├── wiki-ingester.ts        # 知识摄入
├── wiki-query.ts           # 知识查询
├── wiki-linter.ts          # 健康检查
├── utils.ts                # 工具函数
└── templates/              # 模板
skills/llm-wiki/            # OpenCode Skill

# langgraph_node 分支（Python LangGraph）
src/obsidian_wiki_langgraph/
├── config.py               # 配置（Vault 路径等）
├── state.py                # 独立运行 State
├── graph.py                # 独立运行 Graph（7 节点）
├── router.py               # 路由节点
├── subgraph_state.py       # ★ 子图通用 State（WikiSubgraphState）
├── wiki_nodes.py           # ★ 3 个独立节点函数
├── subgraph.py             # ★ 预装配子图
├── core/                   # 核心逻辑（TS 移植）
│   ├── utils.py
│   ├── obsidian_client.py
│   ├── link_engine.py
│   ├── wiki_manager.py
│   ├── wiki_ingester.py
│   ├── wiki_querier.py
│   └── wiki_linter.py
├── nodes/                  # 独立运行模式的节点
├── tools/                  # @tool 定义（11 个）
└── templates/              # 模板
examples/
└── parent_workflow.py      # ★ 父工作流示例
```

## Wiki 目录结构

```
~/ObsidianVault/
├── raw/                    # 原始源文件（不可变）
│   ├── tech/               # 技术文档
│   ├── work/               # 工作文档
│   ├── reading/            # 阅读笔记
│   ├── general/            # 通用
│   └── assets/             # 资源
├── wiki/                   # 编译后的知识
│   ├── summaries/          # 源文件摘要
│   ├── concepts/           # 概念页面
│   ├── entities/           # 实体页面
│   ├── methods/            # 方法页面
│   ├── comparisons/        # 对比分析
│   ├── analysis/           # 深度分析
│   └── indexes/            # 索引和日志
├── CLAUDE.md               # Wiki 操作规范
└── README.md               # Wiki 说明
```

## 双向链接

所有 wiki 页面使用 Obsidian `[[wikilink]]` 格式：

- **自动注入**：写入笔记时自动匹配已有标题，将关键词转换为 `[[链接]]`
- **反向链接**：查询谁引用了当前笔记
- **知识图谱**：完整节点-边数据
- **来源追踪**：每个段落标注 `(source: [[summaries/xxx]])`

## 所有权规则

| 区域 | LLM | 人类 |
|------|-----|------|
| `raw/` | 只读 | 可读写 |
| `wiki/` | 可读写 | 只读 |

## 致谢

- [obsidian-llm-wiki](https://github.com/gusibi/obsidian-llm-wiki) — 原始知识编译理念和 Skill 设计
- [Obsidian](https://obsidian.md) — 本地知识管理工具
- [MCP](https://modelcontextprotocol.io/) — Model Context Protocol
- [LangGraph](https://github.com/langchain-ai/langgraph) — LangGraph StateGraph

## License

MIT
