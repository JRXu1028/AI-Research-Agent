"""
Memory 模块
管理对话历史的持久化存储
支持三种存储方式：memory、postgres、hybrid
"""

from .config import Config


async def create_checkpointer():
    """
    根据配置创建 Checkpointer 实例

    支持三种后端：
    - memory:  内存存储（开发环境，重启丢失）
    - postgres: PostgreSQL 持久化（生产环境）
    - hybrid:   PostgreSQL + Redis 缓存（推荐，性能最佳）

    Returns:
        Checkpointer 实例
    """
    store_type = Config.MEMORY_STORE_TYPE
    print(f"   📦 Memory 存储类型: {store_type}")

    if store_type == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        print("   ✅ 使用内存存储（重启后数据丢失）")
        return MemorySaver()

    elif store_type == "postgres":
        from langgraph_checkpoint_postgres import PostgresSaver

        conn_string = Config.get_postgres_async_connection_string()
        print(f"   🔗 连接 PostgreSQL: {Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}")

        checkpointer = PostgresSaver.from_conn_string(conn_string)
        await checkpointer.setup()
        print("   ✅ PostgreSQL 存储就绪")
        return checkpointer

    elif store_type == "hybrid":
        import redis.asyncio as redis
        from langgraph_checkpoint_postgres import PostgresSaver

        conn_string = Config.get_postgres_async_connection_string()
        print(f"   🔗 连接 PostgreSQL: {Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}")

        checkpointer = PostgresSaver.from_conn_string(conn_string)
        await checkpointer.setup()

        # Redis 缓存层
        redis_url = Config.get_redis_url()
        print(f"   🔗 连接 Redis: {Config.REDIS_HOST}:{Config.REDIS_PORT}")
        redis_client = redis.from_url(redis_url)
        checkpointer.redis_client = redis_client
        print("   ✅ Hybrid 存储就绪（PostgreSQL + Redis）")
        return checkpointer

    else:
        raise ValueError(
            f"不支持的 Memory 存储类型: {store_type}\n"
            f"可选值: memory, postgres, hybrid"
        )
