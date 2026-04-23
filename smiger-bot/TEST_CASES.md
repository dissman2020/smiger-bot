# Smiger Bot 功能清单与测试用例

## 一、功能清单

### 1. 前端功能模块

#### 1.1 聊天界面 (Chat Widget)
| 功能 | 描述 |
|------|------|
| 聊天窗口 | 嵌入式聊天组件，支持展开/收起 |
| 消息发送 | 文本输入、发送按钮、回车发送 |
| 消息展示 | 用户消息(右)、机器人消息(左)、时间戳 |
| 产品卡片 | 自动提取产品信息展示为卡片 |
| 线索表单 | 第N轮后触发线索收集表单 |
| 人工转接 | 用户可请求人工客服 |
| 多语言 | 支持中英文自动识别 |

#### 1.2 管理后台 (Admin Dashboard)
| 模块 | 功能 |
|------|------|
| 登录页 | JWT认证登录 |
| 首页 | 仪表盘统计(对话数、线索数、文档数等) |
| 对话管理 | 查看对话列表、对话详情、消息记录 |
| 知识库 | 文档上传、列表、删除、统计 |
| FAQ管理 | FAQ增删改查、批量导入、同步到向量库 |
| 线索管理 | 线索列表查看、CSV导出 |
| 转接管理 | 待处理/活跃转接列表、接受转接、回复用户、解决转接 |
| 客服数据 | 外部客服记录导入、统计 |
| Telegram支持 | 直接Telegram对话管理、AI开关、消息回复 |
| 系统设置 | API设置、模型配置、Telegram账号管理 |

### 2. 后端API功能

#### 2.1 认证模块 (Auth)
| 接口 | 方法 | 描述 |
|------|------|------|
| /api/auth/login | POST | 管理员登录获取JWT |

#### 2.2 聊天模块 (Chat)
| 接口 | 方法 | 描述 |
|------|------|------|
| /api/chat | POST | 非流式聊天 |
| /api/chat/ws/{id} | WebSocket | 流式聊天 |
| /api/chat/conversations | GET | 对话列表(管理员) |
| /api/chat/conversations/{id} | GET | 对话详情(管理员) |
| /api/chat/conversations/{id} | DELETE | 删除对话(管理员) |

#### 2.3 知识库模块 (Knowledge)
| 接口 | 方法 | 描述 |
|------|------|------|
| /api/knowledge/upload | POST | 上传文档(PDF/DOCX/XLSX/TXT) |
| /api/knowledge/documents | GET | 文档列表 |
| /api/knowledge/documents/{id} | DELETE | 删除文档 |
| /api/knowledge/stats | GET | 知识库统计 |

#### 2.4 FAQ模块 (FAQ)
| 接口 | 方法 | 描述 |
|------|------|------|
| /api/faq/entries | GET | FAQ列表(支持分类/状态/搜索筛选) |
| /api/faq/entries | POST | 创建FAQ条目 |
| /api/faq/entries/{id} | GET | 获取FAQ详情 |
| /api/faq/entries/{id} | PUT | 更新FAQ |
| /api/faq/entries/{id} | DELETE | 删除FAQ |
| /api/faq/import | POST | 批量导入FAQ(JSON/DOCX/TXT) |
| /api/faq/sync | POST | 同步FAQ到向量知识库 |
| /api/faq/categories | GET | FAQ分类列表 |

#### 2.5 线索模块 (Leads)
| 接口 | 方法 | 描述 |
|------|------|------|
| /api/leads | POST | 提交线索表单 |
| /api/leads | GET | 线索列表(管理员) |
| /api/leads/count | GET | 线索数量统计 |
| /api/leads/export | GET | 导出CSV |

#### 2.6 转接模块 (Handoff)
| 接口 | 方法 | 描述 |
|------|------|------|
| /api/admin/handoff/count | GET | 转接统计(待处理/活跃数) |
| /api/admin/handoff/list | GET | 转接列表(支持状态/地区筛选) |
| /api/admin/handoff/{id}/messages | GET | 获取对话消息 |
| /api/admin/handoff/{id}/channel | POST | 更新转接渠道(Telegram账号) |
| /api/admin/handoff/{id}/accept | POST | 接受转接 |
| /api/admin/handoff/{id}/reply | POST | 人工回复用户 |
| /api/admin/handoff/{id}/resolve | POST | 解决转接 |

#### 2.7 Telegram支持模块
| 接口 | 方法 | 描述 |
|------|------|------|
| /api/admin/telegram-support/settings | GET | 获取设置 |
| /api/admin/telegram-support/settings | PUT | 更新设置(AI开关/历史长度/系统提示词) |
| /api/admin/telegram-support/chats | GET | Telegram对话列表 |
| /api/admin/telegram-support/chats/{id} | GET | 对话详情 |
| /api/admin/telegram-support/chats/{id}/messages | POST | 发送回复 |
| /api/admin/telegram-support/chats/{id}/ai | PUT | 切换AI开关 |

#### 2.8 客服数据模块 (CS Data)
| 接口 | 方法 | 描述 |
|------|------|
| /api/cs-data | GET | 客服记录列表 |
| /api/cs-data | POST | 创建客服记录 |
| /api/cs-data/import | POST | 批量导入 |
| /api/cs-data/stats | GET | 统计信息 |

#### 2.9 仪表盘模块 (Dashboard)
| 接口 | 方法 | 描述 |
|------|------|------|
| /api/dashboard/stats | GET | 仪表盘统计数据 |

#### 2.10 设置模块 (Settings)
| 接口 | 方法 | 描述 |
|------|------|------|
| /api/settings | GET | 获取所有设置 |
| /api/settings | PUT | 更新设置 |
| /api/settings/telegram-accounts | GET | Telegram账号列表 |
| /api/settings/telegram-accounts | PUT | 更新Telegram账号配置 |

#### 2.11 Webhook模块
| 接口 | 方法 | 描述 |
|------|------|------|
| /webhook/telegram/{secret} | POST | Telegram Bot Webhook |
| /webhook/whatsapp | GET/POST | WhatsApp验证/消息 |
| /webhook/gchat | POST | Google Chat Webhook |

### 3. 核心业务逻辑

#### 3.1 RAG引擎
- 文档解析(PDF/DOCX/XLSX/TXT)
- 文本分块(可配置块大小和重叠)
- 向量嵌入(SophNet API)
- 向量存储(ChromaDB)
- 相似度搜索(余弦相似度)

#### 3.2 对话管理
- 多轮对话历史(Redis缓存)
- 上下文构建(RAG结果+历史)
- 线索触发(可配置轮数)
- 购买意图检测
- 产品卡片提取

#### 3.3 人工转接
- 转接状态机(none→pending→active→resolved)
- WebSocket实时推送
- Telegram/WhatsApp/GChat通知
- 人工消息转发

#### 3.4 多通道支持
- Web聊天(REST + WebSocket)
- Telegram Bot(轮询/Webhook)
- WhatsApp Business API
- Google Chat

---

## 二、测试用例清单

### 1. 认证模块测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| AUTH-001 | 正常登录 | 输入正确用户名密码 | 返回JWT Token | P0 |
| AUTH-002 | 错误密码登录 | 输入错误密码 | 返回401错误 | P0 |
| AUTH-003 | 空用户名 | 用户名为空 | 返回400错误 | P1 |
| AUTH-004 | Token过期 | 使用过期Token访问 | 返回401错误 | P1 |
| AUTH-005 | 无效Token | 使用伪造Token | 返回401错误 | P1 |

### 2. 聊天模块测试

#### 2.1 REST聊天接口
| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| CHAT-001 | 正常对话 | 发送产品咨询消息 | 返回相关回答和confidence | P0 |
| CHAT-002 | 新会话创建 | 不带conversation_id | 创建新会话并返回ID | P0 |
| CHAT-003 | 继续会话 | 带有效conversation_id | 继续原会话 | P0 |
| CHAT-004 | 无效会话ID | 带不存在conversation_id | 创建新会话 | P1 |
| CHAT-005 | 空消息 | 发送空字符串 | 返回400错误 | P1 |
| CHAT-006 | 超长消息 | 发送>2000字符 | 正常处理或截断 | P2 |
| CHAT-007 | 特殊字符 | 发送HTML/JS代码 | 正确转义处理 | P1 |
| CHAT-008 | 多语言中文 | 发送中文咨询 | 中文回答 | P0 |
| CHAT-009 | 多语言英文 | 发送英文咨询 | 英文回答 | P0 |
| CHAT-010 | 线索触发 | 对话超过LEAD_TRIGGER_TURN轮 | lead_prompt=true | P0 |
| CHAT-011 | 转接状态对话 | handoff_status=active时发送 | 消息转发给人工 | P0 |
| CHAT-012 | 客户信息更新 | 带region/country_code/phone | 信息保存到会话 | P1 |

#### 2.2 WebSocket聊天
| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| WS-001 | 正常连接 | 建立WebSocket连接 | 连接成功 | P0 |
| WS-002 | 流式响应 | 发送消息 | 收到流式token | P0 |
| WS-003 | 多客户端 | 同一conversation多连接 | 消息同步 | P1 |
| WS-004 | 断开重连 | 断开后再连接 | 恢复会话 | P1 |
| WS-005 | 并发消息 | 快速发送多条 | 按序处理 | P2 |

### 3. 知识库模块测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| KNOW-001 | 上传PDF | 上传有效PDF | 解析成功，status=ready | P0 |
| KNOW-002 | 上传DOCX | 上传有效DOCX | 解析成功 | P0 |
| KNOW-003 | 上传XLSX | 上传有效XLSX | 解析成功 | P0 |
| KNOW-004 | 上传TXT | 上传有效TXT | 解析成功 | P0 |
| KNOW-005 | 空文件 | 上传0字节文件 | 返回错误 | P1 |
| KNOW-006 | 超大文件 | 上传>20MB文件 | 返回413错误 | P1 |
| KNOW-007 | 不支持格式 | 上传图片文件 | 返回400错误 | P1 |
| KNOW-008 | 损坏文件 | 上传损坏PDF | status=error | P1 |
| KNOW-009 | 删除文档 | 删除存在的文档 | 文档和chunks删除 | P0 |
| KNOW-010 | 删除不存在 | 删除不存在的ID | 返回404 | P1 |
| KNOW-011 | 列表查询 | 获取文档列表 | 返回正确列表 | P0 |
| KNOW-012 | 统计查询 | 获取知识库统计 | 返回正确统计 | P0 |

### 4. FAQ模块测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| FAQ-001 | 创建FAQ | 填写完整信息创建 | 创建成功 | P0 |
| FAQ-002 | 创建缺字段 | 缺少question_cn | 返回400 | P1 |
| FAQ-003 | 列表查询 | 获取FAQ列表 | 返回列表 | P0 |
| FAQ-004 | 分类筛选 | 按category筛选 | 返回筛选结果 | P1 |
| FAQ-005 | 状态筛选 | 按is_active筛选 | 返回筛选结果 | P1 |
| FAQ-006 | 搜索 | 按关键词搜索 | 返回匹配结果 | P1 |
| FAQ-007 | 更新FAQ | 修改FAQ内容 | 更新成功 | P0 |
| FAQ-008 | 删除FAQ | 删除存在的FAQ | 删除成功 | P0 |
| FAQ-009 | 导入JSON | 上传JSON文件导入 | 导入成功 | P0 |
| FAQ-010 | 导入DOCX | 上传DOCX自动解析 | 解析导入成功 | P0 |
| FAQ-011 | 导入格式错误 | 上传错误格式JSON | 返回400 | P1 |
| FAQ-012 | 同步到向量库 | 执行sync | FAQ转为chunks | P0 |
| FAQ-013 | 分类列表 | 获取分类统计 | 返回分类列表 | P1 |

### 5. 线索模块测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| LEAD-001 | 提交线索 | 填写完整表单提交 | 创建成功 | P0 |
| LEAD-002 | 只填邮箱 | 只填必填项email | 创建成功 | P0 |
| LEAD-003 | 空邮箱 | 不填email | 返回400 | P1 |
| LEAD-004 | 无效邮箱 | 填无效格式邮箱 | 返回400 | P1 |
| LEAD-005 | 关联会话 | 带conversation_id提交 | 正确关联 | P0 |
| LEAD-006 | 列表查询 | 管理员获取列表 | 返回列表 | P0 |
| LEAD-007 | 分页 | skip/limit分页 | 正确分页 | P1 |
| LEAD-008 | 统计 | 获取线索数量 | 返回正确数量 | P1 |
| LEAD-009 | 导出CSV | 执行导出 | 返回CSV文件 | P0 |
| LEAD-010 | 大量导出 | 导出>10000条 | 正常处理 | P2 |

### 6. 转接模块测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| HAND-001 | 转接统计 | 获取待处理/活跃数 | 返回正确统计 | P0 |
| HAND-002 | 转接列表 | 获取转接列表 | 返回列表 | P0 |
| HAND-003 | 状态筛选 | 按pending/active筛选 | 正确筛选 | P1 |
| HAND-004 | 地区筛选 | 按region筛选 | 正确筛选 | P1 |
| HAND-005 | 获取消息 | 获取转接会话消息 | 返回消息列表 | P0 |
| HAND-006 | 接受转接 | 接受pending转接 | 状态变active | P0 |
| HAND-007 | 重复接受 | 接受已active转接 | 正常处理 | P1 |
| HAND-008 | 人工回复 | 发送回复消息 | 用户收到消息 | P0 |
| HAND-009 | WS推送 | 回复时WebSocket推送 | 前端收到推送 | P0 |
| HAND-010 | 解决转接 | 执行resolve | 状态变resolved | P0 |
| HAND-011 | Telegram通知 | 接受时Telegram启用 | 发送通知 | P1 |
| HAND-012 | WhatsApp通知 | 接受时WhatsApp启用 | 发送通知 | P1 |
| HAND-013 | 更新渠道 | 修改Telegram账号 | 更新成功 | P1 |

### 7. Telegram支持模块测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| TG-001 | 获取设置 | 获取TG支持设置 | 返回设置 | P0 |
| TG-002 | 更新设置 | 修改AI开关 | 更新成功 | P0 |
| TG-003 | 对话列表 | 获取TG对话列表 | 返回列表 | P0 |
| TG-004 | 对话详情 | 获取单对话详情 | 返回详情 | P0 |
| TG-005 | 发送回复 | 回复TG用户 | 发送成功 | P0 |
| TG-006 | 切换AI | 关闭AI开关 | AI不再回复 | P0 |
| TG-007 | 新消息触发 | TG用户发送消息 | 触发AI回复 | P0 |
| TG-008 | 未读计数 | 新消息增加未读 | 计数正确 | P1 |

### 8. RAG引擎测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| RAG-001 | 向量搜索 | 查询产品信息 | 返回相关chunks | P0 |
| RAG-002 | 相似度阈值 | 测试低于阈值查询 | 返回空或fallback | P0 |
| RAG-003 | 分类过滤 | 按category搜索 | 返回该分类结果 | P1 |
| RAG-004 | 文档分块 | 上传大文档 | 正确分块 | P1 |
| RAG-005 | 嵌入生成 | 测试嵌入API | 返回正确维度向量 | P0 |
| RAG-006 | 批量嵌入 | 批量文本嵌入 | 正确处理 | P1 |
| RAG-007 | 删除chunks | 删除文档 | 关联chunks删除 | P0 |

### 9. 对话管理测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| CONV-001 | 历史存储 | 多轮对话后检查 | Redis中有历史 | P0 |
| CONV-002 | 历史限制 | 超过MAX_HISTORY_TURNS | 正确截断 | P1 |
| CONV-003 | 意图检测 | 发送购买意图消息 | 检测到intent | P1 |
| CONV-004 | 产品卡片 | 回答含产品信息 | 提取产品卡片 | P0 |
| CONV-005 | 上下文构建 | 多轮后检查prompt | 包含历史+知识 | P1 |

### 10. Webhook测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| WH-001 | Telegram验证 | 发送验证请求 | 正确响应 | P0 |
| WH-002 | Telegram消息 | 用户发送消息 | 正确处理并回复 | P0 |
| WH-003 | WhatsApp验证 | 发送验证请求 | 正确响应 | P0 |
| WH-004 | WhatsApp消息 | 用户发送消息 | 正确处理 | P0 |
| WH-005 | GChat消息 | 发送消息 | 正确处理 | P0 |
| WH-006 | 无效签名 | 发送伪造签名 | 拒绝处理 | P1 |

### 11. 前端UI测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| UI-001 | 聊天窗口展开 | 点击聊天按钮 | 窗口展开 | P0 |
| UI-002 | 发送消息 | 输入并发送 | 消息显示 | P0 |
| UI-003 | 接收回复 | 等待机器人回复 | 回复显示 | P0 |
| UI-004 | 产品卡片 | 触发产品推荐 | 卡片渲染 | P0 |
| UI-005 | 线索表单 | 触发后填写提交 | 提交成功 | P0 |
| UI-006 | 登录页面 | 输入凭证登录 | 登录成功跳转 | P0 |
| UI-007 | 仪表盘加载 | 进入首页 | 统计数据加载 | P0 |
| UI-008 | 对话列表 | 进入对话管理 | 列表加载 | P0 |
| UI-009 | 文件上传 | 选择文件上传 | 上传成功 | P0 |
| UI-010 | 移动端适配 | 手机浏览器访问 | 正常显示 | P1 |

### 12. 集成测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| INT-001 | 完整对话流程 | 用户聊天→触发线索→提交 | 数据完整 | P0 |
| INT-002 | 转接全流程 | 用户请求→接受→回复→解决 | 流程正常 | P0 |
| INT-003 | 知识库更新 | 上传文档→查询验证 | 新内容可检索 | P0 |
| INT-004 | FAQ同步 | 创建FAQ→同步→查询 | 可检索到 | P0 |
| INT-005 | 多通道并发 | Web+Telegram同时对话 | 独立处理 | P1 |

### 13. 性能测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| PERF-001 | 并发聊天 | 100并发对话 | 响应<3s | P1 |
| PERF-002 | 大文档上传 | 上传20MB文档 | 处理<30s | P1 |
| PERF-003 | 向量搜索 | 1000次搜索 | 平均<100ms | P1 |
| PERF-004 | 数据库查询 | 大量数据分页 | 响应<500ms | P2 |
| PERF-005 | WebSocket并发 | 1000连接 | 稳定运行 | P2 |

### 14. 安全测试

| 用例ID | 用例名称 | 测试步骤 | 预期结果 | 优先级 |
|--------|----------|----------|----------|--------|
| SEC-001 | SQL注入 | 输入SQL注入语句 | 安全处理 | P0 |
| SEC-002 | XSS攻击 | 输入XSS脚本 | 正确转义 | P0 |
| SEC-003 | 越权访问 | 无Token访问管理接口 | 返回401 | P0 |
| SEC-004 | 文件遍历 | 上传../etc/passwd | 拒绝处理 | P0 |
| SEC-005 | 暴力破解 | 多次错误登录 | 限制或封禁 | P1 |

---

## 三、测试优先级说明

| 优先级 | 说明 |
|--------|------|
| P0 | 核心功能，必须100%通过 |
| P1 | 重要功能，建议通过 |
| P2 | 一般功能，可选测试 |

## 四、测试环境要求

1. **单元测试**: 使用pytest，mock外部依赖
2. **集成测试**: 需要完整Docker环境
3. **E2E测试**: 使用Playwright或Cypress
4. **性能测试**: 使用locust或k6

## 五、自动化建议

```bash
# 运行单元测试
pytest backend/tests/ -v

# 运行集成测试
pytest backend/tests/integration/ -v --docker

# 运行E2E测试
cd frontend && npm run test:e2e

# 性能测试
locust -f load_test.py
```
