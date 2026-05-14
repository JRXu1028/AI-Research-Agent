"""
LLM 模块
负责初始化和配置语言模型
"""

from langchain_openai import ChatOpenAI
from .config import Config


def create_llm(temperature: float = None):
    """
    创建 LLM 实例
    
    Args:
        temperature: 温度参数，控制输出的随机性（0-1）
                    None 则使用配置文件中的默认值
    
    Returns:
        ChatOpenAI 实例
    """
    # 校验配置是否完整（比如 API_KEY、BASE_URL 是否存在）
    # 防止在创建 LLM 时出现配置缺失问题
    Config.validate()

    return ChatOpenAI(
        model=Config.get_model_name(),
        openai_api_key=Config.get_api_key(),
        openai_api_base=Config.get_base_url(),
        temperature=temperature if temperature is not None else Config.TEMPERATURE,
    )


def bind_tools_to_llm(llm, tools: list):
    """
    将工具绑定到 LLM
    
    Args:
        llm: LLM 实例
        tools: 工具列表
    
    Returns:
        绑定了工具的 LLM
    """
    return llm.bind_tools(tools)
