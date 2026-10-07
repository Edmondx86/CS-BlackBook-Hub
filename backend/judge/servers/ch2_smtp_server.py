"""SMTP 参考服务器 —— 后端判题用（非学生答案）。

监听 ``127.0.0.1:<port>``，实现最小 SMTP 对话，并把每条收到的命令打印为
``received <CMD>`` 供判题判断客户端是否完成了完整对话：

  220 问候 → HELO(250) → MAIL FROM(250) → RCPT TO(250) → DATA(354) → 正文(250) → QUIT(221)
"""

import argparse
import socket

HOST = "127.0.0.1"


def run_server(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, port))
        srv.listen(5)
        print(f"listening on {HOST}:{port}", flush=True)
        while True:
            conn, _ = srv.accept()
            with conn:
                conn.sendall(b"220 localhost Simple Mail Transfer Service Ready\r\n")
                buf = b""
                in_data = False
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    buf += data

                    # DATA 阶段：一直读到正文结束标记 \r\n.\r\n
                    if in_data:
                        if b"\r\n.\r\n" in buf:
                            print("received <message>", flush=True)
                            conn.sendall(b"250 OK\r\n")
                            in_data = False
                            buf = b""
                        continue

                    # 逐行处理命令
                    while b"\r\n" in buf:
                        line, buf = buf.split(b"\r\n", 1)
                        text = line.decode(errors="replace").strip()
                        if not text:
                            continue
                        cmd = text.split()[0].upper()
                        print(f"received {cmd}", flush=True)
                        if cmd in ("HELO", "EHLO"):
                            conn.sendall(b"250 localhost\r\n")
                        elif cmd == "MAIL":
                            conn.sendall(b"250 OK\r\n")
                        elif cmd == "RCPT":
                            conn.sendall(b"250 OK\r\n")
                        elif cmd == "DATA":
                            conn.sendall(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                            in_data = True
                            break
                        elif cmd == "QUIT":
                            conn.sendall(b"221 Bye\r\n")
                            break
                        else:
                            conn.sendall(b"250 OK\r\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="SMTP reference server")
    parser.add_argument("--port", type=int, default=25, help="监听端口")
    args = parser.parse_args()
    run_server(args.port)


if __name__ == "__main__":
    main()
