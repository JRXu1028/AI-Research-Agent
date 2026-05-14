"""
工具模块
定义 Agent 可以使用的所有工具
"""

from langchain_core.tools import tool


@tool
def calculator(a: float, b: float) -> float:
    """
    计算两个数的加法
    
    Args:
        a: 第一个数字
        b: 第二个数字
    
    Returns:
        两个数字的和
    """
    result = a + b
    print(f"工具调用: calculator({a}, {b}) = {result}")
    return result


@tool
def knowledge_search(query: str) -> str:
    """
    从知识库中搜索相关信息
    
    当用户询问关于华东师范大学、Python、LangChain、RAG等知识库中的内容时使用此工具。
    
    Args:
        query: 搜索查询
    
    Returns:
        相关的知识库内容
    """
    from .rag import get_rag_system
    
    print(f"工具调用: knowledge_search('{query}')")
    
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


def get_all_tools():
    """
    获取所有可用工具
    
    Returns:
        工具列表
    """
    # 返回一个工具函数列表
    return [calculator, knowledge_search]


#  -> dict: 是函数的返回类型标注（type hint）
def create_tools_map(tools: list) -> dict:
    """
    创建工具名称到工具对象的映射
    
    Args:
        tools: 工具列表
    
    Returns:
        {工具名称: 工具对象} 的字典
    """

    # 遍历 tools 列表中的每一个 tool：
    # - tool.name 作为 key（工具名称）
    # - tool 本身作为 value（工具对象）
    return {tool.name: tool for tool in tools}
