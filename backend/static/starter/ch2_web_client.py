"""Web 客户端 —— 初始代码模板。

判题约定：
  - 判题时后端会在 127.0.0.1:80 起一个 HTTP 参考服务器（/hello.html 返回 200）；
  - 你实现客户端：建立到 127.0.0.1:80 的 TCP 连接、发送 GET /hello.html、
    循环读取并打印响应。
"""

from socket import *
# TODO：设置IP和端口号
# TODO：创建客户端套接字，用TCP连接到服务器
# TODO：发送HTTP GET请求，别忘了末尾的\r\n\r\n
data = 1
while data:
    #TODO: 循环读取服务器响应并打印
    print(data.decode(), end = '')
#TODO: 关闭客户端套接字