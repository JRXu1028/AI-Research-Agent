# 企业级落地实施方案：RAG + Fine-tuning 双引擎知识库问答系统

## 一句话定位

面向企业内部知识库的智能问答系统，通过 **RAG 检索增强 + 领域模型微调** 双引擎架构，在保证答案准确性的同时持续优化响应质量，形成"使用→反馈→训练→提升"的数据飞轮。

---

## 为什么这个场景适合写在简历上

| 能力维度 | 体现点 |
|----------|--------|
| **LLM 应用工程** | LangGraph Agent、RAG Pipeline、多源数据摄入、Hybrid Search |
| **模型后训练** | SFT 微调、DPO/RLHF 偏好对齐、RAFT 检索增强微调 |
| **ML 基础设施** | 训练数据飞轮、评估框架、A/B 测试、模型版本管理 |
| **系统设计** | 双引擎路由、反馈闭环、流式输出、多租户隔离 |
| **全栈能力** | FastAPI + Vue 3 + PostgreSQL + Redis + Docker |

同一个项目同时覆盖 **RAG 工程** 和 **模型微调**，这在简历中非常稀缺。

---

## 一、双引擎架构总览

```
                          ┌──────────────────┐
                          │   用户提问         │
                          └────────┬─────────┘
                                   │
                          ┌────────▼─────────┐
                          │   Router Agent    │  ← LangGraph 路由
                          │  (判断走哪条路径)  │
                          └───┬──────────┬───┘
                              │          │
              ┌───────────────▼──┐   ┌──▼────────────────┐
              │  RAG 引擎        │   │  Fine-tuned 引擎   │
              │  (高频/边缘问题)  │   │  (高频/领域问题)    │
              └───────┬──────────┘   └──┬────────────────┘
                      │                 │
                      │    ┌────────────▼────────────┐
                      │    │  Evaluation Gate        │  ← 质量兜底
                      │    │  (置信度 + 事实性校验)   │
                      │    └────────────┬────────────┘
                      │                 │
              ┌───────▼─────────────────▼──────┐
              │         结构化回答               │
              │  (答案 + 来源引用 + 置信度)      │
              └────────────────┬───────────────┘
                               │
              ┌────────────────▼───────────────┐
              │       用户反馈 (👍/👎)          │
              └────────────────┬───────────────┘
                               │
              ┌────────────────▼───────────────┐
              │      训练数据飞轮               │
              │  反馈 → 筛选 → 重标注 → 微调    │
              └────────────────────────────────┘
```

### RAG 引擎（高频+边缘问题）

- 处理需要引用原始文档、时效性要求高的问题
- Hybrid Search（BM25 + Vector）+ Reranker
- 结构化引用（答案中标注来源文档和段落）

### Fine-tuned 引擎（高频+领域问题）

- 处理频繁出现的领域通用问题（无需每次都检索）
- 基于 RAG 历史数据 + 人工标注进行 SFT 微调
- 通过用户反馈进行 DPO/RLHF 偏好对齐

### Router Agent（LangGraph 实现）

- 分析问题类型，决定走 RAG / Fine-tuned / 两者混合
- 判断依据：问题是否在 FAQ 范围内、是否需要引用文档、置信度预估

---

## 二、技术模块拆解

### 模块 1：多源数据摄入管道（Ingestion Pipeline）

```
Confluence 页面 ─┐
Git 仓库文档 ────┼──→ Document Loader → Chunking → Embedding → PGVector
PDF 手册 ────────┤                                         ↓
Slack 精华消息 ──┘                                  知识库索引
```

**技术选型**：

| 环节 | 方案 | 理由 |
|------|------|------|
| 文档解析 | Unstructured.io / LlamaParse | 支持 PDF/Word/HTML/Markdown |
| 文本分块 | RecursiveCharacterTextSplitter + Semantic Chunking | 保证语义完整性 |
| Embedding | BGE-M3 / text2vec-large-chinese | 中文效果更好，支持多语言 |
| 向量库 | PostgreSQL + pgvector（已有） | 生产可用，与 Memory 共用 |

### 模块 2：混合检索 + 重排序（Hybrid Search + Reranker）

```
query → BM25 关键词检索 ─┐
                          ├→ RRF 融合 → BGE-Reranker 重排序 → Top-K
query → 向量语义检索 ─────┘
```

**与当前项目的差异**：当前只有 `similarity_search`（纯语义），增加 BM25 提升精确匹配（如错误码、API 名称），Reranker 提升 Top-K 质量。

### 模块 3：Router Agent（LangGraph 新增节点）

```python
# 新增 LangGraph 节点
workflow.add_node("router", router_node)
workflow.add_node("rag_engine", rag_node)
workflow.add_node("finetuned_engine", finetuned_node)

# 路由逻辑
def router_node(state):
    """判断走 RAG 还是 Fine-tuned 引擎"""
    question = state["messages"][-1].content

    # 规则 1：FAQ 命中 → Fine-tuned
    if is_faq_match(question):
        return {"engine": "finetuned"}

    # 规则 2：需要引用文档 → RAG
    if needs_citation(question):
        return {"engine": "rag"}

    # 规则 3：LLM 判断
    decision = router_llm.invoke(f"这个问题需要检索文档吗？{question}")
    return {"engine": decision}
```

### 模块 4：Fine-tuning 训练管道

**4.1 训练数据构建**

```
RAG 历史数据
    │
    ├→ 高频问题 → 人工筛选/修正 → SFT 训练集
    │
    └→ 用户反馈 (👍/👎) → DPO 偏好对 → DPO 训练集
```

**4.2 微调策略**

| 阶段 | 方法 | 数据来源 | 目标 |
|------|------|----------|------|
| SFT | 监督微调 | RAG 高频问题 + 人工标注答案 | 让模型学会领域知识 |
| DPO | 直接偏好优化 | 👍 答案 vs 👎 答案 | 对齐用户偏好 |
| RAFT | 检索增强微调 | (文档, 问题, 答案) 三元组 | 让模型更好地利用检索上下文 |

**4.3 RAFT（Retrieval Augmented Fine-Tuning）详解**

这是方案中最体现技术深度的部分。传统微调让模型背答案，RAFT 让模型学会"如何使用检索到的文档"：

```
传统 RAG:
  query → retrieve docs → LLM reads docs → generate answer

RAFT 训练:
  训练样本: (query, [golden_doc, distractor_docs], golden_answer)
  训练目标: 让模型学会区分相关/不相关文档，
            基于相关文档生成准确答案，
            忽略干扰文档
```

**实现路径**：

```python
# RAFT 训练样本构造
def build_raft_sample(query, golden_doc, distractor_docs, answer):
    """构造 RAFT 训练样本"""
    # 混合 golden doc 和 distractor docs
    docs = [golden_doc] + random.sample(distractor_docs, k=4)
    random.shuffle(docs)

    context = "\n\n".join(d.page_content for d in docs)

    # 训练格式：模型需要学会从混合文档中提取正确答案
    prompt = f"""基于以下文档回答问题。注意：有些文档可能不相关。

文档：
{context}

问题：{query}

答案："""

    return {"prompt": prompt, "completion": answer}
```

### 模块 5：评估框架

```python
class EvaluationSuite:
    """模型质量评估套件"""

    def evaluate(self, model, test_set):
        """多维度评估"""
        return {
            "answer_accuracy": self.factual_accuracy(model, test_set),
            "citation_correctness": self.citation_score(model, test_set),
            "hallucination_rate": self.hallucination_check(model, test_set),
            "response_latency": self.latency_benchmark(model),
            "user_satisfaction": self.feedback_score(model),
        }

    def a_b_test(self, model_a, model_b, test_set):
        """A/B 对比测试 — 用于微调前后对比"""
        pass
```

### 模块 6：管理后台

```
┌──────────────────────────────────────────────────────┐
│  📊 知识库问答系统管理后台                              │
│                                                        │
│  ┌──────────┬──────────┬──────────┬──────────┐        │
│  │ 今日问答  │ 准确率    │ 活跃用户  │ 知识库文档 │        │
│  │  1,234   │  94.2%   │   89     │  5,230   │        │
│  └──────────┴──────────┴──────────┴──────────┘        │
│                                                        │
│  ┌─ 问答质量监控 ──────────────────────────────┐      │
│  │  [低分回答列表]  [用户反馈统计]  [趋势图]    │      │
│  └──────────────────────────────────────────────┘      │
│                                                        │
│  ┌─ 模型管理 ──────────────────────────────────┐      │
│  │  当前版本: v2.3  |  SFT 训练中...   |  [触发训练] │      │
│  │  [模型版本历史]  [A/B 测试配置]  [部署切换] │      │
│  └──────────────────────────────────────────────┘      │
│                                                        │
│  ┌─ 知识库管理 ────────────────────────────────┐      │
│  │  [文档上传]  [同步 Confluence]  [索引状态]   │      │
│  └──────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────┘
```

---

## 三、新增项目结构

```
AI Research Agent/
├── src/                            # 现有后端（保留）
│   ├── ...
│   ├── tools.py                    # 扩展工具：feedback_collector, faq_search
│   ├── router.py                   # [新增] Router Agent
│   └── evaluation.py               # [新增] 评估框架
├── ingestion/                      # [新增] 数据摄入管道
│   ├── loaders/
│   │   ├── confluence.py           # Confluence 文档加载
│   │   ├── git_repo.py             # Git 仓库文档加载
│   │   └── pdf_parser.py           # PDF 解析
│   ├── chunker.py                  # 智能分块
│   ├── embedder.py                 # BGE-M3 Embedding
│   └── pipeline.py                 # 摄入管道编排
├── training/                       # [新增] 模型微调管道
│   ├── data_collector.py           # 训练数据采集
│   ├── sft_trainer.py              # SFT 微调
│   ├── dpo_trainer.py              # DPO 偏好对齐
│   ├── raft_trainer.py             # RAFT 检索增强微调
│   └── evaluator.py                # 模型评估
├── admin/                          # [新增] 管理后台前端
│   └── src/
│       ├── Dashboard.vue           # 数据大盘
│       ├── ModelManager.vue        # 模型管理
│       ├── KnowledgeManager.vue    # 知识库管理
│       └── FeedbackReview.vue      # 反馈审核
├── app.py                          # FastAPI（扩展新端点）
├── frontend/                       # 现有用户端（保留，增强）
└── docs/
    ├── ENTERPRISE_ROADMAP.md        # 本文档
    └── TRAINING_GUIDE.md            # [新增] 训练指南
```

---

## 四、新增 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/chat` | POST | 现有，增强为双引擎路由 |
| `/feedback` | POST | 用户反馈收集（👍/👎 + 评语） |
| `/admin/stats` | GET | 问答统计数据 |
| `/admin/models` | GET | 模型版本列表 |
| `/admin/models/train` | POST | 触发微调训练 |
| `/admin/models/deploy` | POST | 切换生产模型 |
| `/admin/knowledge/upload` | POST | 上传文档到知识库 |
| `/admin/knowledge/sync` | POST | 从外部源同步 |
| `/admin/eval/run` | POST | 执行评估任务 |

---

## 五、分阶段实施计划

### 第一阶段：RAG 增强（2-3 周）

基于现有代码扩展，不动架构：

- [ ] 多源文档摄入管道（Confluence + Git + PDF）
- [ ] Hybrid Search（BM25 + Vector 融合）
- [ ] BGE-Reranker 重排序
- [ ] 结构化输出（答案 + 来源引用）
- [ ] 用户反馈收集端点（👍/👎）

### 第二阶段：双引擎 + Router（2-3 周）

- [ ] Router Agent（LangGraph 新增节点）
- [ ] FAQ 知识库与快速匹配
- [ ] 评测框架搭建（准确率、事实性、延时）
- [ ] 管理后台基本功能
- [ ] 流式输出（SSE → 前端实时渲染）

### 第三阶段：微调管道（3-4 周）

- [ ] SFT 训练数据采集与清洗
- [ ] SFT 微调（基于 Qwen2.5-7B / Llama-3-8B）
- [ ] DPO 偏好对齐（基于用户反馈）
- [ ] RAFT 检索增强微调
- [ ] A/B 测试环境搭建
- [ ] 模型版本管理与部署切换

### 第四阶段：完善与打磨（2 周）

- [ ] 管理后台功能完善
- [ ] 监控告警接入
- [ ] 性能优化
- [ ] 文档与演示材料

---

## 六、技术选型细节

### 微调基座模型选择

| 模型 | 参数量 | 优势 | GPU 需求 |
|------|--------|------|----------|
| Qwen2.5-7B-Instruct | 7B | 中文能力强，指令遵循好 | 1×A100 (SFT) |
| Llama-3.1-8B-Instruct | 8B | 生态丰富，工具链成熟 | 1×A100 |
| DeepSeek-V3-Lite | 16B (MoE) | 推理能力强 | 2×A100 |

推荐 Qwen2.5-7B：中文场景最优，单卡可训练。

### 微调框架选择

| 框架 | 优势 |
|------|------|
| **LLaMA-Factory** | 可视化、支持 Qwen/Llama、SFT+DPO+RM 一站式 |
| Axolotl | 社区活跃、配置灵活 |
| Unsloth | 训练速度快 2-5x，显存占用低 |

推荐 LLaMA-Factory：上手快，功能全，与项目解耦。

### GPU 资源方案

| 方案 | 适用场景 | 成本 |
|------|----------|------|
| AutoDL 按量租用 | 训练时使用 | 约 ¥5-10/小时 (A100) |
| HuggingFace Spaces | 托管推理 | 免费额度 |
| 本地 RTX 4090 | SFT 小模型 | 可训练 7B-LoRA |

---

## 七、为什么这个方案能体现技术深度

### 1. RAFT 微调（2024 年顶会论文技术）

不是简单的"跑个微调脚本"，而是训练模型**学会如何利用检索结果**。这需要理解 RAG 的痛点（模型忽略检索文档、被干扰文档误导），并通过训练数据构造解决。

### 2. Router Agent 的决策逻辑

不是 if-else，而是 LangGraph Agent 的多路径路由。Router 需要平衡：
- RAG 路径的准确性（有引用）vs 延迟（检索耗时）
- Fine-tuned 路径的速度（直接生成）vs 幻觉风险（无引用）

可以写成一个带评估反馈的自适应路由。

### 3. 训练数据飞轮设计

```
用户使用 → 反馈收集 → 数据清洗 → 微调训练 → 模型部署 → 用户使用
    ↑                                                      ↓
    └──────────────── A/B 测试验证 ─────────────────────────┘
```

这个闭环本身就是 ML 工程师的核心能力体现。

### 4. 从 Demo 到生产的工程化细节

- 模型版本管理（不是覆盖式更新，而是可回滚的版本历史）
- A/B 测试框架（微调前后的定量对比）
- 评估体系（不仅要"好看"，还要"准确"）

---

## 八、面试中的话术参考

**面试官问"你做过什么有挑战的项目？"**

> 我做了一个企业知识库智能问答系统。技术栈是 LangGraph + RAG + 模型微调。
>
> 比较有挑战的是双引擎架构的设计——不是简单的 RAG 或者微调，而是让 Router Agent 实时判断每个问题应该走 RAG 检索还是微调后的模型直接回答。
>
> 我做了三件事来提升效果：第一，Hybrid Search + Reranker 提升检索质量；第二，用 RAFT 微调让模型学会利用检索文档而非忽略它；第三，搭建了用户反馈的数据飞轮，通过 DPO 持续对齐用户偏好。
>
> 最终准确率从初版的 78% 提升到 94%，同时 P95 延时控制在 2 秒以内。

---

## 九、风险与应对

| 风险 | 应对方案 |
|------|----------|
| 微调后模型退化（Catastrophic Forgetting） | 保留通用能力测试集，SFT 数据中混合 10% 通用数据 |
| RAG + Fine-tuned 答案矛盾 | Router 同一问题只走一条路径；关键场景走 RAG |
| 训练数据质量差 | 人工审核环节 + 自动化质量过滤（长度、格式、事实性） |
| GPU 资源不足 | LoRA 微调（仅训练 1-2% 参数），单卡 4090 可行 |
| 冷启动无反馈数据 | 先用 RAG 积累数据，合成一批初始训练样本 |
