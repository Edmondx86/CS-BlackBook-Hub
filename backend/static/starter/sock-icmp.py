"""ICMP Ping 客户端 —— 初始代码模板（请补全）。

判题约定：通过 --host 指定目标；使用原始套接字发送 ICMP Echo Request。
注意：原始套接字通常需要管理员/root 权限。
"""
import argparse
import os
import socket
import struct


def checksum(data: bytes) -> int:
    # TODO: 计算 ICMP 校验和（16 位反码和）
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="ICMP ping client")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    # TODO: 1. 创建原始套接字 socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)
    # TODO: 2. 构造 ICMP Echo Request 报文（含校验和）
    # TODO: 3. 发送并接收 Echo Reply，计算 RTT


if __name__ == "__main__":
    main()
