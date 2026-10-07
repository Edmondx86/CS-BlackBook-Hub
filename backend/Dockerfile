FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 依赖装的是完整锁定文件（含传递依赖），保证每次构建装到完全相同的版本。
# requirements.txt 是给人读的直接依赖清单，升级时改那个，再重新解析锁文件。
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY app ./app
COPY static ./static
# judge/servers/ 下是判题用的“对端”脚本（参考服务器），evaluator 按 /app/judge/servers/ 读取，
# 漏拷会导致 sock-websocket / sock-web-client / sock-smtp / sock-proxy 判题失败。
COPY judge ./judge

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
