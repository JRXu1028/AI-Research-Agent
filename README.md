# AI Research Agent

基于 LangChain + LangGraph 的状态驱动 AI Agent 系统，集成 RAG 检索增强生成，支持命令行与 Web 两种交互方式。

## 项目特性

- **模块化架构** — 职责清晰的模块设计，每个模块可独立测试和替换
- **状态驱动** — 基于 AgentState 的统一状态管理，易于调试和扩展
- **ReAct 模式** — 标准 Reasoning + Acting 多轮推理循环
- **工具调用** — LLM 驱动工具选择（calculator + knowledge_search），无硬编码路由
- **RAG 系统** — 检索增强生成，基于真实文档回答，减少模型幻觉
- **双向量数据库** — Chroma（本地开发）+ PostgreSQL/pgvector（生产环境），按配置切换
- **三级 Memory 存储** — 内存 / PostgreSQL / PostgreSQL+Redis（Hybrid），适应不同部署规模
- **LangGraph Agent** — 图结构 Agent 实现，支持可视化、流式输出和复杂流程编排
- **Web 应用** — FastAPI 后端 + Vue 3 前端，开箱即用
- **多轮对话** — 完整上下文记忆，支持跨轮次引用和追问

## 当前状态

当前已完成本地大模型接入：服务器通过 vLLM 启动 `Qwen2.5-7B-Instruct`，暴露 OpenAI 兼容接口 `http://localhost:8001/v1`；项目后端通过 `langchain-openai` 的 `ChatOpenAI` 调用该本地模型。

已验证的服务器推理环境：

```text
GPU: NVIDIA GeForce RTX 4090
torch: 2.8.0+cu128
vLLM: 0.10.2
model: Qwen2.5-7B-Instruct
served model name: qwen2.5-7b-instruct
```

## 技术栈

| 层级 | 技术 |
|------|------|
| **LLM 框架** | LangChain, LangGraph |
| **本地大模型服务** | vLLM OpenAI-compatible server |
| **LLM 模型** | Qwen2.5-7B-Instruct |
| **LLM 调用方式** | `ChatOpenAI` → `http://localhost:8001/v1` |
| **向量数据库** | Chroma（开发）/ PostgreSQL + pgvector（生产） |
| **Embedding** | HuggingFace sentence-transformers (`all-MiniLM-L6-v2`) |
| **Memory** | MemorySaver / PostgresSaver / Hybrid (PostgreSQL + Redis) |
| **Web 后端** | FastAPI + Uvicorn |
| **Web 前端** | Vue 3 + Vite |
| **数据库** | PostgreSQL 15+, Redis 7+ |
| **语言** | Python 3.10（服务器环境） |

## 项目结构

```
AI Research Agent/
├── src/                          # 后端核心源码
│   ├── agent.py                  # Agent 核心逻辑（call_model, execute_tools）
│   ├── langgraph_agent.py        # LangGraph Agent（ReAct 图结构 + Memory）
│   ├── memory.py                 # Memory 管理（memory / postgres / hybrid）
│   ├── config.py                 # 配置管理（环境变量 + 多后端配置）
│   ├── llm.py                    # LLM 初始化
│   ├── state.py                  # AgentState 状态定义
│   ├── tools.py                  # 工具定义（calculator, knowledge_search）
│   ├── rag.py                    # RAG 系统（双向量数据库切换）
│   ├── embeddings.py             # Embedding 模型管理
│   ├── vector_store.py           # Chroma 向量数据库
│   ├── vector_store_pg.py        # PostgreSQL + pgvector 向量数据库
│   └── knowledge_base.py         # 知识库数据定义（8 篇文档）
├── frontend/                     # Vue 3 前端
│   ├── src/
│   │   ├── App.vue               # 主聊天组件
│   │   ├── main.js               # 入口文件
│   │   └── style.css             # 全局样式
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── docs/                         # 技术文档
│   ├── RAG_IMPLEMENTATION.md
│   ├── LANGGRAPH_IMPLEMENTATION.md
│   ├── MEMORY_IMPLEMENTATION.md
│   └── FUTURE_IMPROVEMENTS.md
├── data/
│   └── chroma_db/                # Chroma 持久化数据（使用 chroma 模式时）
├── app.py                        # FastAPI Web 服务入口
├── main.py                       # 命令行演示（原版 Agent）
├── main_langgraph.py             # 命令行演示（LangGraph Agent）
├── main_langgraph_memory.py      # 命令行演示（Memory 多轮对话）
├── view_knowledge_base.py        # 查看知识库工具
├── requirements.txt              # Python 依赖
├── .env.example                  # 环境变量模板
├── README.md
├── QUICKSTART.md
└── DEPLOYMENT.md
```

### 核心模块

| 模块 | 职责 |
|------|------|
| `config.py` | 管理所有配置项：API、PostgreSQL、Redis、向量数据库类型、Memory 类型 |
| `state.py` | 定义 AgentState（messages, tool_calls, final_answer, error） |
| `llm.py` | 初始化 LLM，绑定 API 配置 |
| `tools.py` | 定义 Agent 可用工具（calculator, knowledge_search） |
| `agent.py` | 原版 Agent 核心逻辑（call_model + execute_tools） |
| `langgraph_agent.py` | LangGraph StateGraph 实现，支持 checkpointer 注入 |
| `memory.py` | Memory 后端工厂：根据配置创建 MemorySaver / PostgresSaver / Hybrid |
| `rag.py` | RAG 系统，根据 VECTOR_STORE_TYPE 自动选择向量数据库后端 |
| `vector_store.py` | Chroma 向量数据库（本地文件持久化） |
| `vector_store_pg.py` | PostgreSQL + pgvector 向量数据库（生产环境） |
| `embeddings.py` | HuggingFace Embedding 模型管理 |
| `knowledge_base.py` | 知识库数据（8 篇文档，覆盖华师大信息 + 技术知识） |

## 快速开始

### Web 应用（推荐）

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，使用本地 Qwen

# 3. 安装前端依赖
cd frontend && npm install && cd ..

# 4. 启动后端（默认 http://localhost:8000）
python app.py

# 5. 另一个终端启动前端（默认 http://localhost:3000）
cd frontend && npm run dev
```

### 命令行

```bash
python main.py                    # 原版 Agent（while 循环）
python main_langgraph.py          # LangGraph Agent（图结构）
python main_langgraph_memory.py   # Memory 多轮对话（含交互模式）
python view_knowledge_base.py     # 查看知识库
```

> 详细说明见 [QUICKSTART.md](QUICKSTART.md)

## 核心功能

### 1. 三种 Agent 运行模式

| 特性 | main.py | main_langgraph.py | main_langgraph_memory.py |
|------|---------|-------------------|--------------------------|
| 实现方式 | while 循环 | StateGraph 图结构 | StateGraph + Checkpointer |
| 多轮推理 | ✅ | ✅ | ✅ |
| 对话记忆 | ❌ | ❌ | ✅ |
| 可视化 | ❌ | 支持 | 支持 |
| 交互模式 | ❌ | ❌ | ✅ |

### 2. 双向量数据库

开发环境使用 Chroma（零配置），生产环境切换到 PostgreSQL + pgvector：

```bash
# .env 配置
VECTOR_STORE_TYPE=chroma      # 本地开发
VECTOR_STORE_TYPE=postgres    # 生产环境
```

### 3. 三级 Memory 存储

| 模式 | 后端 | 持久化 | 适用场景 |
|------|------|--------|----------|
| `memory` | 内存 | ❌ 重启丢失 | 本地开发、调试 |
| `postgres` | PostgreSQL | ✅ | 单机生产部署 |
| `hybrid` | PostgreSQL + Redis | ✅ | 生产推荐（最佳性能） |

```bash
# .env 配置
MEMORY_STORE_TYPE=memory      # 本地开发
MEMORY_STORE_TYPE=postgres    # 持久化
MEMORY_STORE_TYPE=hybrid      # 生产推荐
```

### 4. RAG 检索增强生成

```
用户提问 → 语义向量化 → 向量数据库检索 Top-K → LLM 基于检索结果生成答案
```

知识库包含 8 篇文档（华东师范大学信息 + Python/LangChain/RAG 技术知识），所有回答均有据可查。

### 5. 工具系统

Agent 通过 `tool_calls` 自主决定何时调用工具：
- **calculator** — 数学运算
- **knowledge_search** — RAG 知识库检索

### 6. ReAct 循环

```
START → agent (LLM 推理) → 有 tool_calls? → tools (执行工具) → agent → ... → END
```

## 配置参考

```bash
# .env 文件
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:8001/v1
LOCAL_LLM_MODEL=qwen2.5-7b-instruct
LOCAL_LLM_API_KEY=not-needed

# ECNU_API_KEY 仅在 LLM_PROVIDER=ecnu 时需要
ECNU_API_KEY=your_api_key_here

# 向量数据库
VECTOR_STORE_TYPE=chroma                # chroma | postgres

# PostgreSQL（VECTOR_STORE_TYPE=postgres 或 MEMORY_STORE_TYPE=postgres/hybrid 时必填）
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_research_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Memory 存储
MEMORY_STORE_TYPE=memory                # memory | postgres | hybrid

# Redis（MEMORY_STORE_TYPE=hybrid 时必填）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

## 服务器启动本地 Qwen

在一个终端中保持 vLLM 服务运行：

```bash
cd /home/ubuntu/project_xjr/AI-Research-Agent
conda activate qwen-vllm

python -m vllm.entrypoints.openai.api_server \
  --model ./Qwen2.5-7B-Instruct \
  --served-model-name qwen2.5-7b-instruct \
  --host 127.0.0.1 \
  --port 8001 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.85
```

另一个终端启动项目后端：

```bash
cd /home/ubuntu/project_xjr/AI-Research-Agent
conda activate qwen-vllm
python app.py
```

Qwen 服务根路径 `/` 返回 404 是正常的，请测试 `/v1/models` 或 `/v1/chat/completions`。

## 扩展指南

### 添加新工具

在 `src/tools.py` 中使用 `@tool` 装饰器定义，加入 `get_all_tools()` 返回列表。

### 扩展知识库

编辑 `src/knowledge_base.py` 添加文档，删除 `data/chroma_db` 目录后重新运行即可重建索引（PostgreSQL 模式使用 `force_reload=True`）。

### 添加 LangGraph 节点

在 `src/langgraph_agent.py` 中添加节点函数，注册到 `StateGraph` 并设置边即可。

## 文档索引

| 文档 | 内容 |
|------|------|
| [QUICKSTART.md](QUICKSTART.md) | 快速上手、常用命令、常见问题 |
| [DEPLOYMENT.md](DEPLOYMENT.md) | 生产部署指南（PostgreSQL + Redis + Docker） |
| [docs/RAG_IMPLEMENTATION.md](docs/RAG_IMPLEMENTATION.md) | RAG 系统详解（双向量数据库） |
| [docs/LANGGRAPH_IMPLEMENTATION.md](docs/LANGGRAPH_IMPLEMENTATION.md) | LangGraph Agent 实现详解 |
| [docs/MEMORY_IMPLEMENTATION.md](docs/MEMORY_IMPLEMENTATION.md) | Memory 三级存储详解 |
| [docs/FUTURE_IMPROVEMENTS.md](docs/FUTURE_IMPROVEMENTS.md) | 未来技术改进方向 |
| [docs/ENTERPRISE_ROADMAP.md](docs/ENTERPRISE_ROADMAP.md) | 企业级落地方案：RAG + Fine-tuning 双引擎 |

## 架构设计原则

1. **模块化** — 每个模块职责单一，可独立替换
2. **状态驱动** — 统一 AgentState，函数签名一致 `(state, ...) -> state`
3. **LLM 驱动路由** — 通过 `tool_calls` 决定流程，不使用硬编码关键词
4. **代码复用** — LangGraph Agent 100% 复用 `agent.py` 的核心逻辑
5. **配置切换** — 向量数据库 / Memory 后端通过环境变量切换，无需改代码

## 学习资源

- [LangChain 文档](https://python.langchain.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [ReAct 论文](https://arxiv.org/abs/2210.03629)
- [RAG 论文](https://arxiv.org/abs/2005.11401)
- [Chroma 文档](https://docs.trychroma.com/)
- [pgvector](https://github.com/pgvector/pgvector)

## License

MIT License
