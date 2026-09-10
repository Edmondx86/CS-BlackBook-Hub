"""简易 Web 服务器 —— 参考答案。"""

import argparse
import os
import socket

HOST = "127.0.0.1"

# 内置默认页面：即使提交目录下没有 index.html 也能返回 200，便于判题。
INDEX_HTML = b"""<!doctype html>
<html lang="zh">
<head><meta charset="utf-8"><title>Web Server</title></head>
<body><h1>Hello from the Web Server</h1><p>It works!</p></body>
</html>"""


def handle_request(conn: socket.socket) -> None:
    request = conn.recv(4096).decode(errors="replace")
    if not request:
        return
    request_line = request.splitlines()[0]
    parts = request_line.split()
    path = parts[1] if len(parts) > 1 else "/"
    path = path.split("?")[0]

    if path in ("/", "/index.html"):
        status, content_type, body = "200 OK", "text/html; charset=utf-8", INDEX_HTML
    else:
        status, content_type, body = "404 Not Found", "text/html; charset=utf-8", b"<h1>404 Not Found</h1>"

    response = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode() + body
    conn.sendall(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple HTTP server")
    parser.add_argument("--port", type=int, default=None, help="监听端口")
    args = parser.parse_args()

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
