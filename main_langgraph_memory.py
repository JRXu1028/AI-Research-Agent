#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LangGraph Agent with Memory 演示
展示如何使用 Memory 实现多轮对话
"""

import sys
import io

# 设置标准输出为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.llm import create_llm
from src.tools import get_all_tools, create_tools_map
from src.state import create_initial_state
from src.rag import initialize_rag_system
from src.langgraph_agent import run_langgraph_agent_with_memory
from langgraph.checkpoint.memory import MemorySaver


def print_separator():
    """打印分隔线"""
    print("\n" + "=" * 70)


def main():
    """主函数"""
    
    print_separator()
    print("🧠 LangGraph Agent with Memory - 多轮对话演示")
    print_separator()
    
    # 1. 初始化 LLM
    print("\n[1/5] 初始化 LLM...")
    llm = create_llm()
    print("      ✅ LLM 初始化完成")
    
    # 2. 初始化 RAG 系统
    print("\n[2/5] 初始化 RAG 系统...")
    initialize_rag_system(force_reload=False)
    
    # 3. 获取工具
    print("\n[3/5] 加载工具...")
    tools = get_all_tools()
    tools_map = create_tools_map(tools)
    print(f"      ✅ 已加载 {len(tools)} 个工具: {', '.join(tools_map.keys())}")
    
    print("\n[4/5] 初始化 Memory...")
    checkpointer = MemorySaver()
    print("      ✅ Memory 已启用（内存存储）")

    print("\n[5/5] LangGraph Agent 准备就绪!")
    print_separator()
    
    # 4. 多轮对话演示
    print("\n💬 开始多轮对话演示...")
    print("   提示：Agent 会记住之前的对话内容")
    print_separator()
    
    # 使用同一个 thread_id 来标识这个对话会话
    thread_id = "demo_conversation_001"
    
    # 对话序列（展示 Memory 的作用）
    conversations = [
        {
            "round": 1,
            "question": "请帮我计算 25 加 17 等于多少？",
            "description": "第一轮：简单计算"
        },
        {
            "round": 2,
            "question": "再加上 10 呢？",
            "description": "第二轮：引用上一轮的结果（测试 Memory）"
        },
        {
            "round": 3,
            "question": "华东师范大学在哪里？",
            "description": "第三轮：切换话题，查询知识库"
        },
        {
            "round": 4,
            "question": "它有几个校区？",
            "description": "第四轮：继续上一个话题（测试 Memory）"
        },
        {
            "round": 5,
            "question": "我刚才问的第一个问题的答案是多少？",
            "description": "第五轮：回顾更早的对话（测试长期 Memory）"
        }
    ]
    
    for conv in conversations:
        round_num = conv["round"]
        question = conv["question"]
        description = conv["description"]
        
        print(f"\n\n{'🔵' * 35}")
        print(f"第 {round_num} 轮对话：{description}")
        print(f"{'🔵' * 35}")
        print(f"\n👤 用户: {question}")
        
        try:
            # 创建初始状态
            initial_state = create_initial_state(question)
            
            # 运行 Agent（带 Memory）
            # 关键：使用相同的 thread_id，Agent 会自动加载历史对话
            final_state = run_langgraph_agent_with_memory(
                initial_state,
                llm,
                tools_map,
                thread_id=thread_id,
                checkpointer=checkpointer
            )

            # 打印结果
            answer = final_state.get('final_answer', '无答案')
            print(f"\n🤖 Agent: {answer}")
            
            # 显示对话历史长度
            message_count = len(final_state.get('messages', []))
            print(f"\n📊 当前对话历史: {message_count} 条消息")
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
    
    print_separator()
    print("\n✅ 多轮对话演示完成!")
    print("\n💡 说明:")
    print("   - 所有对话使用同一个 thread_id，因此 Agent 能记住上下文")
    print("   - 第 2 轮：'再加上 10' - Agent 知道是在 42 的基础上加")
    print("   - 第 4 轮：'它有几个校区' - Agent 知道'它'指的是华东师范大学")
    print("   - 第 5 轮：Agent 能回顾第 1 轮的答案")
    print_separator()
    
    # 5. 交互式对话模式
    print("\n\n🎮 进入交互式对话模式...")
    print("   输入 'quit' 或 'exit' 退出")
    print("   输入 'new' 开始新对话（清空历史）")
    print_separator()
    
    # 新的对话会话
    interactive_thread_id = "interactive_session"
    
    while True:
        try:
            user_input = input("\n👤 你: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("\n👋 再见！")
                break
            
            if user_input.lower() in ['new', '新对话']:
                # 更换 thread_id 开始新对话
                import time
                interactive_thread_id = f"interactive_{int(time.time())}"
                print("\n🆕 已开始新对话（历史已清空）")
                continue
            
            # 创建状态
            state = create_initial_state(user_input)
            
            # 运行 Agent
            final_state = run_langgraph_agent_with_memory(
                state,
                llm,
                tools_map,
                thread_id=interactive_thread_id,
                checkpointer=checkpointer
            )
            
            # 显示回答
            answer = final_state.get('final_answer', '无答案')
            print(f"\n🤖 Agent: {answer}")
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    main()
