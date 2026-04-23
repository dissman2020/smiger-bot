# GitHub -> 公网域名部署（Telegram Webhook）

## 先说结论

- `GitHub` 适合托管代码，不适合直接跑这个 FastAPI + Next.js + PostgreSQL + Redis 项目。
- 这套项目更适合：
  - `GitHub + Render`
  - `GitHub + Railway`
- Telegram webhook 只要求你的后端有一个可公网访问的 `HTTPS` 地址。

项目已经支持两种 Telegram 模式：

- `TELEGRAM_MODE=polling`：本地开发用，不需要公网域名
- `TELEGRAM_MODE=webhook`：云端部署用，需要公网 HTTPS 域名

Webhook 路径固定为：

```text
/api/webhook/telegram
```

## 推荐部署结构

### 后端

- 类型：Docker Web Service
- 目录：`smiger-bot/backend`
- 需要的配套服务：
  - PostgreSQL
  - Redis
  - 持久化磁盘（挂载给 Chroma）

### 前端

- 类型：Docker Web Service
- 目录：`smiger-bot/frontend`
- 构建变量：
  - `NEXT_PUBLIC_API_URL=https://你的后端域名`

## 后端环境变量

最少要配置这些：

```env
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
CHROMA_PERSIST_DIR=/app/chroma_data

LLM_API_KEY=...
LLM_BASE_URL=...
LLM_MODEL=...
EMBEDDING_URL=...
EMBEDDING_EASYLLM_ID=...
EMBEDDING_DIMENSIONS=1024

ADMIN_USERNAME=admin
ADMIN_PASSWORD=请改成你自己的
SECRET_KEY=请改成随机长字符串

TELEGRAM_ENABLED=true
TELEGRAM_MODE=webhook
TELEGRAM_BOT_TOKEN=你的 Bot Token
TELEGRAM_ADMIN_CHAT_ID=你的 Telegram Chat ID
TELEGRAM_WEBHOOK_SECRET=可选，建议设置
TELEGRAM_WEBHOOK_BASE_URL=https://你的后端域名
```

部署后，Telegram webhook 完整地址就是：

```text
https://你的后端域名/api/webhook/telegram
```

应用启动时会自动调用 Telegram `setWebhook` 注册这个地址。

## Render 部署步骤

1. 把 `smiger-bot` 推到 GitHub 仓库。
2. 在 Render 创建 PostgreSQL。
3. 在 Render 创建 Redis / Key Value 服务。
4. 创建 Backend Web Service，根目录选 `smiger-bot/backend`，使用仓库里的 `Dockerfile`。
5. 给后端挂一个磁盘到 `/app/chroma_data`。
6. 配置上面的后端环境变量。
7. 创建 Frontend Web Service，根目录选 `smiger-bot/frontend`。
8. Frontend 构建变量里设置：

```env
NEXT_PUBLIC_API_URL=https://你的后端域名
```

## Railway 部署步骤

1. 把 `smiger-bot` 推到 GitHub 仓库。
2. 在 Railway 新建项目并连接 GitHub 仓库。
3. 添加 PostgreSQL 服务。
4. 添加 Redis 服务。
5. 新建 Backend 服务，Root Directory 设为 `smiger-bot/backend`。
6. 新建 Frontend 服务，Root Directory 设为 `smiger-bot/frontend`。
7. 给 Backend 配置环境变量，并把 `TELEGRAM_WEBHOOK_BASE_URL` 设成后端公网域名。
8. 给 Frontend 设置：

```env
NEXT_PUBLIC_API_URL=https://你的后端域名
```

## 首次部署后的检查

### 1. 健康检查

打开：

```text
https://你的后端域名/api/health
```

应返回：

```json
{"status":"ok","service":"smiger-bot"}
```

### 2. 检查 Telegram webhook

如果后端日志里看到类似下面的信息，说明 webhook 已注册：

```text
Telegram webhook configured: https://你的后端域名/api/webhook/telegram
```

### 3. 导入种子数据

项目首次部署后，最好执行一次：

```bash
python -m app.seed
```

这样商品和 FAQ 数据会进入知识库。

## 常见问题

### 前端页面能打开，但请求后端失败

通常是 `NEXT_PUBLIC_API_URL` 没配对，或者前端还在用旧构建产物。重新触发前端部署即可。

### Telegram 没收到消息

优先检查：

- `TELEGRAM_ENABLED=true`
- `TELEGRAM_MODE=webhook`
- `TELEGRAM_BOT_TOKEN` 是否正确
- `TELEGRAM_ADMIN_CHAT_ID` 是否正确
- `TELEGRAM_WEBHOOK_BASE_URL` 是否是后端公网 HTTPS 地址

### 是否还能继续用 polling

可以。本地开发时保留：

```env
TELEGRAM_MODE=polling
```

云端切到：

```env
TELEGRAM_MODE=webhook
```
