from socket import *

# TODO: 1. 创建 TCP socket
# TODO: 2. 设置端口并绑定
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

