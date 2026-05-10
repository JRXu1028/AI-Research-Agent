"""
LangGraph Agent 模块
基于 LangGraph 实现的状态驱动 Agent（标准 ReAct 模式）
支持 Memory（对话历史持久化）
"""

from langgraph.graph import StateGraph, END
from functools import partial
from .state import AgentState
from .agent import call_model, execute_tools


# ============================================================
# 1. 节点函数（完全复用现有逻辑）
# ============================================================

def agent_node(state: AgentState, llm, tools_map) -> AgentState:
    """
    Agent 节点：调用 LLM 并让其决定是否使用工具
    
    完全复用 agent.py 的 call_model 逻辑，保留 tool_calls 机制
    """
    print(f"\n🤖 [Agent节点] 调用模型...")
    
    # 绑定工具到 LLM
    tools = list(tools_map.values())
    llm_with_tools = llm.bind_tools(tools)
    
    # 复用原有逻辑
    state = call_model(state, llm_with_tools)
    
    return state


def tool_node(state: AgentState, tools_map) -> AgentState:
    """
    工具节点：执行 LLM 决定的工具调用
    
    完全复用 agent.py 的 execute_tools 逻辑
    """
    print(f"\n🔧 [工具节点] 执行工具...")
    
    # 复用原有逻辑
    state = execute_tools(state, tools_map)
    
    return state


# ============================================================
# 2. 路由函数（基于 tool_calls，不是关键词）
# ============================================================

def should_continue(state: AgentState) -> str:
    """
    路由函数：基于 LLM 的 tool_calls 决定下一步
    
    让 LLM 通过 tool_calls 驱动流程，不使用关键词匹配
    
    Returns:
        "tools" - LLM 决定调用工具
        "end" - LLM 给出最终答案
    """
    # 检查是否有待执行的工具调用
    if state.get("tool_calls"):
        print(f"🔀 [Router] LLM 决定调用工具")
        return "tools"
    
    # 检查是否有最终答案
    if state.get("final_answer"):
        print(f"🔀 [Router] LLM 给出最终答案")
        return "end"
    
    # 默认继续（此项目理论上不应该到这里）
    # 因为逻辑为：
    # if response.tool_calls:
    #     state["tool_calls"] = response.tool_calls
    # else:
    #     state["final_answer"] = response.content
    print(f"🔀 [Router] 继续推理")
    return "continue"


# ============================================================
# 3. LangGraph 构建（标准 ReAct 模式 + Memory 支持）
# ============================================================

def create_langgraph_agent(llm, tools_map, checkpointer=None):
    """
    创建 LangGraph Agent（标准 ReAct 模式 + Memory 支持）
    
    Args:
        llm: 语言模型
        tools_map: 工具映射字典
        checkpointer: Checkpointer 实例（None 表示不使用 Memory）
    
    流程：
    START → agent (LLM 推理)
             ↓ (有 tool_calls)
           tools (执行工具)
             ↓
           agent (基于工具结果继续推理)
             ↓ (无 tool_calls)
            END
    
    特点：
    - 支持多轮推理
    - LLM 驱动流程
    - 完全复用现有逻辑
    - 可选的 Memory 支持（记住对话历史）
    """
    # 创建状态图
    workflow = StateGraph(AgentState)  # AgentState 定义了这个图中"状态"的数据结构
    
    # 使用 partial 绑定上下文，避免污染状态
    # 把函数需要的部分参数提前固定，生成一个新的函数，从而在调用时自动携带这些参数（即上下文）
    
    # 使用 functools.partial 对 agent_node 进行"参数预绑定"
    # 相当于创建一个新的函数 agent_with_context
    # 这个函数已经默认带上了：
    # - llm
    # - tools_map
    #
    # 后续调用 agent_with_context(state) 时：
    # 实际等价于 agent_node(state, llm=llm, tools_map=tools_map)
    agent_with_context = partial(agent_node, llm=llm, tools_map=tools_map)
    tool_with_context = partial(tool_node, tools_map=tools_map)
    
    # 添加节点
    workflow.add_node("agent", agent_with_context)
    workflow.add_node("tools", tool_with_context)
    
    # 设置入口点：指定流程从哪个节点开始执行
    workflow.set_entry_point("agent")
    
    # 添加条件边：agent → tools 或 END
    # 含义：从 "agent" 节点出来之后，调用 should_continue(state)，根据返回值决定下一步走向
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
            "continue": "agent"  # 支持继续推理（此项目理论不会到这）
        }
    )
    
    # 添加边：tools → agent（形成 ReAct 循环）
    # 含义：从 "tools" 节点出来之后，进入 "agent" 节点
    workflow.add_edge("tools", "agent")
    
    if checkpointer:
        # 使用传入的 checkpointer（支持 PostgreSQL、Redis 等）
        # 这会自动保存每一步的状态，支持对话历史
        """
        👉 启用 Memory 后：

        LangGraph 会自动保存每一步 state

        Memory 的作用

        ✔ 记住对话历史
        ✔ 支持多轮对话
        ✔ 每个 thread_id 是一个会话   config = {"configurable": {"thread_id": thread_id}}
        """
        app = workflow.compile(checkpointer=checkpointer)
        print("   ✅ Memory 已启用（支持多轮对话）")
    else:
        # 编译图：把定义的流程图 "编译" 成一个可执行对象    之后就可以：app.invoke(initial_state) 来运行整个 Agent
        app = workflow.compile()
    
    return app


# ============================================================
# 4. 便捷函数
# ============================================================

def run_langgraph_agent(state: AgentState, llm, tools_map: dict) -> AgentState:
    """
    运行 LangGraph Agent（无 Memory）
    
    Args:
        state: 初始状态
        llm: 语言模型
        tools_map: 工具映射字典
    
    Returns:
        最终状态
    """
    # 创建 LangGraph Agent（不使用 Memory）
    agent = create_langgraph_agent(llm, tools_map, checkpointer=None)
    
    # 运行
    # 执行这个 Agent，从 state 开始，按照图的流程自动运行：
    # 实际发生：
    # state
    #   ↓
    # agent_node（LLM）
    #   ↓
    # 是否调用工具？
    #   ↓
    # tool_node（如果需要）
    #   ↓
    # 再回 agent_node
    #   ↓
    # 直到 should_continue 返回 "end"
    final_state = agent.invoke(state)
    
    # 返回最终状态（里面包含 final_answer 等信息）
    return final_state


def run_langgraph_agent_with_memory(state: AgentState, llm, tools_map: dict, thread_id: str, checkpointer=None):
    """
    运行 LangGraph Agent（带 Memory）

    Args:
        state: 初始状态
        llm: 语言模型
        tools_map: 工具映射字典
        thread_id: 对话线程 ID（用于区分不同的对话会话）
        checkpointer: Checkpointer 实例，None 则使用内存存储

    Returns:
        最终状态
    """
    if checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()

    # 创建 LangGraph Agent（启用 Memory）
    agent = create_langgraph_agent(llm, tools_map, checkpointer=checkpointer)
    
    # 配置：指定 thread_id 来标识对话会话
    # 每个 thread_id 独立存储，避免会话冲突
    config = {"configurable": {"thread_id": thread_id}}
    
    # 运行（会自动保存和加载历史状态）
    """
    👉 和普通 invoke 的区别：
        会自动：
        
        读取历史（从 PostgreSQL/Redis）
        保存新状态（到 PostgreSQL/Redis）
        恢复上下文
    """
    final_state = agent.invoke(state, config)
    
    return final_state
