# 对代码进行了少部分改动

import socket
import os
import sys
import struct
import time
import select
import binascii

ICMP_ECHO_REQUEST = 8


def checksum(strCheck):
    csum = 0
    countTo = (len(strCheck) / 2) * 2
    count = 0
    while count < countTo:
        thisVal = strCheck[count + 1] * 256 + strCheck[count]
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2

    if countTo < len(strCheck):
        csum = csum + strCheck[len(strCheck) - 1]
        csum = csum & 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:  # Timeout
            return "Request timed out."

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        header = recPacket[20:28]
        header_type, header_code, header_checksum, header_packet_ID, header_sequence = struct.unpack("bbHHh", header)

        if(header_type != 0 or header_code != 0 or header_packet_ID != ID or header_sequence != 1):
            return "Receive error."

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."
        return 1 - timeLeft


def sendOnePing(mySocket, destAddr, ID):
    #TODO: 需要构造ICMP报文并发送
    pass


def doOnePing(destAddr, timeout):
    #TODO: 需要创建原始套接字，发送ICMP报文并接收响应
    pass


def ping(host, timeout=1):
    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client’s ping or the server’s pong is lost
    # timeout = 1 表示：如果一秒钟没有收到服务器的答复，则客户端会认为客户端的ping或服务器的pong丢失了
    dest = socket.gethostbyname(host)
    print("正在 Ping", host, "[", dest, "] :")
    # Send ping requests to a server separated by approximately one second
    # 将ping请求发送到间隔约一秒钟的服务器
    num = 4
    lost = 0
    delayList = []
    for i in range(num):
        delay = doOnePing(dest, timeout)
        if(type(delay) == str):
            print(delay)
            lost = lost + 1
            continue
        delay = int(delay * 1000)
        delayList.append(delay)
        print("来自", dest, "的回复: 时间=", delay, "ms")
        time.sleep(1)  # one second
    print(dest, "的 Ping 统计信息:")
    print("\t数据包: 已发送 =", num, "，已接收 =", num - lost, "，丢失 =", lost, "(", lost/num * 100, "% 丢失)")
    if(delayList):
        print("往返行程的估计时间(以毫秒为单位):")
        print("\t最短 =", min(delayList), "ms，最长 =", max(delayList), "ms，平均 =", sum(delayList)/len(delayList), "ms")

ping("qq.com")