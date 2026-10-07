# UDPPingerClient.py
from socket import *
import time
# TODO: 设置服务器 IP 和端口号

for i in range(10):
    #TODO: 设置套接字超时
    
    #TODO: 发送报文到服务器

    try:
        # TODO: 接收服务器回显报文和地址

        # TODO: 计算 RTT 并打印回显报文和 RTT

        # TODO: 打印回显报文和 RTT

    except:
        print("lost " + str(i))
