"""UDP Pinger —— Socket 编程练习初始代码模板。

判题约定：通过命令行 ``--port <N>`` 或环境变量 ``PORT`` 读取端口。
请补全缺失的 TODO 部分。

运行：
    python udp_pinger.py --role server --port 12000
    python udp_pinger.py --role client --port 12000
"""

import argparse
import os
import socket
import time

HOST = "127.0.0.1"


def run_server(port: int) -> None:
    """UDP 服务器：接收 ping 报文并回显（可随机丢包模拟）。"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind((HOST, port))
        print(f"UDP server listening on {HOST}:{port}", flush=True)
        while True:
            message, addr = server.recvfrom(1024)
            # TODO: 可选——以一定概率丢弃报文，模拟网络丢包
            server.sendto(message, addr)


def run_client(port: int) -> None:
    """UDP 客户端：发送 10 个 ping，测量 RTT 或打印超时。"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(1.0)  # 1 秒未收到响应视为超时
        for seq in range(1, 11):
            message = f"ping {seq} {time.time()}".encode()
            start = time.time()
            sock.sendto(message, (HOST, port))
            try:
                data, _ = sock.recvfrom(1024)
                rtt = time.time() - start
                print(f"seq={seq} rtt={rtt * 1000:.1f}ms reply={data.decode()}")
            except socket.timeout:
                print(f"seq={seq} Request timed out")


def main() -> None:
    parser = argparse.ArgumentParser(description="UDP Pinger")
    parser.add_argument("--role", choices=["server", "client"], required=True)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    port = args.port or int(os.environ.get("PORT", "12000"))
    if args.role == "server":
        run_server(port)
    else:
        run_client(port)


if __name__ == "__main__":
    main()
