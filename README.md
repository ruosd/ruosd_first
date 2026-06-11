# 多Agent电商客服系统

基于 LangGraph + FastAPI 的企业级智能客服系统，LLM 语义意图识别、多 Agent 协作、工具调用、流式对话、多租户隔离。

---

## 核心能力

| 能力 | 技术方案 |
|------|---------|
| 意图路由 | LLM 语义理解（非关键词匹配），max_tokens=10 极速分类 |
| Agent 协作 | LangGraph 有向图编排，3 个专业 Agent + 条件路由 |
| 工具调用 | 7 个异步工具（查订单、搜产品、搜知识库），LLM 自主决策 |
| 流式对话 | SSE 真流式输出，首 token < 0.5s |
| 对话归档 | 超 3000 token 自动 LLM 摘要压缩，省 80%+ token |
| 多租户 | JWT → user_id → ChromaDB 元数据过滤，用户记忆隔离 |
| 向量知识库 | ChromaDB + Ollama bge-m3，TXT/PDF/DOCX 上传自动分块 |
| 异步任务 | Celery + Redis，大文件上传不阻塞 HTTP |
| 安全 | bcrypt 密码、JWT 环境变量化、API 限流、CORS 白名单、输入长度校验 |
| 可观测 | JSON 结构化日志、Prometheus /metrics、逐依赖健康检查 |

---

## 架构

```
用户 → Vue3 前端 → Nginx → FastAPI
                              │
                    ┌─────────┼──────────┐
                    │   LangGraph 协作图   │
                    │  classify → route   │
                    │   ┌────┬────┬────┐  │
                    │  order product svc │
                    │   └────┴────┴────┘  │
                    │       summarize     │
                    └─────────┼──────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
           MySQL         ChromaDB          Redis
         (订单/物流)     (向量/记忆)      (缓存/队列)
```

---

## 快速开始

### 前置条件

- Docker Desktop + Ollama（宿主机运行，bge-m3 模型已拉取）
- 阿里云百炼 API Key

### 1. 启动 Ollama（如使用本地嵌入）

```cmd
set OLLAMA_HOST=0.0.0.0 && ollama serve
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的阿里云百炼 API Key：
#   ALIYUN_API_KEY=your_key_here
#   ADMIN_PASSWORD=your_admin_password
```

### 3. 一键部署

```bash
docker compose up -d --build
```

### 4. 填充测试数据

```bash
docker compose exec web python scripts/seed_data.py
```

### 5. 打开前端

`http://localhost:3000`

| 角色 | 账号 | 密码 |
|------|------|------|
| 测试用户 | zhangsan | 123456 |
| 测试用户 | lisi | 123456 |
| 管理员 | admin | 由 `.env` 中 `ADMIN_PASSWORD` 配置 |

---

## 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Vue 前端 | 3000 | 管理后台 + 聊天 |
| FastAPI | 8000 | 后端 API |
| MySQL | 3307 | 订单数据库 |
| Redis | 6379 | 缓存和消息队列 |
| Celery Worker | — | 异步任务处理 |

API 文档: `http://localhost:8000/docs`
Prometheus 指标: `http://localhost:8000/metrics`
健康检查: `http://localhost:8000/health`

---

## 项目结构

```
├── src/
│   ├── agents/              # Agent 模块（base/order/product/service）
│   ├── services/            # 业务服务（订单/产品/知识库/记忆/LLM）
│   ├── graph/               # LangGraph 协作引擎
│   │   ├── state.py         # AgentState 状态定义
│   │   ├── intent_router.py # LLM 意图分类器
│   │   ├── tools.py         # 7 个 Agent 工具
│   │   ├── agent_graph.py   # 协作图构建
│   │   └── graph_coordinator.py  # 流式 + 非流式协调器
│   ├── tasks/               # Celery 异步任务
│   ├── platforms/            # 平台适配层（MySQL/淘宝/京东）
│   │   ├── base.py           # PlatformAdapter 抽象接口
│   │   ├── mock_adapter.py   # 自有数据库实现
│   │   └── taobao_adapter.py # 淘宝 API 实现
│   ├── routers/             # API 路由（chat/admin/user/system）
│   ├── models/              # Pydantic 数据模型
│   └── utils/               # 工具（配置/DB/日志/密码/错误码）
├── frontend-vue/            # Vue3 前端（浅色极简风）
├── knowledge_docs/          # 知识文档（测试用）
├── main.py                  # 应用入口
├── docker-compose.yml       # 6 服务编排
├── pyproject.toml           # ruff 代码质量配置
└── .env                     # 环境变量
```

---

## 典型对话测试

| 问题 | 预期结果 |
|------|---------|
| "查询订单 TEST202406090001" | 订单 Agent → query_order 工具 → 返回详情 |
| "我的订单" | 订单 Agent → list_user_orders → 返回列表 |
| "推荐一款手机" | 产品 Agent → search_product → 返回推荐 |
| "iPhone 15 Pro Max 参数" | 产品 Agent → get_product_detail |
| "怎么退货" | 客服 Agent → search_knowledge → 退货政策 |

---

## 平台适配层（对接淘宝/京东等）

系统通过 `PlatformAdapter` 抽象接口隔离数据源。当前默认使用自有数据库（MockAdapter），可通过配置切换到第三方平台 API。

### 架构

```
Agent 工具 → OrderService → PlatformAdapter → 自有 MySQL（MockAdapter）
                                               淘宝 API（TaobaoAdapter）
```

### 默认行为

未配置平台 API 密钥时，自动使用 MockAdapter（查询 MySQL 订单数据），当前功能不受影响。

### 接入淘宝

1. 注册 [淘宝开放平台](https://open.taobao.com)，获取 `app_key`、`app_secret`
2. `.env` 添加：

```
TAOBAO_APP_KEY=你的key
TAOBAO_APP_SECRET=你的secret
TAOBAO_SESSION_KEY=oauth授权后的session
```

3. 安装依赖：`pip install top-sdk`
4. 填写 `src/platforms/taobao_adapter.py` 中标记 `TODO` 的 API 调用
5. 重启 → 所有订单查询自动走淘宝 API

### 扩展其他平台

实现 `PlatformAdapter` 抽象接口（9 个方法），注册到 `set_platform_adapter()` 即可：

```python
from src.platforms import PlatformAdapter, set_platform_adapter

class JingdongAdapter(PlatformAdapter):
    async def get_order(self, order_id): ...
    # ...

set_platform_adapter(JingdongAdapter())
```

---

## 上传知识库

1. 管理员登录 → 控制台 → 知识库上传
2. 选择 TXT 文件（`knowledge_docs/` 下有测试文件）
3. 选择目标集合 → 上传
4. 上传后聊天中可检索到知识库内容

---

## 故障排查

| 问题 | 检查 |
|------|------|
| Ollama 连接失败 | `OLLAMA_HOST=0.0.0.0` 启动；`.env` 用 `host.docker.internal` |
| 上传后搜索不到 | Ollama 是否已拉取 bge-m3；检查 `/health` 的 ollama 状态 |
| 前端"服务不可用" | 检查 `docker-compose logs web` 是否有 LangGraph 初始化错误 |
| 端口占用 | 修改 `docker-compose.yml` 端口映射 |
