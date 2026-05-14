# Quickstart

当前工作流：

```text
服务器启动 Qwen/vLLM
  -> 本地 SSH 隧道转发 8001
  -> 本地 FastAPI 后端调用 localhost:8001
  -> 本地 Vue 前端调用 localhost:8000
```

## 1. 服务器启动大模型

在服务器 SSH 窗口执行：

```bash
cd /home/ubuntu/project_xjr/AI-Research-Agent
conda activate qwen-vllm

python -m vllm.entrypoints.openai.api_server \
  --model ./Qwen2.5-7B-Instruct \
  --served-model-name qwen2.5-7b-instruct \
  --host 127.0.0.1 \
  --port 8001 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.85 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

这个窗口不要关。看到 `Application startup complete` 后，服务器侧模型服务就绪。

服务器上可测试：

```bash
curl http://127.0.0.1:8001/v1/models
```

如果显存不足，降低上下文和显存占比：

```bash
python -m vllm.entrypoints.openai.api_server \
  --model ./Qwen2.5-7B-Instruct \
  --served-model-name qwen2.5-7b-instruct \
  --host 127.0.0.1 \
  --port 8001 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.80 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

## 2. 本地连接服务器大模型

本地 PowerShell 新开窗口：

```powershell
ssh -L 8001:127.0.0.1:8001 ubuntu@202.120.87.24
```

这个窗口也不要关。它会把本地 `localhost:8001` 转发到服务器的 vLLM 服务。

本地测试：

```powershell
Invoke-RestMethod http://127.0.0.1:8001/v1/models
```

`.env` 保持：

```env
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:8001/v1
LOCAL_LLM_MODEL=qwen2.5-7b-instruct
LOCAL_LLM_API_KEY=not-needed
```

## 3. 本地启动后端

本地 PowerShell 新开窗口：

```powershell
cd "D:\Project\idea\AI Research Agent"
D:\Software\Anaconda_envs\envs\AIResearch\python.exe app.py
```

看到下面日志表示后端就绪：

```text
Application startup complete
Uvicorn running on http://0.0.0.0:8000
```

本地测试：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

聊天测试：

```powershell
$body = @{
  message = "你好，你现在调用的是服务器上的 Qwen 吗？"
  thread_id = "local-test"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/chat `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

## 4. 本地启动前端

本地 PowerShell 新开窗口：

```powershell
cd "D:\Project\idea\AI Research Agent\frontend"
npm install
npm run dev
```

浏览器打开：

```text
http://localhost:3000
```

## 需要保持的窗口

```text
1. 服务器 vLLM 窗口：Qwen 模型服务，端口 8001
2. 本地 SSH 隧道窗口：localhost:8001 -> server:8001
3. 本地后端窗口：FastAPI，端口 8000
4. 本地前端窗口：Vue/Vite，端口 3000
```

## 当前技术栈

```text
LLM: Qwen2.5-7B-Instruct
Serving: vLLM 0.10.2
Agent: LangChain + LangGraph
RAG: Chroma + sentence-transformers
Backend: FastAPI
Frontend: Vue 3 + Vite
```

当前不保留服务端对话历史。`thread_id` 仅作为接口字段透传，每次请求独立推理。
