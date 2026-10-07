# **CS-BlackBook-Hub —— 计算机黑皮书学习平台**

### 目前只实现了《计算机网络--自顶向下方法》教材的学习，其他的会陆续上线

全栈项目：FastAPI 后端 + Vue 3 前端，提供章节目录、Wireshark/Socket Lab 与在线判题。

## 目录结构

```
cs-blackbook-hub/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── main.py         # 应用入口
│   │   ├── schemas.py      # Pydantic 模型
│   │   ├── mock_data.py    # mock 数据
│   │   ├── api/            # 路由（chapters / labs）
│   │   ├── core/           # 全局配置 & 工具
│   │   └── services/       # 判题服务（evaluator）
│   ├── static/             # 静态资源（示例 web_server.py）
│   ├── Dockerfile
│   ├── .dockerignore
│   └── requirements.txt
├── frontend/               # Vue 3 + Vite + Tailwind
│   ├── src/
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   ├── .dockerignore
│   └── nginx.conf
├── docker-compose.yml
└── .gitignore
```

## 本地开发

### 后端

```bash
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload
```

接口文档：http://127.0.0.1:8000/docs

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://127.0.0.1:5173 （`/api` 已代理到后端 8000）。

## Docker 一键启动

```bash
docker compose up --build
```

- 前端：http://localhost
- 后端：http://localhost:8000/docs
