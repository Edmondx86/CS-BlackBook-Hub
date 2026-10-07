# <span style="color: rgb(var(--brand));">Socket 编程：在线沙盒</span>

理论学得再多，不亲手写一次 Socket，永远是“纸上谈兵”。这个工具是本站的**在线编程沙盒**——不需要在本地装任何环境，直接在浏览器里写 Python 代码、点“运行测试”，后端就会在隔离沙箱里把你的代码真正跑起来，并把运行结果、服务器的响应都回显到终端里。**即写即测、边学边练**。

## <span style="color: rgb(var(--brand-dark));">Socket 是什么：进程之间的“门”</span>

简单回顾第二章的知识：应用进程之间要通信，不能把数据“顺窗户撇出去”，必须通过 **Socket（套接字）** 这个接口来收发。Socket 是应用层与传输层之间的**编程接口（API）**，你只需调用它提供的函数，数据就会在网络上跑起来，底层的 IP、路由这些细节由操作系统代劳。

因为传输层有 UDP、TCP 两位主角，Socket 编程也分两大流派：

| | UDP Socket | TCP Socket |
| --- | --- | --- |
| 连接方式 | 无连接，直接发 | 面向连接，先握手 |
| 关键函数 | `sendto()` / `recvfrom()` | `connect()` / `accept()` + `read()`/`write()` |
| 传输单位 | 数据报（有边界） | 字节流（无边界） |
| 特点 | 快、简单、不保证送达 | 可靠、有序、不丢 |
| 典型场景 | 实时语音、游戏、DNS | 网页、邮件、文件传输 |

> 打个比方：**UDP 像寄明信片**（写上地址直接扔，不问到没到）；**TCP 像打电话**（先拨号接通，再一句句聊）。选哪个，看你“更怕慢”还是“更怕错”。

## <span style="color: rgb(var(--brand-dark));">怎么用：三步跑通一个程序</span>

1. **进入实验**：从首页“常见工具”或章节页的 Socket 练习区，选一个实验（如“UDP Pinger 客户端”）。
2. **写代码**：在编辑器里补全 TODO 部分——每个实验的 starter 代码都搭好了骨架，只留关键的几处让你实现。
3. **运行测试**：点“运行测试”，后端在沙箱里启动参考服务器、跑起你的代码，把**你的输出 + 服务器的响应**一起显示在终端里，并给出评测结果。

以 UDP Pinger 为例，跑通后终端里大概会看到：

```text
ping 1  ->  reply: ping 1  (rtt=1.2ms)
ping 2  ->  reply: ping 2  (rtt=0.9ms)
ping 3  ->  reply: ping 3  (rtt=1.1ms)
...
```

这里学生写的是**客户端**，后端在沙箱里跑一个**参考服务器**——你 ping 过去，服务器回显，你再把往返结果打印出来。一次完整的客户端 ↔ 服务器通信就在你手里跑通了。

## <span style="color: rgb(var(--brand-dark));">能做哪些实验</span>

| 章节 | Socket 实验 |
| --- | --- |
| 第 1 章 网络基础 | Ping 命令引导 |
| 第 2 章 应用层 | 简易 Web 服务器、Web 客户端、UDP Pinger 客户端、UDP Pinger 服务器、SMTP 邮件客户端、Web 代理服务器 |
| 第 5 章 网络层控制平面 | ICMP Ping 客户端 |

这些实验基本覆盖了《自顶向下》里 Socket 编程的经典作业（Web Server、UDP Pinger、SMTP、Proxy、ICMP Ping），从应用层的字节流，一路练到网络层的 ICMP 报文构造。

## <span style="color: rgb(var(--brand-dark));">Python Socket 速查</span>

```python
import socket

# —— UDP 客户端 ——
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(b"ping 1", (host, port))
data, addr = s.recvfrom(1024)

# —— UDP 服务器 ——
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((host, port))
data, addr = s.recvfrom(1024)
s.sendto(data, addr)          # 原样回显

# —— TCP 服务器 ——
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((host, port))
s.listen(1)
conn, addr = s.accept()       # 三次握手后建立连接
data = conn.recv(1024)
conn.sendall(data)

# —— TCP 客户端 ——
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))       # 发起三次握手
s.sendall(b"GET / HTTP/1.1\r\n")
data = s.recv(4096)
```

> **初学提示**：先从 UDP 入手——它没有连接、没有边界问题，代码最短；吃透 UDP 之后，再去啃 TCP 的“握手 + 字节流边界”这两块硬骨头。
