import os
from socket import *

serverName = '127.0.0.1'
# 端口从环境变量 PORT 读取：判题时参考服务器会跑在注入的空闲端口上（不固定，
# 避免和宿主机上已有的服务撞车）；直接本地自测时用默认值 8080。
serverPort = int(os.environ.get("PORT", 8080))
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName, serverPort))
outputdata = 'GET /hello.html HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n'
clientSocket.send(outputdata.encode())
data = 1
while data:
    data = clientSocket.recv(1024)
    print(data.decode(), end = '')
clientSocket.close()
