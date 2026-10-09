import os
from socket import *

msg = "\r\n I love computer networks!"
endmsg = "\r\n.\r\n"

# Choose a mail server and call it mailserver
# 端口从环境变量 PORT 读取：判题时参考 SMTP 服务器跑在注入的空闲端口上（不固定。
# 25 是特权端口，Linux 上非 root 用户绑不了，所以这里不能写死 25）。本地自测默认 2500。
mailserver = ("127.0.0.1", int(os.environ.get("PORT", 2500)))

# Create socket called clientSocket and establish a TCP connection with mailserver
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect(mailserver)

recv = clientSocket.recv(1024).decode()
print(recv)
if recv[:3] != '220':
    print('220 reply not received from server.')

# Send HELO command and print server response.
heloCommand = 'HELO Alice\r\n'
clientSocket.send(heloCommand.encode())
recv1 = clientSocket.recv(1024).decode()
print(recv1)
if recv1[:3] != '250':
    print('250 reply not received from server.')

# Send MAIL FROM command and print server response.
mailFromCommand = 'MAIL FROM: <alice@crepes.fr>\r\n'
clientSocket.send(mailFromCommand.encode())
recv2 = clientSocket.recv(1024).decode()
print(recv2)

# Send RCPT TO command and print server response.
rcptToCommand = 'RCPT TO: <bob@hamburger.edu>\r\n'
clientSocket.send(rcptToCommand.encode())
recv3 = clientSocket.recv(1024).decode()
print(recv3)

# Send DATA command and print server response.
dataCommand = 'DATA\r\n'
clientSocket.send(dataCommand.encode())
recv4 = clientSocket.recv(1024).decode()
print(recv4)

# Send message data.
clientSocket.send(msg.encode())

# Message ends with a single period.
clientSocket.send(endmsg.encode())
recv5 = clientSocket.recv(1024).decode()
print(recv5)

# Send QUIT command and get server response.
quitCommand = 'QUIT\r\n'
clientSocket.send(quitCommand.encode())
recv6 = clientSocket.recv(1024).decode()
print(recv6)

clientSocket.close()
