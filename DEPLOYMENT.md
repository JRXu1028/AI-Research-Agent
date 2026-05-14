# Deployment

当前部署形态：

```text
vLLM(Qwen) : 127.0.0.1:8001
FastAPI    : 0.0.0.0:8000
Frontend   : Vue/Vite
Vector DB  : Chroma by default
```

## 1. Start Qwen With vLLM

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

## 2. Configure Backend

`.env`:

```env
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:8001/v1
LOCAL_LLM_MODEL=qwen2.5-7b-instruct
LOCAL_LLM_API_KEY=not-needed
# RAG 固定使用本地 Chroma：data/chroma_db
```

## 3. Start FastAPI

```bash
conda activate qwen-vllm
python app.py
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Notes

- Do not commit model files or `.env`.
- The service currently does not use server-side conversation Memory.
- If server network is unstable, download embedding/model files locally and copy them to the server.
