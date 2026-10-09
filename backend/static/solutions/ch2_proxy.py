#改为Python3格式
from socket import *
import sys
import os

if len(sys.argv) <= 1:
	print('Usage : "python ProxyServer.py proxy_port [origin_port]"\n[proxy_port  : 代理自己的监听端口]\n[origin_port : 源服务器端口，默认 8080]')
	sys.exit(2)
# Create a server socket, bind it to a port and start listening
tcpSerSock = socket(AF_INET, SOCK_STREAM)
tcpSerPort = int(sys.argv[1])
# 源服务器端口：判题时由 argv[2] 传进来（每次现分配的空闲端口，不固定 —— 避免和
# 宿主机上已有的服务撞车，比如 nginx 占着的 80）。没给就用默认值，方便本地自测。
originServerPort = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
tcpSerSock.bind(("", tcpSerPort))
print(tcpSerPort)
tcpSerSock.listen(10)
while 1:
	# Strat receiving data from the client
	print('Ready to serve...')
	tcpCliSock, addr = tcpSerSock.accept()
	print('Received a connection from:', addr)
	message = tcpCliSock.recv(1024)
	message = message.decode()
	print("message:", message)
	if(message == ''):
		continue
	# Extract the filename from the given message
	print("message.split()[1]:", message.split()[1])
	filename = message.split()[1].partition("/")[2]
	print("filename:", filename)
	fileExist = "false"
	filetouse = "/" + filename
	print("filetouse:", filetouse)
	try:
		# Check wether the file exist in the cache
		f = open("WEB/" + filetouse[1:], "rb")
		outputdata = f.read()
		f.close()
		fileExist = "true"
		# ProxyServer finds a cache hit and generates a response message
		tcpCliSock.send("HTTP/1.1 200 OK\r\n".encode())
		tcpCliSock.send("Content-Type:text/html\r\n\r\n".encode())
		tcpCliSock.send(outputdata)
		print('Read from cache')
	# Error handling for file not found in cache
	except IOError:
		if fileExist == "false":
			# Create a socket on the proxyserver
			c = socket(AF_INET, SOCK_STREAM)
			hostn = filename.replace("www.","",1)
			print("hostn:", hostn)
			try:
				# Connect to the source server (port comes from argv[2])
				serverName = hostn.partition("/")[0]
				serverPort = originServerPort
				print((serverName, serverPort))
				c.connect((serverName, serverPort))
				askFile = ''.join(filename.partition('/')[1:])
				print("askFile:", askFile)
				# Create a temporary file on this socket and ask the source server
				# for the file requested by the client
				fileobj = c.makefile('rwb', 0)
				fileobj.write("GET ".encode() + askFile.encode() + " HTTP/1.0\r\nHost: ".encode() + serverName.encode() + "\r\n\r\n".encode())
				# Read the response into buffer
				serverResponse = fileobj.read()
				# Create a new file in the cache for the requested file.
				# Also send the response in the buffer to client socket and the corresponding file in the cache
				filename = "WEB/" + filename
				filesplit = filename.split('/')
				for i in range(0, len(filesplit) - 1):
					if not os.path.exists("/".join(filesplit[0:i+1])):
						os.makedirs("/".join(filesplit[0:i+1]))
				tmpFile = open(filename, "wb")
				print(serverResponse)
				serverResponse = serverResponse.split(b'\r\n\r\n')[1]
				print(serverResponse)
				tmpFile.write(serverResponse)
				tmpFile.close()
				tcpCliSock.send("HTTP/1.1 200 OK\r\n".encode())
				tcpCliSock.send("Content-Type:text/html\r\n\r\n".encode())
				tcpCliSock.send(serverResponse)
			except:
				print("Illegal request")
			c.close()
		else:
			# HTTP response message for file not found
			print("NET ERROR")
	# Close the client and the server sockets
	tcpCliSock.close()
tcpSerSock.close()