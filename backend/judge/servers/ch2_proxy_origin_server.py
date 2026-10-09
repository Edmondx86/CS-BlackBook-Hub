"""Web 代理实验的源服务器 —— 后端判题用（非学生答案）。

监听 ``127.0.0.1:<port>``（默认 80），对任意请求返回一个带标记的 200 响应，
供学生写的代理服务器转发，判题据此判断代理能否正确转发请求。

响应正文是**本次判题现生成的标记**（``--marker``），不写死：写死的标记会写在公开的
实验指引里，学生可以在自己的缓存目录里先伪造一份内容、走缓存分支直接返回，一次真
转发都不做也能通过。默认值只服务于本地手工调试。
"""

import argparse
import socket

HOST = "127.0.0.1"
DEFAULT_MARKER = "PROXY_ORIGIN_HELLO"


def run_server(port: int, marker: str) -> None:
    body = marker.encode()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, port))
        srv.listen(5)
        # 只打印端口：标记是本次判题的判据，不要写进任何会被判题日志带出去的地方。
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
                    b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                    b"Connection: close\r\n"
                    b"\r\n" + body
                )
                conn.sendall(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Proxy origin server")
    parser.add_argument("--port", type=int, default=80, help="监听端口")
    parser.add_argument(
        "--marker",
        default=DEFAULT_MARKER,
        help="响应正文（本次判题随机生成；默认值仅供本地手工调试）",
    )
    args = parser.parse_args()
    run_server(args.port, args.marker)


if __name__ == "__main__":
    main()
