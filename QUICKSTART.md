# 快速开始指南

## 5 分钟快速上手

### 1. 环境准备

```bash
# 安装 Python 依赖
pip install -r requirements.txt
```

服务器推理环境已验证组合：

```text
torch 2.8.0+cu128
vLLM 0.10.2
Qwen2.5-7B-Instruct
```

### 2. 配置模型

```bash
cp .env.example .env
```

使用 ECNU API 时，编辑 `.env`，填入你的 API Key：

```bash
LLM_PROVIDER=ecnu
ECNU_API_KEY=your_api_key_here
```

使用本地 Qwen 时，先在服务器启动 vLLM OpenAI 兼容模型服务：

```bash
python -m vllm.entrypoints.openai.api_server \
  --model ./Qwen2.5-7B-Instruct \
  --served-model-name qwen2.5-7b-instruct \
  --host 127.0.0.1 \
  --port 8001 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.85
```

然后确认 `.env` 中配置为：

```bash
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:8001/v1
LOCAL_LLM_MODEL=qwen2.5-7b-instruct
LOCAL_LLM_API_KEY=not-needed
```

> 项目后端默认使用 `8000`，本地 Qwen 服务使用 `8001`，避免端口冲突。

### 3. 运行

**Web 应用（推荐）**：

```bash
# 终端 1：启动后端
python app.py

# 终端 2：启动前端
cd frontend && npm install && npm run dev
```

打开浏览器访问 `http://localhost:3000`。

**命令行演示**：

```bash
python main.py                    # 原版 Agent
python main_langgraph.py          # LangGraph Agent
python main_langgraph_memory.py   # Memory 多轮对话（含交互模式）
```

---

## 运行模式对比

| 模式 | 命令 | 多轮推理 | 对话记忆 | 交互 | 适用场景 |
|------|------|----------|----------|------|----------|
| 原版 Agent | `main.py` | ✅ | ❌ | ❌ | 学习 Agent 基础 |
| LangGraph | `main_langgraph.py` | ✅ | ❌ | ❌ | 学习图结构 |
| Memory | `main_langgraph_memory.py` | ✅ | ✅ | ✅ | 完整体验 |
| Web 应用 | `app.py` + 前端 | ✅ | ✅ | ✅ | 日常使用 |

---

## 配置选项

### 向量数据库切换

```bash
# 本地开发（默认，零配置）
VECTOR_STORE_TYPE=chroma

# 生产环境（需要 PostgreSQL + pgvector）
VECTOR_STORE_TYPE=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_research_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

### Memory 存储切换

```bash
# 本地开发（默认，内存存储，重启丢失）
MEMORY_STORE_TYPE=memory

# 持久化存储
MEMORY_STORE_TYPE=postgres

# 生产推荐（PostgreSQL 持久化 + Redis 缓存加速）
MEMORY_STORE_TYPE=hybrid
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## 测试用例

程序演示了以下典型场景：

1. **计算问题**：`请帮我计算 25 加 17 等于多少？` → 调用 calculator 工具
2. **知识查询**：`华东师范大学在哪里？有几个校区？` → 调用 knowledge_search 工具
3. **上下文追问**：`再加上 10 呢？` → Agent 记得上一轮的 42
4. **代词理解**：`它有几个校区？` → Agent 知道"它"指华东师范大学
5. **长期记忆**：`我刚才问的第一个问题的答案是多少？` → Agent 回顾早期对话

---

## 项目结构

```
AI Research Agent/
├── src/                       # 核心源码
│   ├── agent.py               # Agent 核心逻辑
│   ├── langgraph_agent.py     # LangGraph Agent
│   ├── memory.py              # Memory 管理（三级存储）
│   ├── config.py              # 配置管理
│   ├── llm.py                 # LLM 初始化
│   ├── state.py               # 状态定义
│   ├── tools.py               # 工具定义
│   ├── rag.py                 # RAG 系统（双向量数据库）
│   ├── embeddings.py          # Embedding 模型
│   ├── vector_store.py        # Chroma 向量数据库
│   ├── vector_store_pg.py     # PostgreSQL 向量数据库
│   └── knowledge_base.py      # 知识库数据
├── frontend/                  # Vue 3 前端
│   └── src/
│       ├── App.vue
│       ├── main.js
│       └── style.css
├── docs/                      # 技术文档
├── app.py                     # FastAPI Web 服务
├── main.py                    # 原版 Agent 演示
├── main_langgraph.py          # LangGraph Agent 演示
├── main_langgraph_memory.py   # Memory 多轮对话演示
├── view_knowledge_base.py     # 查看知识库
├── requirements.txt
└── .env.example
```

---

## 常用命令

```bash
# 运行演示
python main.py                    # 原版 Agent
python main_langgraph.py          # LangGraph Agent
python main_langgraph_memory.py   # Memory 多轮对话

# Web 服务
python app.py                     # 启动后端 API

# 查看知识库
python view_knowledge_base.py

# 语法检查
python -m py_compile src/*.py

# 安装依赖
pip install -r requirements.txt
```


---

## 使用技巧

### 修改测试问题

编辑对应 `main_*.py` 文件中的 `test_cases` 或 `conversations` 列表。

### 添加新工具

在 `src/tools.py` 中：

```python
@tool
def my_tool(param: str) -> str:
    """工具描述"""
    return result

def get_all_tools():
    return [calculator, knowledge_search, my_tool]
```

### 扩展知识库

编辑 `src/knowledge_base.py`，删除 `data/chroma_db` 后重新运行（或设置 `force_reload=True`）。

### 调整 RAG 检索数量

在 `src/tools.py` 的 `knowledge_search` 中修改 `k` 参数值。

---

## 常见问题

### Q: 运行时提示 "No module named 'xxx'"

```bash
pip install -r requirements.txt
```

### Q: API 调用失败

检查 `.env` 文件中的 `ECNU_API_KEY` 是否正确。

### Q: 知识库为空

删除 `data/chroma_db` 文件夹，重新运行程序（PostgreSQL 模式使用 `force_reload=True`）。

### Q: PostgreSQL 连接失败

检查 PostgreSQL 服务是否运行，以及 `.env` 中的连接信息是否正确。

### Q: Memory 数据丢失

- `memory` 模式重启即丢失，这是正常的
- 需要持久化请切换到 `postgres` 或 `hybrid` 模式

---

## 验证安装

```bash
# 1. 检查 Python 版本
python --version  # 需要 3.9+

# 2. 检查关键依赖
pip list | grep langchain
pip list | grep chromadb

# 3. 运行测试
python main.py
```

预期输出：

```
============================================================
AI Research Agent - 启动中...
============================================================
[1/5] 初始化 LLM...
      ✅ LLM 初始化完成
[2/5] 初始化 RAG 系统...
      ✅ 知识库初始化完成
...
```

---

## 进阶阅读

- [README.md](README.md) — 项目总览
- [DEPLOYMENT.md](DEPLOYMENT.md) — 生产部署指南
- [docs/RAG_IMPLEMENTATION.md](docs/RAG_IMPLEMENTATION.md) — RAG 系统详解
- [docs/LANGGRAPH_IMPLEMENTATION.md](docs/LANGGRAPH_IMPLEMENTATION.md) — LangGraph Agent 详解
- [docs/MEMORY_IMPLEMENTATION.md](docs/MEMORY_IMPLEMENTATION.md) — Memory 系统详解
- [docs/FUTURE_IMPROVEMENTS.md](docs/FUTURE_IMPROVEMENTS.md) — 未来改进方向
