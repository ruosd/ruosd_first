# 贡献指南

感谢你对本项目的关注！以下是参与贡献的流程。

## 环境准备

1. **Fork 本仓库**，然后 clone 到本地
2. 安装前置依赖：Docker Desktop、Ollama（拉取 bge-m3 模型）
3. 复制 `.env.example` → `.env`，填入你的阿里云百炼 API Key
4. 运行 `docker-compose up -d --build` 启动全部服务
5. 访问 `http://localhost:3000` 确认运行正常

## 本地开发

```bash
# 后端（需要 Python 3.10+）
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 前端
cd frontend-vue
npm install
npm run dev
```

## 代码规范

- **Python**: [ruff](https://docs.astral.sh/ruff/) — `ruff check src/ && ruff format src/`
- **Vue**: [Prettier](https://prettier.io/) — `npx prettier --write frontend-vue/src/`
- 禁止裸 `print()`，使用 `logger = get_logger("name")`
- 提交前运行 `pytest tests/ -v`

## Pull Request 流程

1. 创建 feature 分支：`git checkout -b feature/your-feature`
2. 编写代码 + 测试
3. 运行 `ruff check src/ && pytest tests/ -v`
4. 提交并推送，创建 PR 到 `main` 分支
5. 在 PR 描述中说明改动目的和测试方式

## 项目结构

```
src/
├── agents/       # Agent 模块（Order/Product/CS）
├── services/     # 业务逻辑层
├── routers/      # FastAPI 路由
├── models/       # Pydantic 数据模型
├── graph/        # LangGraph 编排
├── platforms/    # 平台适配层
├── tasks/        # Celery 异步任务
└── utils/        # 工具函数

tests/            # 测试
frontend-vue/     # Vue3 前端
```

## 测试说明

| 测试类型 | 命令 |
|----------|------|
| 全部测试 | `pytest tests/ -v` |
| 覆盖率 | `pytest tests/ --cov=src --cov-report=term-missing` |
| 单个文件 | `pytest tests/test_api.py -v` |

## License

MIT — 详见 [LICENSE](LICENSE)
