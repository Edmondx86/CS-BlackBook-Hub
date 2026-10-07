"""Mock 数据：用《自顶向下》前两章演示完整数据结构与接口。

生产环境中这些数据应来自数据库或磁盘文件；这里为保持轻量，直接以内联
方式给出，并在模块底部构建 ``LAB_INDEX`` 供章节下的 lab 路由做 O(1) 查询。
"""

from __future__ import annotations

from pathlib import Path

from .schemas import (
    Attachment,
    Chapter,
    KnowledgePoint,
    Lab,
    SocketExercise,
    TestCase,
    WiresharkLab,
)

# --------------------------------------------------------------------------
# 静态文件读取（初始代码 / 文档路径）
# --------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_STARTER_DIR = _STATIC_DIR / "starter"
_SOLUTIONS_DIR = _STATIC_DIR / "solutions"

# 每个 Socket 练习对应的作业要求文档（PDF），统一放在 backend/static/docs/ 下
DOCUMENTS: dict[str, str] = {
    "sock-web": "/static/docs/web_server.pdf",
    "sock-pinger": "/static/docs/udp_pinger.pdf",
    # Wireshark 实验
    "ws-http": "/static/docs/ws-http.pdf",
    "ws-dns": "/static/docs/ws-dns.pdf",
    "ws-tcp": "/static/docs/ws-tcp.pdf",
    "ws-udp": "/static/docs/ws-udp.pdf",
    "ws-ip": "/static/docs/ws-ip.pdf",
    "ws-icmp": "/static/docs/ws-icmp.pdf",
    "ws-dhcp": "/static/docs/ws-dhcp.pdf",
    "ws-nat": "/static/docs/ws-nat.pdf",
    "ws-ethernet-arp": "/static/docs/ws-ethernet-arp.pdf",
    "ws-80211": "/static/docs/ws-80211.pdf",
    "ws-ssl": "/static/docs/ws-ssl.pdf",
    # Socket 练习
    "sock-smtp": "/static/docs/sock-smtp.pdf",
    "sock-proxy": "/static/docs/sock-proxy.pdf",
    "sock-icmp": "/static/docs/sock-icmp.pdf",
}


def _read_starter(filename: str) -> str:
    """读取初始代码模板内容，文件缺失时返回空串。"""
    p = _STARTER_DIR / filename
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _read_solution(filename: str) -> str:
    """读取参考答案内容，文件缺失时返回空串。"""
    p = _SOLUTIONS_DIR / filename
    return p.read_text(encoding="utf-8") if p.exists() else ""


# --------------------------------------------------------------------------
# Socket 练习的“判题对端”参考实现：有的放在 static/solutions/，有的放在 judge/servers/，
# 两个目录都要找；文件缺失时返回空串，前端会自动隐藏“参考服务器代码”入口。
# --------------------------------------------------------------------------

_JUDGE_SERVERS_DIR = Path(__file__).resolve().parent.parent / "judge" / "servers"
_SERVER_CODE_DIRS = (_SOLUTIONS_DIR, _JUDGE_SERVERS_DIR)

# 个别对端脚本的文件名不符合 <starter文件名>_server.py 的约定，在这里单独登记。
_SERVER_SCRIPT_OVERRIDES: dict[str, str] = {
    "sock-proxy": "ch2_proxy_origin_server.py",
}


def _read_server_code(lab_id: str, starter_code_path: str) -> str:
    """按 lab_id 读取参考服务器代码，solutions/ 与 judge/servers/ 都找不到时返回空串。"""
    filename = _SERVER_SCRIPT_OVERRIDES.get(lab_id) or starter_code_path.rsplit("/", 1)[-1].replace(
        ".py", "_server.py"
    )
    for directory in _SERVER_CODE_DIRS:
        p = directory / filename
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


_BACKEND_DIR = Path(__file__).resolve().parent.parent


def _file_exists(rel_path: str) -> bool:
    """判断 ``static/...`` 这类相对 backend/ 的路径是否真实存在。"""
    return (_BACKEND_DIR / rel_path).exists()


def _document_path(lab_id: str) -> str | None:
    """作业要求 PDF 的访问路径；文件不在磁盘上时返回 ``None``。

    为什么要有这个判断：这些 PDF 每个 2 MB 上下（11 个实验文档合计约 24 MB），
    **不进版本库**（见 backend/static/docs/README.md），由部署时单独上传。
    在只 clone 了仓库、还没传 PDF 的机器上，接口就不能再吐一个必然 404 的链接 ——
    返回 None，前端自然不渲染 PDF 区块，而不是给用户一个加载失败的面板。
    """
    rel = DOCUMENTS.get(lab_id)
    if not rel:
        return None
    # DOCUMENTS 里存的是 URL 形式（以 / 开头），而 _file_exists 要的是相对 backend/ 的路径
    return rel if _file_exists(rel.lstrip("/")) else None


# --------------------------------------------------------------------------
# Markdown 指南内容（mock）。真实实现可从 guide_path 指向的磁盘文件读取。
# --------------------------------------------------------------------------

GUIDES: dict[str, str] = {
    "ws-intro": """# Wireshark 入门实验

> 对应教材 **Chapter 1**「Computer Networks and the Internet」。
## 实验介绍

如果你想加深自己对计算机网络的理解，那么自己动手操作是再好不过的方式了。
用来观察执行协议的实体之间交换的报文的基本工具称为**分组嗅探器**（packet sniffer）。顾名思义，分组嗅探器可以捕获网络中传输的分组，并将其显示出来。Wireshark 是一个非常流行的分组嗅探器，它可以捕获网络中传输的分组，并将其显示出来，帮助我们理解网络协议的工作原理。
最重要的是，Wireshark是免费的喔。

## 实验目标

1. 熟悉 Wireshark 的抓包界面与基本过滤操作。
2. 捕获并检查你的Web浏览器和Web服务器之间交换的协议报文。

## 实验步骤

1. 下载并安装Wireshark，链接在此（https://www.wireshark.org/download.html）。
2. 访问一个浏览器站点（例如 http://www.example.com），并在Wireshark中查看信息格式和内容。
3. 在Wireshark中使用过滤器过滤HTTP流量，观察HTTP请求和响应报文的结构和内容。
4. 记录你观察到的HTTP请求方法、状态码、头字段等信息。

### 2. 观察 HTTP 请求

1. 选中一条 `GET / HTTP/1.1` 报文。
2. 在「Packet Details」面板展开 `Hypertext Transfer Protocol` 层，记录：
   - 请求方法（Request Method）
   - Host 头字段
   - User-Agent 头字段

## 思考

1. HTTP 属于什么层的协议？
2. HTTP 请求报文的结构是怎样的？包括哪些部分？
""",
    "ws-http": """# HTTP 协议实验

> 对应教材 **Chapter 2**「Application Layer」。

## 实验目标

1. 掌握 HTTP/1.1 请求与响应报文结构。
2. 理解持久连接（Keep-Alive）与条件 GET（Conditional GET）。
3. 观察浏览器缓存对网络行为的影响。

## 实验材料

- 抓包文件：`http.pcap`（见附件）

## 实验步骤

1. 打开 `http.pcap`，过滤 `http`。
2. 找到第一条 GET 请求，记录请求行与首部字段。
3. 检查响应状态码，确认是否 `200 OK`。
4. 观察是否存在 `If-Modified-Since` 头，分析条件 GET 的往返。

## 思考题

1. 浏览器与服务器之间的连接在响应后是否关闭？依据是什么？
2. 什么是「条件 GET」？它如何减少带宽占用？
""",
    "sock-web": """# Socket 编程练习：简易 Web 服务器

> 对应教材 **Chapter 2**「Application Layer」2.7 节。

## 任务

使用 Python 的 `socket` 模块实现一个单线程 HTTP 服务器：

1. 监听 `80` 端口，循环接受连接。
2. 从请求行解析出文件名，打开对应文件。
3. 文件存在则返回 `200 OK` 及文件内容；打开失败（`IOError`）则返回 `404 Not Found`。

## 初始代码

见编辑器，补全TODO。

## 判题

点击「运行测试」后，判题程序会起你的服务器、分别请求 `/index.html`（期望 200）与
`/missing.html`（期望 404），并比对返回的状态码。

""",
    "sock-web-client": """# Socket 编程练习：Web 客户端

> 对应教材 **Chapter 2**「Application Layer」2.7 节。

## 任务

模仿浏览器，写一个 TCP 客户端：向 `127.0.0.1:80` 的参考服务器发出 HTTP 请求，并打印响应。具体步骤：

1. 建立到 `127.0.0.1:80` 的 TCP 连接（教材示例写法，端口硬编码为 80）。
2. 发送 `GET /hello.html HTTP/1.1` 请求（记得带 `Host` 头和结尾空行）。
3. 循环读取并打印服务器返回的响应，直到连接关闭。

## 判题

点击「运行测试」后，判题程序会在 80 端口起参考服务器、运行你的客户端，并检查：
- 服务器是否收到了 `/hello.html` 请求；
- 你的客户端是否打印了 `200 OK` 状态行。

""",
    "sock-pinger": """# Socket 编程练习：UDP Pinger 客户端

> 对应教材 **Chapter 2**「Application Layer」2.7 节。

## 任务

判题时后端会拉起一个 UDP 回显服务器（收到报文后转大写并回显），监听端口通过
`--port` 传入你的客户端（本地直接运行默认 `12000`）。你只需实现**客户端**：

1. 向 `127.0.0.1:<port>` 发送 ping 报文（内容如 `Ping 1 <时间戳>`）。
2. 循环发送 10 个 ping，每次设置 1 秒超时。
3. 收到回显则打印「回显 + RTT」，超时则打印 `lost`。

## 初始代码

见编辑器中的 `ch2_udp_pinger.py`，补全 `run_client` 里的 TODO（端口已由 `--port` 解析好）。

## 判题

点击「运行测试」后，判题程序会起参考服务器、运行你的客户端，并检查：
- 服务器是否收到了你的 ping 报文；
- 你的客户端是否打印了回显（含 `RTT`）。

## 提示

点击编辑器右上角的「提示」按钮可以逐级查看解题提示（最后才是参考答案）。

## 提交要求

提交源码并附上客户端运行截图。
""",
    "sock-pinger-server": """# Socket 编程练习：UDP Pinger 服务器

> 对应教材 **Chapter 2**「Application Layer」2.7 节。

## 任务

实现一个 UDP Pinger **服务器**：

1. 通过 `--port` 参数读取监听端口，创建 UDP 套接字并绑定。
2. 循环接收客户端的 ping 报文。
3. 将报文**转大写**后回显。
4. 模拟网络丢包：以约 4/11 的概率丢弃报文（用 `random.seed(42)` 保证可复现）。

## 初始代码

见编辑器中的 `ch2_udp_pinger_server.py`，补全 TODO。

## 判题

点击「运行测试」后，判题程序会以 UDP 客户端身份连上你的服务器、发若干 ping，并检查：
- 服务器能响应（至少 3 次回显）；
- 回显内容正确转大写。

## 提交要求

提交源码并附上运行截图。
""",
    "sock-websocket": """# 第一章引导：Ping 命令

> 认识「ping 指令」与「客户端 ↔ 服务器」通信。

## 做什么

在编辑器里输入一条 ping 命令，例如：

    ping 127.0.0.1:8000

然后点击「运行测试」。后端会在沙箱里拉起一个服务器，替你发出 `ping`，服务器回一个 `pong`。

## 你会看到

- 终端显示服务器收到的报文与回显；
- 若成功，显示 `pong，恭喜你成功通过测试`。

## 想一想

1. `ping` 里的 `127.0.0.1` 是什么？`8000` 又是什么？
2. 是谁在「发 ping」，谁在「回 pong」？
""",
    "ws-dns": """# DNS 协议实验

> 对应教材 **Chapter 2**「Application Layer」。

使用 Wireshark 观察 DNS 查询与响应报文，理解域名解析过程。详细实验步骤见下方「作业要求文档」（PDF）。
""",
    "ws-tcp": """# TCP 协议实验

> 对应教材 **Chapter 3**「Transport Layer」。

使用 Wireshark 观察 TCP 三次握手、可靠传输与拥塞控制。详细实验步骤见「作业要求文档」（PDF）。
""",
    "ws-udp": """# UDP 协议实验

> 对应教材 **Chapter 3**「Transport Layer」。

使用 Wireshark 观察 UDP 报文结构与无连接传输特性。详细实验步骤见「作业要求文档」（PDF）。
""",
    "ws-ip": """# IP 协议实验

> 对应教材 **Chapter 4**「Network Layer」。

使用 Wireshark 观察 IP 数据报头部字段与分片。详细实验步骤见「作业要求文档」（PDF）。
""",
    "ws-icmp": """# ICMP 协议实验

> 对应教材 **Chapter 5**「Network Layer: Control Plane」5.6 节。

使用 Wireshark 观察 ICMP 差错报告与 Ping/Traceroute 报文。详细实验步骤见「作业要求文档」（PDF）。
""",
    "ws-dhcp": """# DHCP 协议实验

> 对应教材 **Chapter 4**「Network Layer」。

使用 Wireshark 观察 DHCP 发现/提供/请求/确认四步过程。详细实验步骤见「作业要求文档」（PDF）。
""",
    "ws-nat": """# NAT 实验

> 对应教材 **Chapter 4**「Network Layer」。

使用 Wireshark 观察 NAT 对内外网地址的转换。详细实验步骤见「作业要求文档」（PDF）。
""",
    "ws-ethernet-arp": """# 以太网与 ARP 实验

> 对应教材 **Chapter 6**「The Link Layer and LANs」。

使用 Wireshark 观察以太网帧结构与 ARP 地址解析过程。详细实验步骤见「作业要求文档」（PDF）。
""",
    "ws-80211": """# 802.11 无线局域网实验

> 对应教材 **Chapter 7**「Wireless and Mobile Networks」。

使用 Wireshark 观察 802.11 帧结构与无线局域网通信。详细实验步骤见「作业要求文档」（PDF）。
""",
    "ws-ssl": """# SSL 安全实验

> 对应教材 **Chapter 8**「Security」。

使用 Wireshark 观察 SSL/TLS 握手与加密通信。详细实验步骤见「作业要求文档」（PDF）。
""",
    "sock-smtp": """# Socket 编程练习：SMTP 邮件客户端

> 对应教材 **Chapter 2**「Application Layer」2.7 节。

实现一个 SMTP 客户端，通过 socket 连接邮件服务器并完成邮件投递。详细要求见「作业要求文档」（PDF）。
""",
    "sock-proxy": """# Socket 编程练习：Web 代理服务器

> 对应教材 **Chapter 2**「Application Layer」2.7 节。

实现一个 Web 代理服务器，转发客户端 HTTP 请求。详细要求见「作业要求文档」（PDF）。
""",
    "sock-icmp": """# Socket 编程练习：ICMP Ping 客户端

> 对应教材 **Chapter 5**「Network Layer: Control Plane」5.6 节。

## 任务

用 Python 的 `socket` 模块实现一个 ICMP Ping 客户端，通过**原始套接字**（raw socket）
发送 ICMP Echo Request（类型 8）并测量往返时间 RTT。你需要补全初始代码中的 `sendOnePing`
与 `doOnePing` 两处 TODO：

1. 构造 ICMP Echo Request 报文头（type=8、code=0、checksum、id、sequence），并计算校验和。
2. 创建原始套接字 `socket(AF_INET, SOCK_RAW, getprotobyname("icmp"))`，发送报文并接收 Echo Reply。

## 初始代码

见编辑器中的 `ch5_icmp.py`，补全 TODO。

## 判题

点击「运行测试」后，判题程序会对你的代码做**静态校验**：检查是否创建了原始套接字、
是否正确构造了 ICMP 报文头与校验和、是否完成了收发逻辑，并校验 `checksum` 函数的输出
与参考答案一致。

## 提示

> 原始套接字需要管理员 / root 权限才能真实发送 ICMP 报文，因此本练习的判题不实际发包，
> 而是静态检查代码结构；本地自测时请以管理员身份运行。

## 提交要求

提交源码并附上客户端运行截图。
""",
}

# --------------------------------------------------------------------------
# 分级提示（前端「提示」按钮逐级揭示；下标顺序即揭示顺序，最后一步之前都是引导）
# --------------------------------------------------------------------------

HINTS: dict[str, list[str]] = {
    "sock-pinger": [
        "先建一个 UDP socket：`socket.socket(socket.AF_INET, socket.SOCK_DGRAM)`，并用 `sock.settimeout(1.0)` 设 1 秒接收超时。",
        "发送前记录 `time1 = time.time()`，把 `f\"Ping {i} {time1}\".encode()` 用 `sock.sendto(data, (SERVER_NAME, port))` 发出去。",
        "用 `sock.recvfrom(2048)` 收回显（返回 `(data, addr)`），`RTT = time.time() - time1`；捕获 `socket.timeout` 并打印 `lost`。",
    ],
    "sock-web-client": [
        "用 `socket.socket(socket.AF_INET, socket.SOCK_STREAM)` 建 TCP socket，然后 `connect((SERVER_NAME, port))`。",
        "构造请求 `f\"GET {path} HTTP/1.1\\r\\nHost: {SERVER_NAME}\\r\\nConnection: close\\r\\n\\r\\n\"`，用 `send()` 发出。",
        "循环 `recv(4096)` 直到返回空串（表示连接已关闭），每段都用 `print(..., end='')` 打印。",
    ],
    "sock-web": [
        "建 TCP socket：`socket(AF_INET, SOCK_STREAM)`，`bind(('', 80))`，`listen(1)`，然后循环 `accept()`。",
        "`recv(1024)` 读请求，用 `message.split()[1]` 取出文件名，`open(filename[1:])` 打开并 `read()` 内容。",
        "文件存在就发 `HTTP/1.1 200 OK` + 内容；`IOError` 则发 `HTTP/1.1 404 Not Found`，最后 `connectionSocket.close()`。",
    ],
    "sock-pinger-server": [
        "建 UDP socket：`socket(AF_INET, SOCK_DGRAM)`，`bind(('', 12000))`，并用 `random.seed(42)` 固定丢包模式。",
        "循环 `recvfrom(1024)` 收报文和地址，用 `message.upper()` 转大写。",
        "`rand = random.randint(0, 10)`，若 `rand < 4` 就 `continue` 丢包，否则 `sendto(message, address)` 回显。",
    ],
    "sock-smtp": [
        "建 TCP socket，`connect(('127.0.0.1', 25))`，先收 `220` 问候。",
        "依次 `send` 并 `recv`：`HELO`、`MAIL FROM`、`RCPT TO`、`DATA`，每步收响应。",
        "发送正文 + `\\r\\n.\\r\\n`，再发 `QUIT`，每次收响应并打印。",
    ],
    "sock-proxy": [
        "从 `sys.argv[1]` 读端口，建 TCP socket，`bind(('', port))` + `listen`，循环 `accept()`。",
        "`recv(1024)` 读请求，用 `message.split()[1].partition('/')[2]` 取出文件名。",
        "先查 `WEB/` 缓存；未命中则连源服务器（80 端口）取内容、写缓存，再把 `200 OK` 响应回传客户端。",
    ],
    "sock-icmp": [
        "ICMP 报文头用 `struct.pack(\"bbHHh\", type, code, checksum, id, sequence)` 打包；Echo Request 的 type=8、code=0。",
        "校验和先按 0 计算：`header = struct.pack(\"bbHHh\", 8, 0, 0, ID, 1)`，算出 `checksum(header + data)` 后写入并 `socket.htons()` 转换字节序。",
        "创建原始套接字 `socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname(\"icmp\"))`，用 `sendto(packet, (destAddr, 1))` 发送、`recvfrom(1024)` 接收。",
    ],
}


# --------------------------------------------------------------------------
# 章节数据（mock）
# --------------------------------------------------------------------------

CHAPTERS: list[Chapter] = [
    Chapter(
        id="ch1",
        number="Chapter 1",
        title="Computer Networks and the Internet",
        summary="网络的基本组成、分组交换与协议分层。",
        knowledge_points=[
            KnowledgePoint(id="kp-1-1", title="What is the Internet?", summary="网络的组成视角与结构"),
            KnowledgePoint(id="kp-1-2", title="The Network Edge", summary="接入网与端系统"),
            KnowledgePoint(id="kp-1-3", title="The Network Core", summary="分组交换与电路交换"),
            KnowledgePoint(id="kp-1-4", title="Delay, Loss, and Throughput", summary="时延、丢包与吞吐量"),
            KnowledgePoint(id="kp-1-5", title="Protocol Layers", summary="协议分层与封装"),
        ],
        wireshark_labs=[
            WiresharkLab(
                id="ws-intro",
                title="Wireshark 入门",
                pcap_path="static/pcaps/intro.pcap",
                guide_path="static/guides/ws-intro.md",
            ),
        ],
        socket_exercises=[
            SocketExercise(
                id="sock-websocket",
                title="Ping 命令引导",
                language="python",
                starter_code_path="static/starter/ch1_ping.py",
                guide_path="static/guides/sock-websocket.md",
                test_cases=[],
            ),
        ],
    ),
    Chapter(
        id="ch2",
        number="Chapter 2",
        title="Application Layer",
        summary="应用层原理、HTTP/DNS 协议与 Socket 编程。",
        knowledge_points=[
            KnowledgePoint(id="kp-2-1", title="Principles of Network Applications", summary="应用体系结构"),
            KnowledgePoint(id="kp-2-2", title="The Web and HTTP", summary="HTTP 协议与缓存"),
            KnowledgePoint(id="kp-2-3", title="DNS", summary="域名系统"),
            KnowledgePoint(id="kp-2-4", title="Socket Programming", summary="UDP/TCP 套接字编程"),
        ],
        wireshark_labs=[
            WiresharkLab(
                id="ws-http",
                title="HTTP 协议实验",
                pcap_path="static/pcaps/http.pcap",
                guide_path="static/guides/ws-http.md",
            ),
            WiresharkLab(
                id="ws-dns",
                title="DNS 协议实验",
                pcap_path="static/pcaps/ws-dns.pcap",
                guide_path="static/guides/ws-dns.md",
            ),
        ],
        socket_exercises=[
            SocketExercise(
                id="sock-web",
                title="简易 Web 服务器",
                language="python",
                starter_code_path="static/starter/ch2_web_server.py",
                guide_path="static/guides/sock-web.md",
                test_cases=[
                    TestCase(name="GET 200", input="GET /index.html HTTP/1.1", expected="HTTP/1.1 200 OK"),
                    TestCase(name="GET 404", input="GET /missing.html HTTP/1.1", expected="HTTP/1.1 404 Not Found"),
                ],
            ),
            SocketExercise(
              id="sock-web-client",
              title="Web 客户端",
              language="python",
              starter_code_path="static/starter/ch2_web_client.py",
              guide_path="static/guides/sock-web-client.md",
              test_cases=[],
            ),
            SocketExercise(
                id="sock-pinger",
                title="UDP Pinger 客户端",
                language="python",
                starter_code_path="static/starter/ch2_udp_pinger.py",
                guide_path="static/guides/sock-pinger.md",
                test_cases=[],
            ),
            SocketExercise(
                id="sock-pinger-server",
                title="UDP Pinger 服务器",
                language="python",
                starter_code_path="static/starter/ch2_udp_pinger_server.py",
                guide_path="static/guides/sock-pinger-server.md",
                test_cases=[],
            ),
            SocketExercise(
                id="sock-smtp",
                title="SMTP 邮件客户端",
                language="python",
                starter_code_path="static/starter/ch2_smtp.py",
                guide_path="static/guides/sock-smtp.md",
                test_cases=[],
            ),
            SocketExercise(
                id="sock-proxy",
                title="Web 代理服务器",
                language="python",
                starter_code_path="static/starter/ch2_proxy.py",
                guide_path="static/guides/sock-proxy.md",
                test_cases=[],
            ),
        ],
    ),
    Chapter(
        id="ch3",
        number="Chapter 3",
        title="Transport Layer",
        summary="传输层：UDP/TCP 与可靠传输。",
        knowledge_points=[
            KnowledgePoint(id="kp-3-1", title="Multiplexing and Demultiplexing", summary="多路复用与分用"),
            KnowledgePoint(id="kp-3-2", title="UDP", summary="无连接传输"),
            KnowledgePoint(id="kp-3-3", title="TCP", summary="可靠数据传输"),
        ],
        wireshark_labs=[
            WiresharkLab(id="ws-tcp", title="TCP 协议实验", pcap_path="static/pcaps/ws-tcp.pcap", guide_path="static/guides/ws-tcp.md"),
            WiresharkLab(id="ws-udp", title="UDP 协议实验", pcap_path="static/pcaps/ws-udp.pcap", guide_path="static/guides/ws-udp.md"),
        ],
        socket_exercises=[],
    ),
    Chapter(
        id="ch4",
        number="Chapter 4",
        title="Network Layer: Data Plane",
        summary="网络层数据平面：IP 编址、转发与 DHCP/NAT。",
        knowledge_points=[
            KnowledgePoint(id="kp-4-1", title="IPv4 Addressing", summary="IPv4 编址"),
            KnowledgePoint(id="kp-4-2", title="Forwarding", summary="转发"),
        ],
        wireshark_labs=[
            WiresharkLab(id="ws-ip", title="IP 协议实验", pcap_path="static/pcaps/ws-ip.pcap", guide_path="static/guides/ws-ip.md"),
            WiresharkLab(id="ws-dhcp", title="DHCP 协议实验", pcap_path="static/pcaps/ws-dhcp.pcap", guide_path="static/guides/ws-dhcp.md"),
            WiresharkLab(id="ws-nat", title="NAT 实验", pcap_path="static/pcaps/ws-nat.pcap", guide_path="static/guides/ws-nat.md"),
        ],
        socket_exercises=[],
    ),
    Chapter(
        id="ch5",
        number="Chapter 5",
        title="Network Layer: Control Plane",
        summary="网络层控制平面：路由选择算法、OSPF/BGP、SDN、ICMP 与网络管理。",
        knowledge_points=[
            KnowledgePoint(id="kp-5-1", title="Routing Algorithms", summary="链路状态与距离向量"),
            KnowledgePoint(id="kp-5-2", title="OSPF", summary="域内路由（Intra-AS）"),
            KnowledgePoint(id="kp-5-3", title="BGP", summary="域间路由（Inter-AS）"),
            KnowledgePoint(id="kp-5-4", title="SDN Control Plane", summary="软件定义网络与 OpenFlow"),
            KnowledgePoint(id="kp-5-5", title="ICMP", summary="因特网控制报文协议"),
            KnowledgePoint(id="kp-5-6", title="SNMP & NETCONF", summary="网络管理"),
        ],
        wireshark_labs=[
            WiresharkLab(id="ws-icmp", title="ICMP 协议实验", pcap_path="static/pcaps/ws-icmp.pcap", guide_path="static/guides/ws-icmp.md"),
        ],
        socket_exercises=[
            SocketExercise(
                id="sock-icmp",
                title="ICMP Ping 客户端",
                language="python",
                starter_code_path="static/starter/ch5_icmp.py",
                guide_path="static/guides/sock-icmp.md",
                test_cases=[],
            ),
        ],
    ),
    Chapter(
        id="ch6",
        number="Chapter 6",
        title="The Link Layer and LANs",
        summary="链路层：差错检测、多路访问、以太网、ARP、交换机与 VLAN。",
        knowledge_points=[
            KnowledgePoint(id="kp-6-1", title="Link Layer Overview", summary="链路层服务与成帧"),
            KnowledgePoint(id="kp-6-2", title="Error Detection", summary="差错检测与纠正"),
            KnowledgePoint(id="kp-6-3", title="Multiple Access", summary="多路访问协议"),
            KnowledgePoint(id="kp-6-4", title="ARP", summary="地址解析协议"),
            KnowledgePoint(id="kp-6-5", title="Ethernet", summary="以太网帧"),
            KnowledgePoint(id="kp-6-6", title="Switches & VLAN", summary="链路层交换机与虚拟局域网"),
        ],
        wireshark_labs=[
            WiresharkLab(id="ws-ethernet-arp", title="以太网与 ARP 实验", pcap_path="static/pcaps/ws-ethernet-arp.pcap", guide_path="static/guides/ws-ethernet-arp.md"),
        ],
        socket_exercises=[],
    ),
    Chapter(
        id="ch7",
        number="Chapter 7",
        title="Wireless and Mobile Networks",
        summary="无线与移动网络：无线链路特征、WiFi、蜂窝网络与移动性管理。",
        knowledge_points=[
            KnowledgePoint(id="kp-7-1", title="Wireless Links", summary="无线链路与网络特征"),
            KnowledgePoint(id="kp-7-2", title="WiFi & CSMA/CA", summary="802.11 体系结构与接入"),
            KnowledgePoint(id="kp-7-3", title="802.11 Frame", summary="802.11 帧结构"),
            KnowledgePoint(id="kp-7-4", title="Cellular Networks", summary="4G 与 5G 蜂窝网络"),
            KnowledgePoint(id="kp-7-5", title="Mobility Management", summary="移动性管理"),
        ],
        wireshark_labs=[
            WiresharkLab(id="ws-80211", title="802.11 无线局域网实验", pcap_path="static/pcaps/ws-80211.pcap", guide_path="static/guides/ws-80211.md"),
        ],
        socket_exercises=[],
    ),
    Chapter(
        id="ch8",
        number="Chapter 8",
        title="Security in Computer Networks",
        summary="网络安全：攻击类型、密码学、完整性、鉴别、TLS 与防火墙。",
        knowledge_points=[
            KnowledgePoint(id="kp-8-1", title="Network Security", summary="安全目标与攻击类型"),
            KnowledgePoint(id="kp-8-2", title="Cryptography", summary="对称与公钥加密"),
            KnowledgePoint(id="kp-8-3", title="Integrity & Signatures", summary="报文完整性与数字签名"),
            KnowledgePoint(id="kp-8-4", title="Authentication", summary="端点鉴别与密钥分发"),
            KnowledgePoint(id="kp-8-5", title="SSL/TLS", summary="安全传输层协议"),
            KnowledgePoint(id="kp-8-6", title="IPsec & Firewalls", summary="网络层安全与运维安全"),
        ],
        wireshark_labs=[
            WiresharkLab(id="ws-ssl", title="SSL 安全实验", pcap_path="static/pcaps/ws-ssl.pcap", guide_path="static/guides/ws-ssl.md"),
        ],
        socket_exercises=[],
    ),
]


# --------------------------------------------------------------------------
# 将 Wireshark 实验 / Socket 练习统一为 Lab 详情模型，构建查询索引。
# --------------------------------------------------------------------------

def _lab_from_wireshark(chapter: Chapter, lab: WiresharkLab) -> Lab:
    """把 Wireshark 实验元数据展开为统一 Lab 详情。

    ``attachments`` 只收录磁盘上真实存在的文件——pcap / 指南正文有的 lab 有、有的没有，
    把不存在的路径报给前端等于让 API 撒谎。
    """
    candidates = [
        Attachment(
            name=lab.pcap_path.rsplit("/", 1)[-1],
            path=lab.pcap_path,
            kind="pcap",
            description="抓包文件",
        ),
        Attachment(
            name=lab.guide_path.rsplit("/", 1)[-1],
            path=lab.guide_path,
            kind="markdown",
            description="实验指南",
        ),
    ]
    return Lab(
        id=lab.id,
        chapter_id=chapter.id,
        type="wireshark",
        title=lab.title,
        summary=chapter.title,
        guide_path=lab.guide_path,
        guide=GUIDES[lab.id],
        document_path=_document_path(lab.id),
        attachments=[a for a in candidates if _file_exists(a.path)],
    )


def _lab_from_socket(chapter: Chapter, ex: SocketExercise) -> Lab:
    """把 Socket 练习元数据展开为统一 Lab 详情（``attachments`` 同样只收录真实存在的文件）。"""
    candidates = [
        Attachment(
            name=ex.starter_code_path.rsplit("/", 1)[-1],
            path=ex.starter_code_path,
            kind="code",
            description="初始代码模板",
        ),
        Attachment(
            name=ex.guide_path.rsplit("/", 1)[-1],
            path=ex.guide_path,
            kind="markdown",
            description="练习说明",
        ),
        Attachment(
            name="test_cases.py",
            path=f"static/tests/{ex.id}_tests.py",
            kind="test",
            description="测试用例",
        ),
    ]
    return Lab(
        id=ex.id,
        chapter_id=chapter.id,
        type="socket",
        title=ex.title,
        summary=chapter.title,
        language=ex.language,
        guide_path=ex.guide_path,
        guide=GUIDES[ex.id],
        starter_code=_read_starter(ex.starter_code_path.rsplit("/", 1)[-1]),
        reference_code=_read_solution(ex.starter_code_path.rsplit("/", 1)[-1]),
        reference_server_code=_read_server_code(ex.id, ex.starter_code_path),
        hints=HINTS.get(ex.id, []),
        document_path=_document_path(ex.id),
        attachments=[a for a in candidates if _file_exists(a.path)],
        test_cases=ex.test_cases,
    )


LAB_INDEX: dict[str, Lab] = {}
for _ch in CHAPTERS:
    for _ws in _ch.wireshark_labs:
        LAB_INDEX[_ws.id] = _lab_from_wireshark(_ch, _ws)
    for _sock in _ch.socket_exercises:
        LAB_INDEX[_sock.id] = _lab_from_socket(_ch, _sock)


def get_lab(chapter_id: str, lab_id: str) -> Lab | None:
    """按 ``chapter_id`` + ``lab_id`` 查询 Lab 详情；章节不存在或 Lab 不属于该章节时返回 ``None``。"""
    lab = LAB_INDEX.get(lab_id)
    if lab is None or lab.chapter_id != chapter_id:
        return None
    return lab
