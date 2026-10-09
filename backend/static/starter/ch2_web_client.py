"""Web 客户端 —— 初始代码模板。

判题约定：
  - 判题时后端会在 127.0.0.1 起一个 HTTP 参考服务器（/hello.html 返回 200），
    端口**不固定**，通过环境变量 ``PORT`` 告诉你；
  - 你实现客户端：建立到 (127.0.0.1, PORT) 的 TCP 连接、发送 GET /hello.html、
    循环读取并打印响应。
"""

import os
from socket import *

# 端口从环境变量 PORT 读（判题时注入空闲端口）；本地自测时用默认值 8080。
serverPort = int(os.environ.get("PORT", 8080))
serverName = '127.0.0.1'
# TODO：创建客户端套接字，用TCP连接到服务器
# TODO：发送HTTP GET请求，别忘了末尾的\r\n\r\n
data = 1
while data:
    #TODO: 循环读取服务器响应并打印
    print(data.decode(), end = '')
#TODO: 关闭客户端套接字