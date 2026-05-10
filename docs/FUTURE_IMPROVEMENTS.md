# 未来改进方向

基于 2026 年 AI Agent 领域主流技术趋势，结合本项目当前架构，梳理未来可行的改进方向。

---

## 1. MCP 协议集成（Model Context Protocol）

**现状**：工具（calculator, knowledge_search）硬编码在 `src/tools.py` 中，扩展需要修改代码。

**改进方向**：

MCP 是 Anthropic 发布的开放标准协议，将工具、资源和提示的集成标准化。通过 MCP，Agent 可以动态发现和调用任何兼容 MCP 的外部服务。

```
当前: Agent → tools.py (硬编码工具)
未来: Agent → MCP Client → MCP Server A (计算)
                          → MCP Server B (知识库)
                          → MCP Server C (第三方服务)
```

**收益**：
- 工具热插拔，无需修改 Agent 代码
- 复用社区 MCP Server 生态（数据库、文件系统、API 等）
- 工具可跨项目、跨语言共享

**参考**：[Model Context Protocol](https://modelcontextprotocol.io)

---

## 2. 流式输出（Streaming）

**现状**：Agent 需等待完整推理完成后才返回结果，用户感知延迟明显。

**改进方向**：

通过 LangGraph 的 `astream()` / `astream_events()` 实现 Token 级别的实时输出：

```python
# 当前
final_state = agent.invoke(state, config)

# 未来
async for event in agent.astream_events(state, config):
    if event["event"] == "on_chat_model_stream":
        yield event["data"]["chunk"].content  # 逐 Token 推送到前端
```

**收益**：
- 首字延迟降低 80%+
- 用户感知响应更快
- 配合 SSE（Server-Sent Events）推送到浏览器

---

## 3. 多 Agent 协作

**现状**：单一 Agent 处理所有任务类型。

**改进方向**：

引入多 Agent 编排模式，不同 Agent 各司其职：

```
Supervisor Agent（调度者）
  ├── Research Agent（负责信息检索）
  ├── Code Agent（负责代码生成）
  ├── Math Agent（负责数学推理）
  └── Summary Agent（负责总结输出）
```

**可选框架**：
- **LangGraph** — 多 Agent StateGraph，自定义编排
- **CrewAI** — 角色化 Agent，自动任务分解
- **AutoGen** — 微软出品，支持代码执行和多轮对话

**收益**：
- 每个 Agent 可独立优化（不同模型、不同温度）
- 复杂任务自动分解
- 失败隔离，单 Agent 异常不影响全局

---

## 4. Agent 可观测性（Observability）

**现状**：仅通过 `print()` 输出调试信息，缺乏结构化追踪。

**改进方向**：

集成专业 AI 可观测平台：

| 平台 | 特点 |
|------|------|
| **LangSmith** | LangChain 官方，全链路追踪、评估、数据集管理 |
| **LangFuse** | 开源替代，自托管，Token 成本统计 |
| **Weave (W&B)** | Weights & Biases 出品，实验对比 |

**具体改进**：
- 每次 Agent 调用生成 Trace（LLM 调用链 + 工具调用 + 耗时）
- Token 用量与成本统计
- 用户反馈收集与评估数据集构建
- 回归测试（Prompt 变更前后对比）

---

## 5. RAG 增强

**现状**：基于 Chroma / pgvector 的语义检索，Top-K 返回，无重排序。

**改进方向**：

### 5.1 混合检索（Hybrid Search）
结合 BM25 关键词检索 + 向量语义检索，取长补短。

### 5.2 Reranker 重排序
检索后增加 Reranker 模型（如 Cohere Rerank、BGE-Reranker）对候选文档二次排序。

### 5.3 GraphRAG
将知识库文档构建为知识图谱，支持多跳推理（"X 的导师的学生的论文"）。

```
当前 RAG: query → embedding → top-K → LLM
GraphRAG: query → entity extraction → graph traversal → context → LLM
```

### 5.4 多模态 RAG
支持图片、PDF、表格等多格式文档的检索增强。

---

## 6. 结构化输出（Structured Output）

**现状**：Agent 输出为自由文本，前端解析依赖非结构化的 `final_answer`。

**改进方向**：

利用 LLM 的结构化输出能力（JSON Mode / Function Calling），让 Agent 返回结构化数据：

```python
class AgentResponse(BaseModel):
    answer: str
    sources: list[Source]
    tool_calls_made: list[str]
    confidence: float
    follow_up_questions: list[str]
```

**收益**：
- 前端可直接渲染结构化 UI（信息卡片、来源引用）
- 便于下游系统消费
- 可做置信度判断与人工审核路由

---

## 7. 持久化对话管理

**现状**：通过 thread_id 区分会话，但缺少对话列表、历史搜索、导出等功能。

**改进方向**：

- **对话列表 API**：列出用户所有会话及其摘要
- **全文搜索**：搜索历史对话内容
- **对话导出**：Markdown / PDF 导出
- **对话分析**：话题聚类、使用统计
- **会话 TTL**：自动清理过期对话

---

## 8. 安全与护栏（Guardrails）

**现状**：无输入/输出过滤，无权限控制。

**改进方向**：

- **输入护栏**：敏感词过滤、Prompt Injection 检测
- **输出护栏**：事实性校验、有害内容拦截
- **RBAC 权限**：不同用户可访问不同工具和知识库
- **审计日志**：记录所有 Agent 调用，满足合规需求

**可选方案**：
- **NeMo Guardrails**（NVIDIA 开源）
- **Guardrails AI**（结构化验证）
- **LangChain Hub** 的 Guardrails 模板

---

## 9. Prompt 管理与版本控制

**现状**：Prompt 以 f-string 形式散落在代码中。

**改进方向**：

- **Prompt 模板化**：集中管理，支持变量注入
- **版本控制**：Prompt 变更与 Git 关联，可追溯
- **A/B 测试**：不同 Prompt 效果对比
- **动态 Prompt**：根据用户画像/场景自动选择模板

**可选方案**：
- **LangSmith Hub** — Prompt 仓库 + 版本管理
- **Agenta** — 开源 Prompt 实验平台

---

## 10. 本地模型支持

**现状**：依赖 ECNU API（OpenAI 兼容接口），需网络连接。

**改进方向**：

通过 Ollama / vLLM 支持本地部署的开源模型：

```bash
# .env
LLM_PROVIDER=ollama              # ollama | ecnu | openai
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:14b
```

**收益**：
- 离线可用，无 API 费用
- 数据不出本地，满足隐私合规
- 可微调专用模型

**候选模型**（2026 年）：
- Qwen 3 系列（中文能力强）
- DeepSeek-V3 / R1（推理能力强）
- Llama 4 系列（生态丰富）

---

## 11. A2A 协议（Agent-to-Agent）

**现状**：Agent 独立运行，无法与其他 Agent 系统互通。

**改进方向**：

Google 提出的 Agent-to-Agent (A2A) 协议，让不同框架构建的 Agent 能互相发现、通信和协作。

```
本项目 Agent ←→ A2A ←→ 第三方 Agent
                  ↕
              Agent Card（能力声明 + 接口发现）
```

**收益**：
- 跨团队、跨组织 Agent 协作
- 发现并调用外部 Agent 的能力
- 与 MCP 互补（MCP 连接工具，A2A 连接 Agent）

---

## 12. 前端体验升级

**现状**：Vue 3 单页聊天界面，功能基础。

**改进方向**：

- **Markdown 渲染**：支持代码高亮、表格、LaTeX 公式
- **来源引用**：展示 RAG 检索到的原始文档
- **思考过程可视化**：展示 Agent 的推理链（Chain-of-Thought）
- **语音输入/输出**：Web Speech API 集成
- **暗色模式**：跟随系统主题
- **移动端适配**：PWA 支持，离线使用

---

## 优先级建议

| 优先级 | 方向 | 理由 |
|--------|------|------|
| 🔴 高 | 流式输出 | 用户体验质变，实现成本低 |
| 🔴 高 | 结构化输出 | 前端交互升级的基础设施 |
| 🔴 高 | Agent 可观测性 | 从"黑盒"到"可调试"的关键 |
| 🟡 中 | MCP 协议集成 | 工具生态质变，但需要架构调整 |
| 🟡 中 | RAG 增强（Hybrid + Reranker） | 检索质量明显提升 |
| 🟡 中 | 安全与护栏 | 生产环境的必要条件 |
| 🟢 低 | 本地模型支持 | 取决于部署环境需求 |
| 🟢 低 | 多 Agent 协作 | 适合复杂场景，当前可暂缓 |
| 🟢 低 | A2A 协议 | 生态尚未成熟，保持关注 |

---

## 企业级落地

以上改进方向中，**RAG + Fine-tuning 双引擎架构** 是最具简历竞争力的综合方案。详见：

> [docs/ENTERPRISE_ROADMAP.md](ENTERPRISE_ROADMAP.md) — RAG + SFT/DPO/RAFT 微调，含分阶段实施计划

## 参考资源

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
- [LangGraph Multi-Agent](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [LangSmith](https://www.langchain.com/langsmith)
- [LangFuse](https://langfuse.com)
- [GraphRAG (Microsoft)](https://github.com/microsoft/graphrag)
- [CrewAI](https://www.crewai.com)
- [Ollama](https://ollama.com)
- [Google A2A Protocol](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
