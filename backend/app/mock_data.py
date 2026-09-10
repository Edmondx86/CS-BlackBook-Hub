"""Mock 数据：用《自顶向下》前两章演示完整数据结构与接口。

生产环境中这些数据应来自数据库或磁盘文件；这里为保持轻量，直接以内联
方式给出，并在模块底部构建 ``LAB_INDEX`` 供 labs 路由做 O(1) 查询。
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
# Markdown 指南内容（mock）。真实实现可从 guide_path 指向的磁盘文件读取。
# --------------------------------------------------------------------------

GUIDES: dict[str, str] = {
    "ws-intro": """# Wireshark 入门实验

> 对应教材 **Chapter 1**「Computer Networks and the Internet」。

## 实验目标

1. 熟悉 Wireshark 的抓包界面与基本过滤语法。
2. 观察一次 HTTP 请求/响应在链路层到应用层的报文封装过程。
3. 理解分组交换网络中「报文往返（round trip）」的基本概念。

## 实验材料

- 抓包文件：`intro.pcap`（见附件）

## 实验步骤

### 1. 打开抓包文件

1. 启动 Wireshark，选择 `File → Open`，打开附件中的 `intro.pcap`。
2. 在显示过滤器输入 `http`，回车，只保留 HTTP 报文。

### 2. 观察 HTTP 请求

1. 选中第一条 `GET / HTTP/1.1` 报文。
2. 在「Packet Details」面板展开 `Hypertext Transfer Protocol` 层，记录：
   - 请求方法（Request Method）
   - Host 头字段
   - User-Agent 头字段

### 3. 观察报文封装

依次展开 `Ethernet II → Internet Protocol → Transmission Control Protocol → HTTP`，
确认每层对应的源/目的地址字段。

## 思考题

1. 为什么 DNS 查询报文通常出现在 HTTP 请求之前？
2. 同一连接上是否出现了 TCP 三次握手？请指出对应的三个报文序号。

## 提交要求

将上述观察结果整理为 Markdown 报告，随截图一并提交。
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

1. 监听 `127.0.0.1:6789`。
2. 接收浏览器发来的 HTTP GET 请求。
3. 若请求文件存在，返回 `200 OK` 及文件内容；否则返回 `404 Not Found`。

## 初始代码

见附件 `web_server.py`，请补全 `handle_request` 函数。

## 测试

运行 `pytest test_cases.py`，或手动使用 `curl http://127.0.0.1:6789/hello.html` 验证。

## 评分标准

- 正确解析请求行（30%）
- 正确处理 200 / 404（40%）
- 代码结构与注释（30%）
""",
     "sock-web-client":"""
     # Socket 编程练习：简易 Web 服务器

> 对应教材 **Chapter 2**「Application Layer」2.7 节。

## 任务

使用 Python 的 ·socket· 模块实现一个单线程的客户端 HTTP 请求
"""
  ,
    "sock-pinger": """# Socket 编程练习：UDP Pinger

> 对应教材 **Chapter 2**「Application Layer」2.7 节。

## 任务

1. 实现 UDP **客户端**：向服务器发送 10 个 ping 报文，每个包含序号与时间戳。
2. 若 1 秒内未收到响应，打印 `Request timed out`。
3. 实现 UDP **服务器**：随机丢弃部分报文以模拟丢包，其余原样回显。

## 初始代码

见附件 `udp_pinger_client.py` 与 `udp_pinger_server.py`。

## 测试

见附件 `test_cases.py`，覆盖超时重传与正常回显两种场景。

## 提交要求

提交源码并附上客户端运行截图。
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

> 对应教材 **Chapter 4**「Network Layer」。

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

> 对应教材 **Chapter 5**「The Link Layer」。

使用 Wireshark 观察以太网帧结构与 ARP 地址解析过程。详细实验步骤见「作业要求文档」（PDF）。
""",
    "ws-80211": """# 802.11 无线局域网实验

> 对应教材 **Chapter 6**「Wireless and Mobile Networks」。

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

> 对应教材 **Chapter 4**「Network Layer」。

实现一个 ICMP Ping 客户端，发送 Echo Request 并测量 RTT。详细要求见「作业要求文档」（PDF）。
""",
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
        socket_exercises=[],
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
                starter_code_path="static/starter/web_server.py",
                guide_path="static/guides/sock-web.md",
                test_cases=[
                    TestCase(name="GET 200", input="GET /index.html HTTP/1.1", expected="HTTP/1.1 200 OK"),
                    TestCase(name="GET 404", input="GET /missing.html HTTP/1.1", expected="HTTP/1.1 404 Not Found"),
                ],
            ),
            SocketExercise(
              id="sock-web-client",
              title="简易 Web 服务器（Client）",
              language="python",
              starter_code_path="static/starter/web_client.py",
              guide_path="static/guides/sock-web-client.md",
                 test_cases=[
                    TestCase(name="GET 200", input="GET /hello.html HTTP/1.1", expected="HTTP/1.1 200 OK"),
                    TestCase(name="GET 404", input="GET /missing.html HTTP/1.1", expected="HTTP/1.1 404 Not Found"),
                ],
            ),
            SocketExercise(
                id="sock-pinger",
                title="UDP Pinger",
                language="python",
                starter_code_path="static/starter/udp_pinger.py",
                guide_path="static/guides/sock-pinger.md",
                test_cases=[
                    TestCase(name="回显 ping 1", input="ping 1", expected="ping 1"),
                    TestCase(name="回显 hello", input="hello", expected="hello"),
                ],
            ),
            SocketExercise(
                id="sock-smtp",
                title="SMTP 邮件客户端",
                language="python",
                starter_code_path="static/starter/sock-smtp.py",
                guide_path="static/guides/sock-smtp.md",
                test_cases=[],
            ),
            SocketExercise(
                id="sock-proxy",
                title="Web 代理服务器",
                language="python",
                starter_code_path="static/starter/sock-proxy.py",
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
        summary="网络层：IP 编址、转发与 ICMP/DHCP/NAT。",
        knowledge_points=[
            KnowledgePoint(id="kp-4-1", title="IPv4 Addressing", summary="IPv4 编址"),
            KnowledgePoint(id="kp-4-2", title="Forwarding", summary="转发"),
            KnowledgePoint(id="kp-4-3", title="ICMP", summary="差错报告"),
        ],
        wireshark_labs=[
            WiresharkLab(id="ws-ip", title="IP 协议实验", pcap_path="static/pcaps/ws-ip.pcap", guide_path="static/guides/ws-ip.md"),
            WiresharkLab(id="ws-icmp", title="ICMP 协议实验", pcap_path="static/pcaps/ws-icmp.pcap", guide_path="static/guides/ws-icmp.md"),
            WiresharkLab(id="ws-dhcp", title="DHCP 协议实验", pcap_path="static/pcaps/ws-dhcp.pcap", guide_path="static/guides/ws-dhcp.md"),
            WiresharkLab(id="ws-nat", title="NAT 实验", pcap_path="static/pcaps/ws-nat.pcap", guide_path="static/guides/ws-nat.md"),
        ],
        socket_exercises=[
            SocketExercise(
                id="sock-icmp",
                title="ICMP Ping 客户端",
                language="python",
                starter_code_path="static/starter/sock-icmp.py",
                guide_path="static/guides/sock-icmp.md",
                test_cases=[],
            ),
        ],
    ),
    Chapter(
        id="ch5",
        number="Chapter 5",
        title="The Link Layer and LANs",
        summary="链路层：以太网与 ARP。",
        knowledge_points=[
            KnowledgePoint(id="kp-5-1", title="Ethernet", summary="以太网帧"),
            KnowledgePoint(id="kp-5-2", title="ARP", summary="地址解析协议"),
        ],
        wireshark_labs=[
            WiresharkLab(id="ws-ethernet-arp", title="以太网与 ARP 实验", pcap_path="static/pcaps/ws-ethernet-arp.pcap", guide_path="static/guides/ws-ethernet-arp.md"),
        ],
        socket_exercises=[],
    ),
    Chapter(
        id="ch6",
        number="Chapter 6",
        title="Wireless and Mobile Networks",
        summary="无线网络：802.11。",
        knowledge_points=[
            KnowledgePoint(id="kp-6-1", title="802.11 Frame", summary="802.11 帧结构"),
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
        summary="网络安全：SSL/TLS。",
        knowledge_points=[
            KnowledgePoint(id="kp-8-1", title="SSL/TLS", summary="安全传输层协议"),
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
    """把 Wireshark 实验元数据展开为统一 Lab 详情。"""
    return Lab(
        id=lab.id,
        chapter_id=chapter.id,
        type="wireshark",
        title=lab.title,
        summary=chapter.title,
        guide_path=lab.guide_path,
        guide=GUIDES[lab.id],
        document_path=DOCUMENTS.get(lab.id),
        attachments=[
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
        ],
    )


def _lab_from_socket(chapter: Chapter, ex: SocketExercise) -> Lab:
    """把 Socket 练习元数据展开为统一 Lab 详情。"""
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
        document_path=DOCUMENTS.get(ex.id),
        attachments=[
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
        ],
        test_cases=ex.test_cases,
    )


LAB_INDEX: dict[str, Lab] = {}
for _ch in CHAPTERS:
    for _ws in _ch.wireshark_labs:
        LAB_INDEX[_ws.id] = _lab_from_wireshark(_ch, _ws)
    for _sock in _ch.socket_exercises:
        LAB_INDEX[_sock.id] = _lab_from_socket(_ch, _sock)


def get_lab(lab_id: str) -> Lab | None:
    """按 ``lab_id`` 查询 Lab 详情；不存在时返回 ``None``。"""
    return LAB_INDEX.get(lab_id)
