"""
Agent 模块
实现状态驱动的 Agent 核心逻辑
"""

from langchain_core.messages import ToolMessage
from .state import AgentState


def call_model(state: AgentState, llm_with_tools) -> AgentState:
    """
    调用 LLM，基于当前状态生成响应
    
    Args:
        state: 当前状态
        llm_with_tools: 绑定了工具的 LLM
    
    Returns:
        更新后的状态
    """
    print("\n调用模型...")
    
    # 从状态中获取消息
    messages = state["messages"]
    
    # 调用 LLM
    response = llm_with_tools.invoke(messages)
    
    # 更新状态：添加 AI 响应
    state["messages"].append(response)

    """
    response结构

    response = AIMessage(
        content="25 + 17 等于 42",
        tool_calls=[]
    )

    response = AIMessage(
    content="",  # 可能为空
    tool_calls=[
        {
            "name": "calculator",
            "args": {
                "expression": "25 + 17"
            },
            "id": "call_123"
        }
    ]
)
    """
    # 检查是否有工具调用
    if response.tool_calls:
        print(f"模型决定: 需要调用 {len(response.tool_calls)} 个工具")
        state["tool_calls"] = response.tool_calls
    else:
        print("模型决定: 不需要工具，直接回答")
        state["tool_calls"] = None
        state["final_answer"] = response.content
    
    return state


def execute_tools(state: AgentState, tools_map: dict) -> AgentState:
    """
    执行工具调用，基于状态中的 tool_calls
    
    Args:
        state: 当前状态
        tools_map: 工具名称到工具对象的映射
    
    Returns:
        更新后的状态
    """

    """
    tool_calls=[
        {
            "name": "calculator",
            "args": {
                "expression": "25 + 17"
            },
            "id": "call_123"
        }
    ]
    """
    tool_calls = state.get("tool_calls")
    
    if not tool_calls:
        print("无需执行工具")
        return state
    
    print("\n执行工具...")
    
    # 执行所有工具调用
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        # 从工具映射中获取工具并调用
        tool = tools_map.get(tool_name)
        if tool:
            # 执行工具
            tool_result = tool.invoke(tool_args)
        else:
            tool_result = f"错误: 未找到工具 '{tool_name}'"
            print(tool_result)
        
        # 将工具结果添加到状态的消息历史
        state["messages"].append(
            ToolMessage(
                content=str(tool_result),
                tool_call_id=tool_call["id"]
            )
        )
        """
        messages = [
            HumanMessage(content="25 + 17 等于多少？"),

            AIMessage(
                content="",
                tool_calls=[{"name": "calculator", "args": {...}, "id": "1"}]
            ),

            ToolMessage(
                content="42",
                tool_call_id="1"
            ),
            
            ...
            AIMessage(
                content="25 + 17 等于 42"
            )
        ]
        """
    
    # 清空 tool_calls（已执行完毕）
    state["tool_calls"] = None
    
    return state


def should_continue(state: AgentState) -> bool:
    """
    判断是否需要继续执行（路由函数）
    
    Args:
        state: 当前状态
    
    Returns:
        True（继续）或 False（结束）
    """
    # 如果有待执行的工具调用，继续
    if state.get("tool_calls"):
        return True
    
    # 如果已有最终答案，结束
    if state.get("final_answer"):
        return False
    
    # 默认继续
    return True


def run_agent(state: AgentState, llm_with_tools, tools_map: dict, max_iterations: int = 10) -> AgentState:
    """
    运行 Agent 的主函数（状态驱动，支持多轮推理）
    
    Args:
        state: 初始状态
        llm_with_tools: 绑定了工具的 LLM
        tools_map: 工具映射字典
        max_iterations: 最大迭代次数（防止无限循环）
    
    Returns:
        最终状态
    
    工作流程（ReAct 循环）：
    1. 调用模型 -> 更新 state
    2. 如果需要工具 -> 执行工具 -> 回到步骤 1
    3. 如果不需要工具 -> 返回最终答案
    """
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Step 1: 调用模型
        state = call_model(state, llm_with_tools)
        
        # Step 2: 检查是否需要继续
        if not should_continue(state):
            # 已有最终答案，结束
            break
        
        # Step 3: 执行工具
        state = execute_tools(state, tools_map)
        
        # 继续下一轮循环
    
    if iteration >= max_iterations:
        print(f"达到最大迭代次数 ({max_iterations})，强制结束")
        if not state.get("final_answer"):
            state["final_answer"] = "抱歉，推理过程超时"
    
    return state
