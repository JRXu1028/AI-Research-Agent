# RAG 系统实现详解

## 概述

RAG（Retrieval-Augmented Generation，检索增强生成）是一种结合了信息检索和文本生成的 AI 技术。本项目实现了双向量数据库后端的 RAG 系统，支持 Chroma（本地开发）和 PostgreSQL + pgvector（生产环境）两种后端，通过环境变量一键切换。

---

## 一、架构总览

### 模块组成

```
src/
├── embeddings.py       # Embedding 模型管理
├── vector_store.py     # Chroma 向量数据库（本地开发）
├── vector_store_pg.py  # PostgreSQL + pgvector 向量数据库（生产环境）
├── knowledge_base.py   # 知识库数据定义
└── rag.py             # RAG 系统核心逻辑（自动选择后端）
```

### 双后端设计

通过 `VECTOR_STORE_TYPE` 环境变量控制：

```
VECTOR_STORE_TYPE=chroma    → VectorStore (Chroma, 文件持久化)
VECTOR_STORE_TYPE=postgres  → VectorStorePG (PostgreSQL + pgvector)
```

`rag.py` 中的 `initialize_rag_system()` 根据配置自动选择后端，上层代码无需感知差异。

---

## 二、详细改动说明

### 改动 1：添加依赖包（requirements.txt）

**新增依赖**：
```txt
langchain-community>=0.0.20    # LangChain 社区组件（包含 Chroma）
chromadb>=0.4.0                # 向量数据库
sentence-transformers>=2.2.0   # Embedding 模型
```

**为什么需要这些包**：
- `langchain-community`: 提供 Chroma 向量数据库的集成
- `chromadb`: 开源向量数据库，用于存储和检索文档向量
- `sentence-transformers`: 提供文本向量化模型

---

### 改动 2：创建 Embedding 模块（src/embeddings.py）

**作用**：将文本转换为向量（数字表示）

```python
from langchain_community.embeddings import HuggingFaceEmbeddings

def create_embeddings():
    """创建 Embedding 模型"""
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",  # 轻量级模型
        model_kwargs={'device': 'cpu'},                        # 使用 CPU
        encode_kwargs={'normalize_embeddings': True}           # 归一化向量
    )
    return embeddings
```

**核心概念**：
- **Embedding**: 将文本转换为固定长度的向量（如 384 维）
- **相似度**: 向量之间的距离可以表示文本的语义相似度
- **模型选择**: `all-MiniLM-L6-v2` 是一个平衡了速度和效果的模型

**工作流程**：
```
文本 "华东师范大学" 
    ↓ [Embedding 模型]
向量 [0.23, -0.45, 0.67, ..., 0.12]  (384维)
```

---

### 改动 3：创建知识库（src/knowledge_base.py）

**作用**：定义和管理知识库数据

```python
KNOWLEDGE_BASE = [
    {
        "id": "doc1",
        "content": "华东师范大学创建于1951年...",
        "metadata": {"source": "学校简介", "category": "基本信息"}
    },
    # ... 更多文档
]

def get_knowledge_base():
    """获取知识库数据"""
    return KNOWLEDGE_BASE
```

**数据结构**：
- `id`: 文档唯一标识
- `content`: 文档内容（会被向量化）
- `metadata`: 元数据（来源、分类等）

**扩展方式**：
```python
# 方式1：直接添加到列表
KNOWLEDGE_BASE.append({
    "id": "doc9",
    "content": "新的知识内容...",
    "metadata": {"source": "来源", "category": "分类"}
})

# 方式2：从文件加载
def load_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        KNOWLEDGE_BASE.extend(data)
```

---

### 改动 4：创建向量数据库（src/vector_store.py）

**作用**：管理文档向量的存储和检索

```python
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

class VectorStore:
    def __init__(self, persist_directory="./data/chroma_db"):
        self.persist_directory = persist_directory
        self.embeddings = create_embeddings()
        self.vectorstore = None
    
    def initialize(self, force_reload=False):
        """初始化或加载向量数据库"""
        if os.path.exists(self.persist_directory) and not force_reload:
            # 加载已有数据库
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        else:
            # 创建新数据库
            knowledge_base = get_knowledge_base()
            documents = [
                Document(
                    page_content=doc["content"],
                    metadata=doc["metadata"]
                )
                for doc in knowledge_base
            ]
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
    
    def search_with_score(self, query: str, k: int = 3):
        """检索相关文档（带相似度分数）"""
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        return results
```

**核心流程**：

1. **初始化阶段**：
```
知识库文档
    ↓ [转换为 Document 对象]
LangChain Documents
    ↓ [Embedding 模型向量化]
文档向量
    ↓ [存储到 Chroma]
向量数据库（持久化到磁盘）
```

2. **检索阶段**：
```
用户查询 "华东师范大学在哪里？"
    ↓ [Embedding 模型向量化]
查询向量
    ↓ [计算相似度]
找到最相似的 k 个文档
    ↓ [返回文档 + 相似度分数]
[(doc1, 0.85), (doc2, 0.72), (doc3, 0.68)]
```

**相似度计算**：
- 使用余弦相似度（Cosine Similarity）
- 分数越高表示越相似（0-1之间）
- 通常 > 0.7 表示高度相关

---

### 改动 5：PostgreSQL + pgvector 后端（src/vector_store_pg.py）

**作用**：生产级向量数据库，替代 Chroma

```python
class VectorStorePG:
    def __init__(self):
        self.embeddings = create_embeddings()
        self.connection_string = Config.get_postgres_connection_string()
        self.collection_name = "knowledge_base"

    def initialize(self, force_reload=False):
        self.vectorstore = PGVector(
            embeddings=self.embeddings,
            collection_name=self.collection_name,
            connection=self.connection_string,
            use_jsonb=True,
        )
        # 自动检测并初始化数据

    def search_with_score(self, query: str, k: int = 3):
        return self.vectorstore.similarity_search_with_score(query, k=k)
```

**与 Chroma 版的区别**：

| 特性 | Chroma | PostgreSQL + pgvector |
|------|--------|----------------------|
| 部署方式 | 内嵌，文件存储 | 独立数据库服务 |
| 并发能力 | 单进程 | 多连接并发 |
| 备份恢复 | 手动复制目录 | 标准 pg_dump/pg_restore |
| 适用场景 | 本地开发、原型 | 生产环境、多副本 |

### 改动 6：创建 RAG 系统（src/rag.py）

**作用**：封装 RAG 系统的核心逻辑，自动选择向量数据库后端

```python
class RAGSystem:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def retrieve(self, query: str, k: int = 3):
        return self.vector_store.search_with_score(query, k=k)

def initialize_rag_system(force_reload=False):
    """根据 VECTOR_STORE_TYPE 自动选择后端"""
    global _rag_system_instance
    if _rag_system_instance is None or force_reload:
        vector_store_type = Config.VECTOR_STORE_TYPE
        if vector_store_type == "postgres":
            from .vector_store_pg import create_vector_store
        else:
            from .vector_store import create_vector_store
        vector_store = create_vector_store(force_reload=force_reload)
        _rag_system_instance = RAGSystem(vector_store)
    return _rag_system_instance
```

**设计模式**：
- **单例模式**: 全局只有一个 RAG 系统实例
- **策略模式**: 通过配置切换向量数据库后端
- **延迟初始化**: 只在需要时才初始化

---

### 改动 7：添加知识检索工具（src/tools.py）

**新增工具**：

```python
@tool
def knowledge_search(query: str) -> str:
    """
    从知识库中搜索相关信息
    
    当用户询问关于华东师范大学、Python、LangChain、RAG等
    知识库中的内容时使用此工具。
    
    Args:
        query: 搜索查询
    
    Returns:
        相关的知识库内容
    """
    from .rag import get_rag_system
    
    # 获取 RAG 系统实例
    rag_system = get_rag_system()
    
    if rag_system is None:
        return "知识库未初始化，无法搜索"
    
    # 检索相关文档
    results = rag_system.retrieve(query, k=3)
    
    if not results:
        return "未找到相关信息"
    
    # 格式化返回结果
    context = "\n\n".join([
        f"【文档{i+1}】(相似度: {score:.4f})\n{doc.page_content}"
        for i, (doc, score) in enumerate(results)
    ])
    
    return context
```

**工作流程**：
```
1. Agent 判断需要知识库信息
2. 调用 knowledge_search 工具
3. 工具从向量数据库检索相关文档
4. 返回格式化的文档内容
5. Agent 基于检索结果生成答案
```

**修改工具列表**：
```python
def get_all_tools():
    return [calculator, knowledge_search]  # 添加新工具
```

---

### 改动 8：集成到主程序

**新增初始化步骤**：

```python
# 2. 初始化 RAG 系统（知识库）
print("\n[2/5] 初始化 RAG 系统...")
initialize_rag_system(force_reload=False)
```

**新增测试用例**：
```python
test_cases = [
    "请帮我计算 25 加 17 等于多少？",        # 测试 calculator 工具
    "华东师范大学在哪里？有几个校区？",      # 测试 knowledge_search 工具
    "华东师范大学的校训是什么？",           # 测试 knowledge_search 工具
    "123 + 456 = ?",                        # 测试 calculator 工具
    "什么是 RAG 技术？",                    # 测试 knowledge_search 工具
]
```

---

## 三、RAG 工作流程详解

### 完整流程图

```
用户提问: "华东师范大学在哪里？"
    ↓
Agent 分析问题
    ↓
判断: 需要知识库信息
    ↓
调用 knowledge_search 工具
    ↓
工具执行:
    1. 将查询向量化
    2. 在向量数据库中搜索
    3. 找到最相似的 3 个文档
    4. 返回文档内容
    ↓
Agent 收到检索结果:
    【文档1】(相似度: 0.85)
    华东师范大学有两个校区：闵行校区和中山北路校区...
    
    【文档2】(相似度: 0.72)
    华东师范大学创建于1951年...
    
    【文档3】(相似度: 0.68)
    华东师范大学设有教育学部...
    ↓
Agent 基于检索结果生成答案:
    "华东师范大学有两个校区：
     1. 闵行校区：位于上海市闵行区东川路500号
     2. 中山北路校区：位于上海市普陀区中山北路3663号"
    ↓
返回给用户
```

### 关键技术点

#### 1. 向量化（Embedding）

**原理**：
```python
# 文本 → 向量
text = "华东师范大学"
vector = embedding_model.encode(text)
# vector = [0.23, -0.45, 0.67, ..., 0.12]  # 384维
```

**为什么需要向量化**：
- 计算机无法直接理解文本
- 向量可以进行数学运算（计算相似度）
- 语义相似的文本，向量也相似

#### 2. 相似度搜索

**余弦相似度公式**：
```
similarity = (A · B) / (||A|| × ||B||)

其中：
- A, B 是两个向量
- A · B 是点积
- ||A||, ||B|| 是向量的模（长度）
```

**示例**：
```python
query_vector = [0.5, 0.3, 0.8]
doc1_vector = [0.6, 0.2, 0.7]  # 相似度: 0.95 (高)
doc2_vector = [-0.3, 0.9, 0.1] # 相似度: 0.42 (低)
```

#### 3. Top-K 检索

**原理**：
- 计算查询向量与所有文档向量的相似度
- 按相似度排序
- 返回前 K 个最相似的文档

**参数选择**：
- K=3: 平衡精度和上下文长度
- K 太小: 可能遗漏重要信息
- K 太大: 引入噪音，增加 token 消耗

---

## 四、核心概念解释

### 1. RAG vs 传统问答

**传统问答**：
```
用户问题 → LLM → 答案
```
- 依赖模型训练数据
- 无法回答训练后的新知识
- 可能产生幻觉（编造答案）

**RAG 问答**：
```
用户问题 → 检索知识库 → 相关文档 + 问题 → LLM → 答案
```
- 基于实际文档回答
- 可以实时更新知识库
- 答案有据可查

### 2. 向量数据库 vs 传统数据库

**传统数据库（如 MySQL）**：
```sql
SELECT * FROM docs WHERE content LIKE '%华东师范大学%';
```
- 精确匹配
- 无法理解语义
- "华东师大" 和 "华东师范大学" 无法匹配

**向量数据库（如 Chroma）**：
```python
vectorstore.similarity_search("华东师范大学")
```
- 语义搜索
- "华东师大"、"ECNU"、"华师大" 都能匹配
- 理解同义词和相关概念

### 3. Embedding 模型选择

**常用模型对比**：

| 模型 | 维度 | 大小 | 速度 | 效果 | 适用场景 |
|------|------|------|------|------|----------|
| all-MiniLM-L6-v2 | 384 | 90MB | 快 | 中 | 通用、快速原型 |
| all-mpnet-base-v2 | 768 | 420MB | 中 | 好 | 生产环境 |
| text-embedding-ada-002 | 1536 | API | 慢 | 优 | 高精度需求 |

**本项目选择**：
- `all-MiniLM-L6-v2`
- 原因：轻量、快速、效果够用

---

## 五、扩展和优化

### 1. 添加更多文档

**方式1：直接添加**
```python
# src/knowledge_base.py
KNOWLEDGE_BASE.append({
    "id": "doc9",
    "content": "新的知识内容...",
    "metadata": {"source": "来源", "category": "分类"}
})
```

**方式2：从文件加载**
```python
import json

def load_from_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data

# 使用
new_docs = load_from_json('data/new_knowledge.json')
KNOWLEDGE_BASE.extend(new_docs)
```

**方式3：从网页爬取**
```python
from langchain_community.document_loaders import WebBaseLoader

loader = WebBaseLoader("https://example.com")
docs = loader.load()
```

### 2. 优化检索质量

**方法1：调整 K 值**
```python
# 返回更多文档
results = rag_system.retrieve(query, k=5)
```

**方法2：过滤低分文档**
```python
# 只保留相似度 > 0.7 的文档
filtered_results = [
    (doc, score) for doc, score in results 
    if score > 0.7
]
```

**方法3：重排序（Reranking）**
```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

# 使用 LLM 重新排序检索结果
compressor = LLMChainExtractor.from_llm(llm)
compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=vectorstore.as_retriever()
)
```

### 3. 混合检索

**结合关键词和语义搜索**：
```python
from langchain.retrievers import BM25Retriever, EnsembleRetriever

# BM25 关键词检索
bm25_retriever = BM25Retriever.from_documents(documents)

# 向量语义检索
vector_retriever = vectorstore.as_retriever()

# 混合检索
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.5, 0.5]  # 各占 50%
)
```

### 4. 添加文档分块

**为什么需要分块**：
- 长文档难以检索
- 减少无关信息
- 提高检索精度

**实现方式**：
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,        # 每块 500 字符
    chunk_overlap=50,      # 重叠 50 字符
    length_function=len,
)

# 分块
chunks = text_splitter.split_documents(documents)
```

---

## 六、常见问题

### Q1: 向量数据库存储在哪里？
A: `./data/chroma_db` 目录，包含：
- 文档向量
- 元数据
- 索引文件

### Q2: 如何更新知识库？
A: 
1. 修改 `src/knowledge_base.py`
2. 删除 `./data/chroma_db` 目录
3. 重新运行程序（会自动重建）

或者：
```python
initialize_rag_system(force_reload=True)
```

### Q3: Embedding 模型存储在哪里？
A: 
- Windows: `C:\Users\用户名\.cache\huggingface\hub`
- Linux/Mac: `~/.cache/huggingface/hub`

### Q4: 如何使用其他 Embedding 模型？
A: 修改 `src/embeddings.py`:
```python
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # 中文效果更好
    # ...
)
```

### Q5: 如何使用 OpenAI 的 Embedding？
A: 
```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-ada-002",
    openai_api_key="your-api-key"
)
```

---

## 七、学习资源

### 推荐阅读

1. **RAG 论文**：
   - "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
   - https://arxiv.org/abs/2005.11401

2. **LangChain 文档**：
   - https://python.langchain.com/docs/modules/data_connection/

3. **Chroma 文档**：
   - https://docs.trychroma.com/

4. **Sentence Transformers**：
   - https://www.sbert.net/

### 实践项目

1. **文档问答系统**：基于公司文档的问答
2. **代码助手**：基于代码库的编程助手
3. **客服机器人**：基于FAQ的自动客服

---

## 八、总结

### 核心改动

1. ✅ 添加 4 个新模块（embeddings, vector_store, knowledge_base, rag）
2. ✅ 扩展工具系统（添加 knowledge_search）
3. ✅ 集成到主程序（初始化和测试）

### 技术栈

- **Embedding**: sentence-transformers
- **向量数据库**: Chroma
- **框架**: LangChain
- **模式**: 工具调用 + RAG

### 优势

- ✅ 基于真实文档回答
- ✅ 可实时更新知识库
- ✅ 答案有据可查
- ✅ 减少模型幻觉

### 下一步

- 添加更多文档源
- 优化检索质量
- 实现文档分块
- 添加混合检索
- 集成到生产环境

---

**恭喜你完成了 RAG 系统的学习！** 🎉

现在你已经掌握了：
- RAG 的核心原理
- 向量数据库的使用
- Embedding 模型的应用
- 如何集成到 Agent 系统

继续探索和实践吧！
