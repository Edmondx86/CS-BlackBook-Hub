"""简易 Web 服务器 —— 初始代码模板（请补全 handle_request）。

判题约定：程序必须通过命令行 ``--port <N>`` 或环境变量 ``PORT`` 读取监听端口。

要求：
  - 请求 ``/`` 或 ``/index.html`` 时返回 ``200 OK``
  - 其它路径返回 ``404 Not Found``
"""

import argparse
import os
import socket

HOST = "127.0.0.1"


def handle_request(conn: socket.socket) -> None:
    """处理一次 HTTP 请求并写回响应。"""
    # TODO: 1. 用 conn.recv() 读取请求，解析出请求路径
    # TODO: 2. 根据路径决定状态码：/ 与 /index.html -> 200，其它 -> 404
    # TODO: 3. 组装响应（状态行 + Content-Length + 空行 + Body）并 conn.sendall()
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple HTTP server")
    parser.add_argument("--port", type=int, default=None, help="监听端口")
    args = parser.parse_args()

    # 优先命令行参数，其次环境变量 PORT，最后回退默认端口
    port = args.port or int(os.environ.get("PORT", "6789"))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, port))
        server.listen(5)
        print(f"Listening on {HOST}:{port}", flush=True)

        while True:
            conn, _ = server.accept()
            with conn:
                handle_request(conn)


if __name__ == "__main__":
    main()
