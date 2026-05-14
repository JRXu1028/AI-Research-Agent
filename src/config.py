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

    # PostgreSQL 配置
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "ai_research_agent")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

    # Redis 配置
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = os.getenv("REDIS_PORT", "6379")
    REDIS_DB = os.getenv("REDIS_DB", "0")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

    # 向量数据库类型：chroma 或 postgres
    VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "chroma")

    # Memory 存储类型：memory, postgres, hybrid
    # memory: 内存存储（开发环境，重启丢失）
    # postgres: PostgreSQL 持久化（生产环境）
    # hybrid: PostgreSQL + Redis（推荐，性能最佳）
    MEMORY_STORE_TYPE = os.getenv("MEMORY_STORE_TYPE", "memory")

    @classmethod
    def get_postgres_connection_string(cls):
        """获取 PostgreSQL 连接字符串（用于向量数据库）"""
        return (
            f"postgresql+psycopg://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}"
            f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        )

    @classmethod
    def get_postgres_async_connection_string(cls):
        """获取 PostgreSQL 异步连接字符串（用于LangGraph checkpointer）"""
        return (
            f"postgresql+psycopg://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}"
            f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        )

    @classmethod
    def get_redis_url(cls):
        """获取 Redis 连接URL"""
        if cls.REDIS_PASSWORD:
            return f"redis://:{cls.REDIS_PASSWORD}@{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"
        return f"redis://{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"

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

        if cls.VECTOR_STORE_TYPE == "postgres" and not cls.POSTGRES_PASSWORD:
            raise ValueError(
                "使用 PostgreSQL 时请设置 POSTGRES_PASSWORD\n"
                "在 .env 中添加: POSTGRES_PASSWORD=your_password"
            )
