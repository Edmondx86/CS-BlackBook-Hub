"""Web 代理实验的源服务器 —— 后端判题用（非学生答案）。

监听 ``127.0.0.1:<port>``（默认 80），对任意请求返回一个固定内容的 200 响应，
供学生写的代理服务器转发，判题据此判断代理能否正确转发请求。
"""

import argparse
import socket

HOST = "127.0.0.1"
BODY = b"PROXY_ORIGIN_HELLO"


def run_server(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, port))
        srv.listen(5)
        print(f"origin listening on {HOST}:{port}", flush=True)
        while True:
            conn, _ = srv.accept()
            with conn:
                data = conn.recv(4096)
                if not data:
                    continue
                print("received request", flush=True)
                response = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: text/html\r\n"
                    b"Content-Length: " + str(len(BODY)).encode() + b"\r\n"
                    b"Connection: close\r\n"
                    b"\r\n" + BODY
                )
                conn.sendall(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Proxy origin server")
    parser.add_argument("--port", type=int, default=80, help="监听端口")
    args = parser.parse_args()
    run_server(args.port)


if __name__ == "__main__":
    main()
