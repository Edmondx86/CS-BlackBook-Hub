# 判题沙箱镜像：只装运行 Socket/WebSocket 学生代码所需的最小依赖。
# 构建：docker build -f backend/judge/Dockerfile -t csbb-judge .
FROM python:3.12-slim

# 学生代码依赖（WebSocket 练习需要 websockets；按需追加其它纯 Python 依赖）
RUN pip install --no-cache-dir "websockets>=12"

# 非 root 用户，降低容器内权限（与 --cap-drop ALL / --read-only 叠加）
RUN useradd --create-home --uid 1000 judge
USER judge

WORKDIR /app
