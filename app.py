#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FastAPI 后端服务
提供 /chat 接口，连接 LangGraph Agent
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import uvicorn

from src.llm import create_llm
from src.tools import get_all_tools, create_tools_map
from src.state import create_initial_state
from src.rag import initialize_rag_system
from src.langgraph_agent import run_langgraph_agent


# ============================================================
# 1. 全局变量（已废弃，使用 app.state）
# ============================================================
# 注意：现在使用 app.state 存储，不再使用全局变量


# ============================================================
# 2. 生命周期管理
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    
    print("\n" + "=" * 70)
    print("[startup] 正在启动 AI Research Agent 服务...")
    print("=" * 70)
    
    try:
        # 初始化 LLM
        print("\n[1/3] 初始化 LLM...")
        llm = create_llm()
        app.state.llm = llm
        print("      LLM 初始化完成")
        
        # 初始化 RAG 系统
        print("\n[2/3] 初始化 RAG 系统...")
        initialize_rag_system(force_reload=False)
        print("      RAG 系统初始化完成")
        
        # 加载工具
        print("\n[3/3] 加载工具...")
        tools = get_all_tools()
        tools_map = create_tools_map(tools)
        app.state.tools_map = tools_map
        print(f"      已加载 {len(tools)} 个工具: {', '.join(tools_map.keys())}")
        
        print("\n" + "=" * 70)
        print("AI Research Agent 服务启动成功!")
        print("   访问地址: http://localhost:8000")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n服务启动失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    yield
    
    print("\n[shutdown] 服务关闭中...")
    

# ============================================================
# 3. FastAPI 应用初始化
# ============================================================

app = FastAPI(
    title="AI Research Agent API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS（允许浏览器跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本地开发允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 4. 请求/响应模型
# ============================================================

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str  # 用户消息
    thread_id: Optional[str] = "default"  # 客户端会话 ID，仅用于响应透传


class ChatResponse(BaseModel):
    """聊天响应"""
    answer: str  # Agent 回答
    thread_id: str  # 会话 ID
    message_count: int  # 当前对话历史消息数


# ============================================================
# 5. API 端点
# ============================================================

@app.get("/")
async def root():
    """根路径"""
    return {"message": "AI Research Agent API", "docs": "/docs"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天接口
    
    接收用户消息，调用 Agent，返回回答
    """
    try:
        # 验证输入
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="消息不能为空")
        
        print(f"\n收到消息 [thread_id={request.thread_id}]: {request.message}")
        
        # 从 app.state 获取组件
        llm = app.state.llm
        tools_map = app.state.tools_map
        
        # 创建初始状态
        initial_state = create_initial_state(request.message)
        
        # 调用 Agent（无服务端对话 Memory，每次请求独立推理）
        final_state = run_langgraph_agent(
            initial_state,
            llm,
            tools_map
        )
        
        # 提取答案
        answer = final_state.get('final_answer', '抱歉，我无法回答这个问题')
        message_count = len(final_state.get('messages', []))
        
        print(f"回答生成完成 [消息数={message_count}]")
        
        return ChatResponse(
            answer=answer,
            thread_id=request.thread_id,
            message_count=message_count
        )
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "message": "AI Research Agent is running"}


# ============================================================
# 6. 主函数
# ============================================================

if __name__ == "__main__":
    # 启动服务
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
