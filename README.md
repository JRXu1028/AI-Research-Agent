# AI Research Agent

基于本地 Qwen + LangChain/LangGraph 的轻量级研究 Agent。当前重点是围绕本地大模型调用、RAG 检索增强、工具调用，以及后续微调/评测工作展开。

## 当前状态

已完成本地大模型接入：

```text
模型服务: vLLM OpenAI-compatible server
模型: Qwen2.5-7B-Instruct
服务地址: http://localhost:8001/v1
项目后端: FastAPI, http://localhost:8000
调用方式: LangChain ChatOpenAI
```

服务器已验证环境：

```text
GPU: NVIDIA GeForce RTX 4090
torch: 2.8.0+cu128
vLLM: 0.10.2
transformers: 4.56.1
served model name: qwen2.5-7b-instruct
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 本地大模型服务 | vLLM OpenAI-compatible server |
| LLM | Qwen2.5-7B-Instruct |
| Agent 编排 | LangChain, LangGraph |
| Agent 范式 | ReAct, tool calling |
| RAG | Chroma + sentence-transformers |
| Web 后端 | FastAPI, Uvicorn |
| Web 前端 | Vue 3, Vite |
| 配置管理 | python-dotenv |

> 当前不保留服务端对话历史。每次 `/chat` 请求独立推理，后续重点转向微调、评测和本地模型部署。

## 项目结构

```text
src/
  agent.py              # ReAct 循环：调用模型、执行工具
  langgraph_agent.py    # LangGraph 状态图
  llm.py                # ChatOpenAI 初始化
  config.py             # 环境变量配置
  tools.py              # calculator / knowledge_search
  rag.py                # RAG 初始化
  embeddings.py         # sentence-transformers embedding
  vector_store.py       # Chroma 向量库
  knowledge_base.py     # 示例知识库
frontend/               # Vue 前端
app.py                  # FastAPI 后端入口
main.py                 # 原版 Agent 演示
main_langgraph.py       # LangGraph Agent 演示
requirements.txt
```

## 环境变量

`.env` 示例：

```env
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:8001/v1
LOCAL_LLM_MODEL=qwen2.5-7b-instruct
LOCAL_LLM_API_KEY=not-needed

# RAG 固定使用本地 Chroma：data/chroma_db
```

## 启动本地 Qwen

在服务器终端 1 中启动 vLLM：

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

测试模型服务：

```bash
curl http://127.0.0.1:8001/v1/models
```

## 启动项目后端

终端 2：

```bash
cd /home/ubuntu/project_xjr/AI-Research-Agent
conda activate qwen-vllm
python app.py
```

测试：

```bash
curl http://127.0.0.1:8000/health
```

## 前端

```bash
cd frontend
npm install
npm run dev
```

默认访问 `http://localhost:3000`。

## Git 注意事项

不要提交模型、真实环境变量和本地缓存：

```text
.env
Qwen2.5-7B-Instruct/
models/
data/chroma_db/
__pycache__/
*.pyc
frontend/node_modules/
```
