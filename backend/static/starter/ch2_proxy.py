#改为Python3格式
from socket import *
import sys
import os
import tempfile

if len(sys.argv) <= 1:
	print('Usage : "python ProxyServer.py proxy_port [origin_port]"\n[proxy_port  : 代理自己的监听端口]\n[origin_port : 源服务器端口，默认 8080]')
	sys.exit(2)
# 代理自己的监听端口：argv[1]（判题时是现分配的空闲端口）
proxyPort = int(sys.argv[1])
# 源服务器端口：argv[2]（判题时同样是现分配的空闲端口，不固定 —— 避免和宿主机上
# 已有的服务撞车，比如 nginx 占着的 80）。没给就用默认值，方便本地自测。
originServerPort = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
# 缓存目录必须放在临时目录下：判题沙箱里只有临时目录可写（工作目录是只读挂载的），
# 写相对路径 "WEB/..." 会直接 OSError 失败。
cacheRoot = os.path.join(tempfile.gettempdir(), "WEB")

# TODO: 创建一个服务器套接字，绑定到 ("", proxyPort) 并开始监听

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
		f = open(os.path.join(cacheRoot, *filetouse[1:].split("/")), "rb")
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
				# 同样写到临时目录（沙箱里唯一可写的地方），并用 os.makedirs 补出子目录。
				filename = os.path.join(cacheRoot, *filename.split("/"))
				if not os.path.exists(os.path.dirname(filename)):
					os.makedirs(os.path.dirname(filename))
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