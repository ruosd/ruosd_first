# Vue前端

基于Vue 3 + Vite的电商客服助手前端，支持流式输出。

## 功能特性

- 🎨 现代化UI设计
- 🌊 流式响应输出
- 🤖 多Agent智能路由
- 💬 实时对话
- 📱 响应式布局

## 本地开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## Docker部署

### 方式一：使用docker-compose（推荐）

在项目根目录运行：

```bash
# 启动所有服务（包括Vue前端）
./start-docker.sh

# 或者手动启动
docker-compose up -d --build frontend-vue
```

### 方式二：单独构建Vue容器

```bash
cd frontend-vue
docker build -t ecommerce-frontend-vue .
docker run -d -p 3000:80 --name ecommerce-frontend-vue ecommerce-frontend-vue
```

## 访问地址

- Docker部署: http://localhost:3000
- 本地开发: http://localhost:3000

## API配置

在`.env`文件中配置后端API地址：

```
VITE_API_BASE=http://localhost:8000
```

## 技术栈

- Vue 3
- Vite
- Axios
- CSS3
- Nginx（生产环境）
