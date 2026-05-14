# LangGraph Agent

当前 LangGraph 层只负责 ReAct 状态流转，不负责服务端对话 Memory。

## Flow

```text
START
  -> agent: call LLM with tools
  -> tools: execute tool calls when needed
  -> agent
  -> END when final_answer is produced
```

## Core Files

```text
src/agent.py            # call_model / execute_tools / run_agent
src/langgraph_agent.py  # StateGraph wrapper
src/state.py            # AgentState
src/tools.py            # calculator / knowledge_search
```

## Why Keep LangGraph

- Explicit state transitions
- Easy to add fine-tuning evaluation nodes later
- ReAct loop remains readable and testable

## Current Scope

Included:

- Tool calling
- RAG tool integration
- Local Qwen invocation through `ChatOpenAI`

Not included:

- Checkpointer
- Server-side conversation Memory
- Server-side conversation history
