"""TCP Ping/Pong 参考服务器 —— 后端判题用（非学生答案）。

监听 ``127.0.0.1:<port>``，对每条连接：读取一行，若是 ``ping`` 回 ``pong``，
否则回 ``unknown``。打印 received/sent 供判题与前端终端展示。
"""

import argparse
import os
import socket

HOST = "127.0.0.1"


def run_server(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, port))
        srv.listen(1)
        print(f"listening on {HOST}:{port}", flush=True)
        while True:
            conn, addr = srv.accept()
            with conn:
                data = conn.recv(1024).decode(errors="replace").strip()
                print(f"received {data}", flush=True)
                reply = "pong" if data.lower() == "ping" else "unknown"
                conn.sendall(reply.encode())
                print(f"sent {reply}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="TCP ping/pong server")
    parser.add_argument("--port", type=int, default=None, help="监听端口")
    args = parser.parse_args()

    port = args.port or int(os.environ.get("PORT", "8000"))
    run_server(port)


if __name__ == "__main__":
    main()
