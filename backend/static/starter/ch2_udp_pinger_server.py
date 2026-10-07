import argparse
import random
from socket import *

parser = argparse.ArgumentParser(description="UDP Pinger server")
parser.add_argument("--port", type=int, default=12000, help="监听端口")
args = parser.parse_args()

random.seed(42)

# TODO: 创建 UDP 套接字

while True:
    # Generate random number in the range of 0 to 10
    rand = random.randint(0, 10)
    # TODO:从客户端接收报文和地址

    # TODO: 将客户端报文转大写
    
    # If rand is less is than 4, we consider the packet lost and do not respond
    if rand < 4:
        continue
    # Otherwise, the server responds
    # TODO: 将大写报文回显给客户端

    ###############################################
