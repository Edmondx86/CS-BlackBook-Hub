#改为Python3格式
from socket import *
import sys
import os

if len(sys.argv) <= 1:
	print('Usage : "python ProxyServer.py server_ip"\n[server_ip : It is the IP Address Of Proxy Server')
	sys.exit(2)
# TODO: 创建一个服务器套接字，绑定到一个端口并开始监听，端口的值由命令行参数提供

while 1:
	# Strat receiving data from the client
	print('Ready to serve...')
	# TODO: 接收客户端的连接请求，获取客户端套接字和地址

	print('Received a connection from:', addr)
	# TODO: 接收客户端发送的message并打印

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
		# TODO: 发送 'HTTP/1.1 200 OK\r\n' 和 'Content-Type:text/html\r\n\r\n'，然后发送缓存的内容
		print('Read from cache')
	# Error handling for file not found in cache
	except IOError:
		if fileExist == "false":
			# Create a socket on the proxyserver
			c = socket(AF_INET, SOCK_STREAM)
			hostn = filename.replace("www.","",1)
			print("hostn:", hostn)
			try:
				# Connect to the socket to port 80
				serverName = hostn.partition("/")[0]
				serverPort = 80
				print((serverName, serverPort))
				c.connect((serverName, serverPort))
				askFile = ''.join(filename.partition('/')[1:])
				print("askFile:", askFile)
				# Create a temporary file on this socket and ask port 80
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
				# TODO: 发送 'HTTP/1.1 200 OK\r\n' 和 'Content-Type:text/html\r\n\r\n'，然后发送从服务器获取的内容
				
			except:
				print("Illegal request")
			c.close()
		else:
			# HTTP response message for file not found
			print("NET ERROR")
	#TODO:关闭客户端和服务器套接字

# TODO: 关闭服务器套接字

#########################################################################