# Memory 功能实现详解

## 概述

本文档说明 LangGraph Agent 的 Memory 系统架构，包含三级存储后端：内存（开发）、PostgreSQL（持久化）、PostgreSQL + Redis（Hybrid，生产推荐）。核心模块 `src/memory.py` 封装了后端选择逻辑，通过 `MEMORY_STORE_TYPE` 环境变量一键切换。

---

## 一、架构总览

### 模块组成

```
src/
├── memory.py              # Memory 后端工厂（核心新增）
│   └── create_checkpointer() → MemorySaver / PostgresSaver / Hybrid
├── langgraph_agent.py     # LangGraph Agent（接受外部 checkpointer）
│   ├── create_langgraph_agent(llm, tools_map, checkpointer=None)
│   └── run_langgraph_agent_with_memory(state, llm, tools_map, thread_id, checkpointer)
└── config.py              # 配置管理（MEMORY_STORE_TYPE + Redis + PostgreSQL）
```

### 三级存储后端

| 模式 | 后端 | 持久化 | 适用场景 |
|------|------|--------|----------|
| `memory` | MemorySaver（内存） | ❌ 重启丢失 | 本地开发、调试 |
| `postgres` | PostgresSaver | ✅ | 单机生产部署 |
| `hybrid` | PostgresSaver + Redis 缓存 | ✅ | 生产推荐（最佳性能） |

通过 `.env` 配置切换：

```bash
MEMORY_STORE_TYPE=memory      # 本地开发
MEMORY_STORE_TYPE=postgres    # 持久化
MEMORY_STORE_TYPE=hybrid      # 生产推荐
```

---

## 二、核心实现

### 改动 1：Memory 后端工厂（src/memory.py）

`create_checkpointer()` 根据配置创建对应的 Checkpointer：

```python
async def create_checkpointer():
    store_type = Config.MEMORY_STORE_TYPE

    if store_type == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()

    elif store_type == "postgres":
        from langgraph_checkpoint_postgres import PostgresSaver
        checkpointer = PostgresSaver.from_conn_string(conn_string)
        await checkpointer.setup()
        return checkpointer

    elif store_type == "hybrid":
        # PostgreSQL 持久化 + Redis 缓存加速
        checkpointer = PostgresSaver.from_conn_string(conn_string)
        await checkpointer.setup()
        redis_client = redis.from_url(redis_url)
        checkpointer.redis_client = redis_client
        return checkpointer
```

### 改动 2：LangGraph Agent 支持 Checkpointer 注入（src/langgraph_agent.py）

使用 `checkpointer` 参数替代旧的 `with_memory` 布尔值：

```python
def create_langgraph_agent(llm, tools_map, checkpointer=None):
    """创建 LangGraph Agent，支持外部注入 Checkpointer"""
    workflow = StateGraph(AgentState)
    # ... 添加节点和边 ...

    if checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
    else:
        app = workflow.compile()
    return app
```

**关键改进**：
- 从布尔参数改为接受 Checkpointer 实例，支持任意后端
- 与 `src/memory.py` 解耦，Checkpointer 由调用方创建

#### `run_langgraph_agent_with_memory` 函数

```python
def run_langgraph_agent_with_memory(state, llm, tools_map, thread_id, checkpointer=None):
    if checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()

    agent = create_langgraph_agent(llm, tools_map, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    final_state = agent.invoke(state, config)
    return final_state
```

- `thread_id`：对话线程 ID，区分不同会话
- 未提供 checkpointer 时自动降级为 MemorySaver

---

## 三、Memory 工作原理

### 1. Checkpointer 机制

**什么是 Checkpointer？**
- Checkpointer 是 LangGraph 的状态持久化机制
- 在每个节点执行后自动保存状态
- 在下次调用时自动加载历史状态

**工作流程**：
```
第 1 轮对话：
  用户输入 → Agent 处理 → 保存状态（checkpoint_1）

第 2 轮对话：
  加载状态（checkpoint_1） → 用户输入 → Agent 处理 → 保存状态（checkpoint_2）

第 3 轮对话：
  加载状态（checkpoint_2） → 用户输入 → Agent 处理 → 保存状态（checkpoint_3）
```

### 2. Thread ID 的作用

**Thread ID 是什么？**
- 对话线程的唯一标识符
- 用于区分不同的对话会话
- 相同 thread_id 的调用共享历史

**示例**：
```python
# 对话 A（thread_id="user_001"）
run_langgraph_agent_with_memory(state1, llm, tools_map, "user_001")
run_langgraph_agent_with_memory(state2, llm, tools_map, "user_001")  # 能看到 state1 的历史

# 对话 B（thread_id="user_002"）
run_langgraph_agent_with_memory(state3, llm, tools_map, "user_002")  # 看不到 user_001 的历史
```

### 3. Checkpointer 对比

| Checkpointer | 存储位置 | 持久化 | 适用场景 |
|--------------|---------|--------|---------|
| MemorySaver | 内存 | ❌ 否 | 开发、测试、短期会话 |
| PostgresSaver | PostgreSQL | ✅ 是 | 单机生产、长期会话 |
| PostgresSaver + Redis | PostgreSQL + Redis | ✅ 是 | 分布式、高并发（Hybrid） |

**MemorySaver**：
- ✅ 零配置、高性能
- ❌ 重启丢失、不共享

**PostgresSaver**：
- ✅ 持久化、多进程共享
- ❌ 每次读写需数据库查询

**Hybrid（PostgreSQL + Redis）**：
- ✅ 热数据从 Redis 读取，冷数据写 PostgreSQL
- ✅ 兼顾性能与持久化
- ❌ 需要维护 Redis 集群

---

## 四、使用示例

### 示例 1：基本多轮对话

```python
from src.langgraph_agent import run_langgraph_agent_with_memory

# 初始化
llm = create_llm()
tools_map = create_tools_map(get_all_tools())
thread_id = "conversation_001"

# 第 1 轮
state1 = create_initial_state("请帮我计算 25 加 17")
result1 = run_langgraph_agent_with_memory(state1, llm, tools_map, thread_id)
# Agent: 25 + 17 = 42

# 第 2 轮（引用上一轮结果）
state2 = create_initial_state("再加上 10 呢？")
result2 = run_langgraph_agent_with_memory(state2, llm, tools_map, thread_id)
# Agent: 42 + 10 = 52（Agent 记得上一轮的 42）
```

### 示例 2：多个独立对话

```python
# 对话 A
thread_a = "user_alice"
state_a1 = create_initial_state("华东师范大学在哪里？")
result_a1 = run_langgraph_agent_with_memory(state_a1, llm, tools_map, thread_a)

state_a2 = create_initial_state("它有几个校区？")
result_a2 = run_langgraph_agent_with_memory(state_a2, llm, tools_map, thread_a)
# Agent 知道"它"指的是华东师范大学

# 对话 B（独立的会话）
thread_b = "user_bob"
state_b1 = create_initial_state("它有几个校区？")
result_b1 = run_langgraph_agent_with_memory(state_b1, llm, tools_map, thread_b)
# Agent 不知道"它"指什么（因为是新会话）
```

### 示例 3：清空历史（开始新对话）

```python
import time

# 方法 1：更换 thread_id
old_thread = "conversation_001"
new_thread = f"conversation_{int(time.time())}"  # 使用时间戳生成新 ID

# 方法 2：使用新的 Agent 实例
# 重新调用 create_langgraph_agent 会创建新的 Memory
```

---

## 五、运行演示程序

### 1. 多轮对话演示

```bash
python main_langgraph_memory.py
```

**演示内容**：
1. 第 1 轮：计算 25 + 17
2. 第 2 轮：再加上 10（测试 Memory）
3. 第 3 轮：查询华东师范大学
4. 第 4 轮：它有几个校区（测试 Memory）
5. 第 5 轮：回顾第 1 轮的答案（测试长期 Memory）

**预期输出**：
```
第 1 轮对话：简单计算
👤 用户: 请帮我计算 25 加 17 等于多少？
🤖 Agent: 25 + 17 = 42

第 2 轮对话：引用上一轮的结果（测试 Memory）
👤 用户: 再加上 10 呢？
🤖 Agent: 42 + 10 = 52

第 3 轮对话：切换话题，查询知识库
👤 用户: 华东师范大学在哪里？
🤖 Agent: 华东师范大学位于上海市...

第 4 轮对话：继续上一个话题（测试 Memory）
👤 用户: 它有几个校区？
🤖 Agent: 华东师范大学有两个校区...

第 5 轮对话：回顾更早的对话（测试长期 Memory）
👤 用户: 我刚才问的第一个问题的答案是多少？
🤖 Agent: 第一个问题的答案是 42
```

### 2. 交互式对话

程序会自动进入交互式模式：

```
🎮 进入交互式对话模式...
   输入 'quit' 或 'exit' 退出
   输入 'new' 开始新对话（清空历史）

👤 你: 你好
🤖 Agent: 你好！有什么我可以帮助你的吗？

👤 你: 请计算 100 + 200
🤖 Agent: 100 + 200 = 300

👤 你: 再乘以 2
🤖 Agent: 300 × 2 = 600

👤 你: new
🆕 已开始新对话（历史已清空）

👤 你: 再乘以 2
🤖 Agent: 抱歉，我不知道你要对什么数字乘以 2
```

---

## 六、Memory 的优势

### 1. 自然的对话体验

**无 Memory**：
```
用户: 华东师范大学在哪里？
Agent: 在上海市

用户: 它有几个校区？
Agent: 抱歉，我不知道"它"指什么
```

**有 Memory**：
```
用户: 华东师范大学在哪里？
Agent: 在上海市

用户: 它有几个校区？
Agent: 华东师范大学有两个校区
```

### 2. 支持复杂任务

**示例：多步骤任务**
```
用户: 请帮我计算 25 + 17
Agent: 42

用户: 再加上 30
Agent: 72

用户: 再减去 10
Agent: 62

用户: 最终结果是多少？
Agent: 62
```

### 3. 减少重复输入

**无 Memory**：
```
用户: 华东师范大学的校训是什么？
Agent: 求实创造，为人师表

用户: 华东师范大学有几个校区？
Agent: 两个校区
```

**有 Memory**：
```
用户: 华东师范大学的校训是什么？
Agent: 求实创造，为人师表

用户: 有几个校区？  # 不需要重复"华东师范大学"
Agent: 两个校区
```

---

## 七、注意事项

### 1. Memory 的生命周期

| 模式 | 生命周期 |
|------|----------|
| `memory` | 仅在程序运行期间有效，重启丢失 |
| `postgres` | 持久化到 PostgreSQL，重启不丢失 |
| `hybrid` | PostgreSQL 持久化 + Redis 热缓存，重启后从 PG 恢复 |

**开发/生产切换**：
```bash
# 开发环境（.env）
MEMORY_STORE_TYPE=memory

# 生产环境（.env）
MEMORY_STORE_TYPE=hybrid
POSTGRES_HOST=your-pg-host
REDIS_HOST=your-redis-host
```

### 2. Thread ID 管理

**建议**：
- 使用用户 ID 作为 thread_id（如 `user_12345`）
- 或使用会话 ID（如 `session_abc123`）
- 避免使用随机 ID（会导致无法恢复历史）

**示例**：
```python
# ✅ 好的做法
thread_id = f"user_{user_id}"

# ❌ 不好的做法
import uuid
thread_id = str(uuid.uuid4())  # 每次都不同，无法恢复历史
```

### 3. Memory 大小控制

**问题**：对话历史会不断增长，可能导致：
- Token 超限
- 响应变慢
- 内存占用过大

**解决方案**：
```python
# 方法 1：限制历史长度
def trim_messages(messages, max_length=10):
    """只保留最近的 N 条消息"""
    if len(messages) > max_length:
        return messages[-max_length:]
    return messages

# 方法 2：定期清空历史
if message_count > 50:
    # 开始新对话
    thread_id = f"user_{user_id}_{int(time.time())}"
```

### 4. 隐私和安全

**注意**：
- Memory 中包含完整的对话历史
- 可能包含敏感信息
- 生产环境需要考虑数据加密和访问控制

---

## 八、扩展方向

### 1. 对话摘要与 Token 管理

随着对话增长，需控制 Token 消耗。当前可通过切换 thread_id 重置对话，未来可加入自动摘要机制。

### 2. 添加对话摘要

```python
def summarize_conversation(messages):
    """对长对话进行摘要"""
    if len(messages) > 20:
        # 使用 LLM 生成摘要
        summary = llm.invoke(f"请总结以下对话：{messages}")
        # 用摘要替换旧消息
        return [summary] + messages[-10:]
    return messages
```

### 3. 多模态 Memory

```python
# 支持图片、文件等
class MultimodalMemory:
    def __init__(self):
        self.text_memory = MemorySaver()
        self.image_storage = {}
        self.file_storage = {}
    
    def save_image(self, thread_id, image):
        self.image_storage[thread_id] = image
    
    def load_image(self, thread_id):
        return self.image_storage.get(thread_id)
```

---

## 九、常见问题

### Q1: Memory 会占用多少内存？
A: 取决于对话长度。每条消息约 1-2KB，100 条消息约 100-200KB。

### Q2: 如何清空某个用户的历史？
A: 
```python
# 方法 1：使用新的 thread_id
new_thread_id = f"user_{user_id}_{int(time.time())}"

# 方法 2：如果使用 SQLite，可以删除数据库记录
```

### Q3: 可以跨程序共享 Memory 吗？
A: 
- MemorySaver：不可以（内存中）
- SqliteSaver：可以（数据库文件）
- RedisSaver：可以（Redis 服务器）

### Q4: Memory 会影响性能吗？
A: 
- MemorySaver：几乎无影响
- SqliteSaver：轻微影响（磁盘 I/O）
- 对话越长，LLM 处理越慢（Token 增加）

---

## 十、总结

### 核心实现

1. ✅ `src/memory.py` — Memory 后端工厂（memory / postgres / hybrid）
2. ✅ `create_langgraph_agent` — 接受外部 checkpointer 参数
3. ✅ `run_langgraph_agent_with_memory` — 多轮对话便捷函数
4. ✅ 三级存储后端 — 通过 `MEMORY_STORE_TYPE` 一键切换
5. ✅ `app.py` — FastAPI 完整集成（lifespan + checkpointer）

### 技术要点

- **Checkpointer**：LangGraph 状态持久化接口
- **Thread ID**：对话会话隔离标识
- **MemorySaver**：内存 Checkpointer（开发）
- **PostgresSaver**：PostgreSQL Checkpointer（生产持久化）
- **Hybrid**：PostgreSQL + Redis 双层（生产推荐）

### 下一步

- 对话 Token 窗口管理
- 自动对话摘要
- 跨会话记忆共享（用户画像）
- 敏感信息过滤

---

**恭喜你完成了 Memory 功能的学习！** 🎉

现在你已经掌握了：
- LangGraph Memory 的工作原理
- 如何实现多轮对话
- Thread ID 的使用方法
- Memory 的最佳实践

继续探索和实践吧！
