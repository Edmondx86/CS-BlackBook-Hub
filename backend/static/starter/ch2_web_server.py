from socket import *
import os

# 监听端口从环境变量 PORT 读取：判题时会注入一个空闲端口（不固定，避免和宿主机上
# 已有的服务撞车，比如 nginx 占着的 80）。直接本地自测时用默认值 8080。
serverPort = int(os.environ.get("PORT", 8080))

# TODO: 1. 创建 TCP socket
# TODO: 2. 绑定 ("", serverPort)
# TODO: 3. 开始监听

while True:
    # Establish the connection
    print('Ready to serve...')
    connectionSocket, addr = serverSocket.accept()
    try:
        message = connectionSocket.recv(1024)
        filename = message.split()[1]
        # TODO: 1. 用 open(filename[1:]) 打开文件并读取内容
        # TODO: 2. 拼上 'HTTP/1.1 200 OK\r\n\r\n' 头后发送给客户端
        # TODO: 3. 关闭连接 connectionSocket.close()
        ...
    except IOError:
        # TODO: 发送 'HTTP/1.1 404 Not Found\r\n\r\n' 并关闭连接
        ...

