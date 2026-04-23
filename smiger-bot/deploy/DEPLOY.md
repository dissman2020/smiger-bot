# Smiger AI 智能客服 — 部署指南

## 系统要求

| 项目 | 最低要求 |
|---|---|
| 操作系统 | Linux / macOS / Windows (支持 Docker) |
| Docker | >= 20.10 |
| Docker Compose | >= 2.0 (推荐 V2) |
| 内存 | >= 4 GB |
| 磁盘 | >= 5 GB 可用空间 |

## 部署包内容

```
deploy/
├── docker-compose.yml        # 编排文件
├── .env.example              # 环境变量模板
├── smiger-bot-images.tar     # 全部 Docker 镜像 (~1.4 GB)
├── seed_data/                # 产品知识库数据 (JSON)
└── DEPLOY.md                 # 本文档
```

## 快速部署 (3 步)

### 1. 导入镜像

将 `smiger-bot-images.tar` 复制到目标服务器后，执行：

```bash
docker load -i smiger-bot-images.tar
```

导入完成后可验证：

```bash
docker images | grep smiger-bot
```

应看到：

```
smiger-bot/backend    1.0.4   ...
smiger-bot/frontend   1.0.4   ...
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，**必须修改**以下项：

| 变量 | 说明 |
|---|---|
| `LLM_API_KEY` | LLM 服务的 API Key |
| `EMBEDDING_URL` | Embedding 服务地址 |
| `EMBEDDING_EASYLLM_ID` | Embedding 项目 ID |
| `ADMIN_PASSWORD` | 管理后台登录密码 |
| `SECRET_KEY` | JWT 签名密钥 (随机字符串) |

可选修改：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `POSTGRES_PASSWORD` | postgres | 数据库密码 |
| `BACKEND_PORT` | 8000 | 后端 API 端口 |
| `FRONTEND_PORT` | 3000 | 前端页面端口 |
| `DB_PORT` | 5432 | PostgreSQL 端口 |
| `REDIS_PORT` | 6379 | Redis 端口 |

### 3. 启动服务

```bash
docker compose up -d
```

等待所有服务就绪 (约 30 秒)，检查状态：

```bash
docker compose ps
```

所有服务应显示 `running` (healthy)。

## 访问地址

| 服务 | 地址 |
|---|---|
| 前端页面 (含智能客服聊天) | `http://<服务器IP>:3000` |
| 管理后台 | `http://<服务器IP>:3000/admin` |
| 后端 API | `http://<服务器IP>:8000` |
| API 文档 (Swagger) | `http://<服务器IP>:8000/docs` |

管理后台默认账号：`admin` / 您在 `.env` 中设置的密码。

## 包含的镜像

| 镜像 | 版本 | 说明 |
|---|---|---|
| `smiger-bot/backend` | 1.0.4 | FastAPI 后端 + RAG + LLM |
| `smiger-bot/frontend` | 1.0.4 | Next.js 14 前端 |
| `postgres` | 16-alpine | PostgreSQL 数据库 |
| `redis` | 7-alpine | Redis 缓存 |

## 数据持久化

Docker Compose 使用命名卷持久化数据：

- `pgdata` — PostgreSQL 数据
- `chroma_data` — 向量数据库 (ChromaDB)

数据在 `docker compose down` 后保留；仅在 `docker compose down -v` 时删除。

## 知识库数据

`seed_data/` 目录包含产品和 FAQ 数据 (JSON 格式)。后端首次启动时会自动加载。如需更新知识库：

1. 修改 `seed_data/` 中的 JSON 文件
2. 重启后端：`docker compose restart backend`

## 常见问题

### Q: 前端访问后端 API 报跨域 / 连接失败？

前端镜像中 API 地址默认为 `http://localhost:8000`。如果前端和后端不在同一台机器，或使用了不同端口，需要重新构建前端镜像。

### Q: 如何查看日志？

```bash
# 查看所有日志
docker compose logs -f

# 查看某个服务
docker compose logs -f backend
```

### Q: 如何完全重置？

```bash
docker compose down -v   # 删除容器和数据卷
docker compose up -d     # 重新启动
```

### Q: 如何更新镜像？

收到新的 `smiger-bot-images.tar` 后：

```bash
docker compose down
docker load -i smiger-bot-images.tar
docker compose up -d
```

## 技术栈

- **后端**: Python 3.11 / FastAPI / SQLAlchemy / ChromaDB
- **前端**: Next.js 14 / React / Tailwind CSS
- **数据库**: PostgreSQL 16 / Redis 7
- **AI**: RAG 架构 + LLM (DeepSeek) + Embedding
