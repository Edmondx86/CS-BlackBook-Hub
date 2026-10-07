"""Web 客户端判题用参考服务器 —— 后端判题用（非学生答案）。

判题时由 ``evaluator.WebClientStrategy`` 以 subprocess 拉起，监听
``127.0.0.1:<port>``：对 ``/hello.html`` 返回 200，其它路径返回 404，
同时打印 ``received <path>`` 供判题判断「客户端是否发出了请求」。
"""

import argparse
import os
import socket

HOST = "127.0.0.1"

HELLO_HTML = b"""<!doctype html>
<html lang="zh">
<head><meta charset="utf-8"><title>Hello</title></head>
<body><h1>Hello from the Web Client Lab</h1><p>It works!</p></body>
</html>"""


def handle_request(conn: socket.socket) -> None:
    request = conn.recv(4096).decode(errors="replace")
    if not request:
        return
    request_line = request.splitlines()[0]
    parts = request_line.split()
    path = parts[1] if len(parts) > 1 else "/"
    path = path.split("?")[0]
    print(f"received {path}", flush=True)

    if path == "/hello.html":
        status, body = "200 OK", HELLO_HTML
    else:
        status, body = "404 Not Found", b"<h1>404 Not Found</h1>"

    response = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode() + body
    conn.sendall(response)


def run_server(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, port))
        server.listen(5)
        print(f"listening on {HOST}:{port}", flush=True)
        while True:
            conn, _ = server.accept()
            with conn:
                handle_request(conn)


def main() -> None:
    parser = argparse.ArgumentParser(description="HTTP reference server")
    parser.add_argument("--port", type=int, default=None, help="监听端口")
    args = parser.parse_args()

    port = args.port or int(os.environ.get("PORT", "12001"))
    run_server(port)


if __name__ == "__main__":
    main()
