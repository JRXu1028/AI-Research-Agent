# 部署指南

## 架构概览

生产部署推荐架构：

```
浏览器 → Nginx (HTTPS) → FastAPI (app.py)
                              ├── PostgreSQL + pgvector（向量数据库）
                              ├── PostgreSQL（Memory 持久化）
                              └── Redis（Memory 缓存加速）
```

## 部署方式

### 方式一：Docker Compose（推荐）

创建 `docker-compose.yml`：

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ai_research_agent
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      ECNU_API_KEY: ${ECNU_API_KEY}
      VECTOR_STORE_TYPE: postgres
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: ai_research_agent
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your_password
      MEMORY_STORE_TYPE: hybrid
      REDIS_HOST: redis
      REDIS_PORT: 6379
    depends_on:
      - postgres
      - redis

volumes:
  pgdata:
  redisdata:
```

```bash
# 启动
ECNU_API_KEY=your_key docker compose up -d

# 查看日志
docker compose logs -f app
```

### 方式二：手动部署

#### 1. 安装 PostgreSQL + pgvector

**Ubuntu/Debian：**

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo apt install postgresql-16-pgvector
```

**使用 Docker：**

```bash
docker run -d \
  --name postgres-pgvector \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=ai_research_agent \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

#### 2. 创建数据库和扩展

```bash
psql -U postgres -d ai_research_agent
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

#### 3. 安装 Redis（Hybrid Memory 模式需要）

```bash
# Ubuntu/Debian
sudo apt install redis-server

# Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

#### 4. 配置环境变量

编辑 `.env`：

```bash
# API
ECNU_API_KEY=your_api_key_here

# 向量数据库
VECTOR_STORE_TYPE=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_research_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Memory 存储（hybrid 推荐）
MEMORY_STORE_TYPE=hybrid
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

#### 5. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

#### 6. 构建前端

```bash
cd frontend
npm install
npm run build
```

生成的静态文件在 `frontend/dist/`，可用 Nginx 直接托管。

#### 7. 启动服务

```bash
python app.py
```

---

## 环境变量参考

| 变量 | 说明 | 默认值 | 必填 |
|------|------|--------|------|
| `ECNU_API_KEY` | API 密钥 | - | ✅ |
| `VECTOR_STORE_TYPE` | 向量数据库类型：`chroma` / `postgres` | `chroma` | |
| `MEMORY_STORE_TYPE` | Memory 类型：`memory` / `postgres` / `hybrid` | `memory` | |
| `POSTGRES_HOST` | PostgreSQL 主机 | `localhost` | postgres 模式时 |
| `POSTGRES_PORT` | PostgreSQL 端口 | `5432` | |
| `POSTGRES_DB` | PostgreSQL 数据库名 | `ai_research_agent` | |
| `POSTGRES_USER` | PostgreSQL 用户名 | `postgres` | |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 | - | postgres 模式时 |
| `REDIS_HOST` | Redis 主机 | `localhost` | hybrid 模式时 |
| `REDIS_PORT` | Redis 端口 | `6379` | |
| `REDIS_DB` | Redis 数据库编号 | `0` | |
| `REDIS_PASSWORD` | Redis 密码 | - | |

---

## 存储架构选择指南

### 向量数据库

| 场景 | 推荐 | 配置 |
|------|------|------|
| 本地开发 | Chroma | `VECTOR_STORE_TYPE=chroma` |
| 单机生产 | PostgreSQL | `VECTOR_STORE_TYPE=postgres` |
| 多副本生产 | PostgreSQL（共享数据库） | `VECTOR_STORE_TYPE=postgres` |

### Memory 存储

| 场景 | 推荐 | 配置 |
|------|------|------|
| 本地开发 / 调试 | memory | `MEMORY_STORE_TYPE=memory` |
| 单机生产（无 Redis） | postgres | `MEMORY_STORE_TYPE=postgres` |
| 生产环境（最佳性能） | hybrid | `MEMORY_STORE_TYPE=hybrid` |

---

## 生产环境建议

1. **Nginx 反向代理** — 将 8000 端口代理到 80/443，配置 HTTPS
2. **进程管理** — 使用 systemd 或 Supervisor 守护 app.py 进程
3. **CORS 限制** — 修改 `app.py` 中 `allow_origins` 为具体域名
4. **数据库备份** — 定期备份 PostgreSQL 数据目录
5. **日志管理** — 配置日志轮转，接入监控系统
6. **资源限制** — HuggingFace Embedding 模型首次加载需下载约 90MB，确保磁盘空间

## 云数据库选项

- **Supabase** — 免费套餐，自带 pgvector 支持
- **AWS RDS** — 需手动安装 pgvector 扩展
- **Google Cloud SQL** — 支持 pgvector
- **Redis Cloud** — 托管 Redis，适合 hybrid Memory 模式
