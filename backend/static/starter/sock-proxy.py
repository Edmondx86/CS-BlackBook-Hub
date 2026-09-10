"""Web 代理服务器 —— 初始代码模板（请补全 handle_request）。

判题约定：通过 --port 或环境变量 PORT 读取监听端口。
"""
import argparse
import os
import socket

HOST = "127.0.0.1"


def handle_request(conn: socket.socket) -> None:
    # TODO: 1. 读取客户端发来的 HTTP 请求
    # TODO: 2. 解析目标服务器地址与端口，建立连接并转发请求
    # TODO: 3. 把目标服务器的响应转发回客户端
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Web proxy server")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    port = args.port or int(os.environ.get("PORT", "8888"))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, port))
        server.listen(5)
        print(f"Proxy listening on {HOST}:{port}", flush=True)
        while True:
            conn, _ = server.accept()
            with conn:
                handle_request(conn)


if __name__ == "__main__":
    main()
