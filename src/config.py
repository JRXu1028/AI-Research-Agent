"""
配置模块
管理环境变量和配置项
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """配置类"""

    # LLM 提供商：ecnu 或 local
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ecnu").lower()

    # ECNU API 配置（LLM_PROVIDER=ecnu 时使用）
    ECNU_API_KEY = os.getenv("ECNU_API_KEY")
    ECNU_BASE_URL = "https://chat.ecnu.edu.cn/open/api/v1"
    ECNU_MODEL = "ecnu-plus"

    # 本地 LLM 配置（LLM_PROVIDER=local 时使用，vLLM/Ollama 等 OpenAI 兼容服务）
    LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:8001/v1")
    LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "qwen2.5-7b-instruct")
    LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "not-needed")

    # 根据 LLM_PROVIDER 动态获取实际使用的值
    @classmethod
    def get_base_url(cls):
        if cls.LLM_PROVIDER == "local":
            return cls.LOCAL_LLM_BASE_URL
        return cls.ECNU_BASE_URL

    @classmethod
    def get_model_name(cls):
        if cls.LLM_PROVIDER == "local":
            return cls.LOCAL_LLM_MODEL
        return cls.ECNU_MODEL

    @classmethod
    def get_api_key(cls):
        if cls.LLM_PROVIDER == "local":
            return cls.LOCAL_LLM_API_KEY
        return cls.ECNU_API_KEY

    # LLM 配置
    TEMPERATURE = 0  # 0 = 更确定的输出

    @classmethod
    def validate(cls):
        """验证配置是否完整"""
        if cls.LLM_PROVIDER not in {"ecnu", "local"}:
            raise ValueError("LLM_PROVIDER 只能设置为 ecnu 或 local")

        if cls.LLM_PROVIDER == "ecnu" and not cls.ECNU_API_KEY:
            raise ValueError(
                "请设置环境变量 ECNU_API_KEY\n"
                "1. 复制 .env.example 为 .env\n"
                "2. 在 .env 中填入你的 API Key"
            )

        if cls.LLM_PROVIDER == "local":
            if not cls.LOCAL_LLM_BASE_URL:
                raise ValueError("使用本地 LLM 时请设置 LOCAL_LLM_BASE_URL")
            if not cls.LOCAL_LLM_MODEL:
                raise ValueError("使用本地 LLM 时请设置 LOCAL_LLM_MODEL")
