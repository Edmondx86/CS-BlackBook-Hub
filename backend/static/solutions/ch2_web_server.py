#import socket module
import os
from socket import *
serverSocket = socket(AF_INET, SOCK_STREAM)
#Prepare a sever socket
# 监听端口从环境变量 PORT 读取：判题时会注入一个空闲端口，避免和宿主机上已有的服务
# （比如 nginx 占着的 80）撞车；直接本地自测时用默认值 8080。
serverPort = int(os.environ.get("PORT", 8080))
serverSocket.bind(("", serverPort))
serverSocket.listen(1)
while True:
    #Establish the connection
    print('Ready to serve...')
    connectionSocket, addr = serverSocket.accept()
    try:
        message = connectionSocket.recv(1024)
        filename = message.split()[1]
        f = open(filename[1:])
        outputdata = f.read()
        f.close()
        #Send one HTTP header line into socket
        outputdata = 'HTTP/1.1 200 OK\r\n\r\n' + outputdata
        #Send the content of the requested file to the client
        for i in range(0, len(outputdata)):
            connectionSocket.send(outputdata[i].encode())
        connectionSocket.close()
        print("OK!")
    except IOError:
        #Send response message for file not found
        outputdata = 'HTTP/1.1 404 Not Found\r\n\r\n'
        #Close client socket
        for i in range(0, len(outputdata)):
            connectionSocket.send(outputdata[i].encode())
        connectionSocket.close()
serverSocket.close()