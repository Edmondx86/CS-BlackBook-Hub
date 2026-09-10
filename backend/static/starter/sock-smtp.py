"""SMTP 邮件客户端 —— 初始代码模板（请补全 main）。

判题约定：通过 --host / --port（或环境变量 PORT）读取连接参数。
"""
import argparse
import os
import socket


def main() -> None:
    parser = argparse.ArgumentParser(description="SMTP client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    port = args.port or int(os.environ.get("PORT", "25"))

    # TODO: 1. 连接 SMTP 服务器，读取 220 欢迎信息
    # TODO: 2. 依次发送 HELO / MAIL FROM / RCPT TO / DATA / QUIT 命令
    # TODO: 3. 每步读取并校验服务器响应码（220 / 250 / 354 / 221）


if __name__ == "__main__":
    main()
