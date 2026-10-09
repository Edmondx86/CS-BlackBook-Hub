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

> 对应教材 **Chapter 1 · Computer Networks and the Internet** ｜ 建议 40 分钟 ｜ 难度 ★☆☆

## 这个实验要回答什么

“分组嗅探器”到底在做什么？一次普通的网页访问，在链路上是什么样子？
教科书里讲的协议分层，在真实的抓包里怎么体现出来？

做完这个实验，你手里就有了一件贯穿全书的工具：**把看不见的协议变成看得见的分组**。
后面每一个 Wireshark 实验都建立在这一套基本操作上，所以这个实验值得慢慢做。

## 开始之前

- **下载安装 Wireshark**：<https://www.wireshark.org/download.html>
  Windows 安装过程中会问要不要装 **Npcap**，**必须勾选**，否则打开后一个网卡都看不到。
- **抓包需要管理员 / root 权限**（要把网卡切到混杂模式，这属于特权操作）。
- **选对网卡**：无线网卡（Wi-Fi）还是有线，选那个“流量在跳”的。
  装了虚拟机的话会多出 `vmnet*`、`lo` 之类的接口，那些通常没有你要的流量。
- **分清两种过滤器**，这是最容易混的地方：
  - **捕获过滤器**（Capture Filter）：抓之前设，不符合的包直接丢掉，省磁盘。
  - **显示过滤器**（Display Filter）：抓之后筛，包都还在，只是不显示。

## 实验步骤

1. 打开 Wireshark，在欢迎页的**接口列表**里挑一个流量在跳的接口，双击开始捕获。
2. 让浏览器随便访问一个页面，然后回到 Wireshark 点左上角的红色方块停止捕获。
3. **认识三个面板**：
   - 上面：分组列表（一行一个报文，含时间、源、目的、协议、长度）
   - 中间：分组详情（按协议分层展开，这是最常看的地方）
   - 下面：分组字节（十六进制 + ASCII，用来核对字段的真实取值）
4. 在最上面的**显示过滤器**栏输入 `http`，回车。观察列表只剩 HTTP 报文，右下角状态栏会显示已过滤的比例。
5. 清空过滤器，随便点一个报文，在详情面板里逐层展开：
   `Frame → Ethernet II → IPv4 → TCP → 应用层`。体会“一层包一层”的封装关系。
6. 打开 `Statistics → Protocol Hierarchy`，看看这次抓包到底涉及哪些协议、各占多少 —— 你会发现自己平时上网的流量比想象中杂得多。
7. `File → Save As` 保存成 `.pcapng`。后面每个实验都建议这样留档，方便回头再看。

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `http` | 只看 HTTP |
| `dns` | 只看 DNS |
| `tcp` / `udp` / `icmp` | 按传输层协议筛 |
| `ip.addr == 1.1.1.1` | 与某个 IP 有关的全部报文 |
| `tcp.port == 443` | 按端口筛 |
| `tcp and ip.addr == 1.1.1.1` | 用 `and` / `or` / `not` 组合 |
| `!(arp or icmp)` | 排除某些协议 |

> 小坑：判断“不相等”要写 `!=`，而 `not` 用在协议名和组合表达式上。

## 要交付什么

- 本次抓包的**分组总数**与协议分布（`Protocol Hierarchy` 截图或抄写）。
- 挑一个报文，写出它的**四层头部**：帧、IP、TCP/UDP、应用层分别是什么协议、关键字段是什么。
- **一个你自己写的显示过滤器**，说明它筛掉了什么、留下了什么。

## 思考题

1. 为什么抓包需要管理员权限？普通权限下 Wireshark 能做什么、不能做什么？
2. 捕获过滤器和显示过滤器分别作用在哪个阶段？各自的优缺点是什么？
3. 你抓到的报文里，有多少是“发给你的”？剩下的为什么会出现？

## 常见问题

**接口列表是空的？** 三种可能：没装 Npcap（Windows）、当前用户权限不足、网卡被虚拟机软件独占。

**开始抓包后一个包都没有？** 多半选错了网卡 —— 选到 `lo`（回环）或没有流量的虚拟网卡了。

**协议完全不认识？** 正常。现代网页会顺带产生 TLS、QUIC、mDNS 等一堆流量。先用显示过滤器把它收敛到你关心的协议。
""",
    "ws-http": """# HTTP 协议实验

> 对应教材 **Chapter 2 · Application Layer** ｜ 建议 50 分钟 ｜ 难度 ★★☆

## 这个实验要回答什么

HTTP 请求报文和响应报文到底长什么样，每个首部字段在干什么？
加载一个页面用了几条 TCP 连接？“条件 GET”又是怎么帮浏览器省流量的？

## 开始之前

**这个实验最大的坑：现在绝大多数站点都是 HTTPS，抓不到明文 HTTP。**

所以不要去访问平时的网站，用专门为此存在的纯 HTTP 站点：

- <http://neverssl.com> —— 这个网站存在的意义就是“永远不跳转 HTTPS”，方便抓包和连公共 Wi-Fi 认证页
- 或者用命令行主动发一个：`curl -v http://neverssl.com/`

> 说明：教材的实验文档让你打开一个叫 `http.pcap` 的抓包文件，那个文件不在本站。
> 我们改成**自己抓一次真实的 HTTP**，步骤一样，而且过程更直观。

## 实验步骤

1. 建议先关掉浏览器（减少无关流量），然后打开 Wireshark、选有流量的网卡开始抓包。
2. 用浏览器访问 **<http://neverssl.com>**（注意是 `http` 不是 `https`）。
3. 等页面加载完，回到 Wireshark 停止捕获。
4. 显示过滤器输入 `http`，回车。
5. 找到第一条 **`GET / HTTP/1.1`**，在详情面板展开 `Hypertext Transfer Protocol`，记录这些字段：
   - 请求方法（Request Method）与请求 URI
   - `Host`、`User-Agent`、`Accept`、`Accept-Encoding`、`Connection`
6. 找到它对应的**响应**，记录：
   - 状态行（例如 `HTTP/1.1 200 OK`）
   - `Content-Type`、`Content-Length`、`Cache-Control`、`Last-Modified`、`ETag`
7. **观察条件 GET**：再访问一次同一个页面（或在地址栏回车刷新），看请求里是否出现了
   `If-Modified-Since` 或 `If-None-Match`，以及响应是否为 **`304 Not Modified`**。
8. **数连接**：清空过滤器，打开 `Statistics → Conversations`，切到 TCP 标签页，看这次页面加载一共开了几条 TCP 连接。
9. （可选）观察持久连接：找同一条 `tcp.stream`，看里面是否出现了多次 HTTP 请求。

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `http` | 只看 HTTP |
| `http.request` / `http.response` | 只看请求 / 只看响应 |
| `http.request.method == "GET"` | 指定请求方法 |
| `http.response.code == 200` | 只看成功响应 |
| `http.response.code == 304` | 只看“没变，用缓存”的响应 |
| `http.host contains "neverssl"` | 按 Host 筛 |
| `tcp.stream eq 0` | 只看某一条连接 |

## 要交付什么

- 一次请求与响应的**首部字段清单**（各列 5 个以上，写清字段名和值）。
- 是否出现了条件 GET？依据是哪个字段？
- 这次页面加载一共用了几条 TCP 连接？依据是什么？

## 思考题

1. HTTP/1.1 默认是持久连接，那 `Connection: close` 什么时候才会出现？
2. 条件 GET 省下的是哪一部分流量？它省掉了响应正文，还是连请求也省了？
3. HTTP 是无状态协议，那网站是怎么知道“你已经登录了”的？

## 常见问题

**过滤 `http` 出来的不是 HTTP 报文？** 有些非 HTTP 流量里也含 `http` 字样，用 `http.request` 更准。

**访问的站点自动跳到 HTTPS 了？** 换成 `neverssl.com`，或者用 `curl` 显式指定 `http://`。

**看不到 304？** 先正常访问一次让浏览器建立缓存，再**普通刷新**。按 Ctrl+F5 强制刷新反而不会出现 304 —— 那正是在绕过缓存。

**整个页面只看到一条 GET，没有图片请求？** 说明该页面资源少或者浏览器用了缓存，刷新时按住 Shift 会更完整。
""",
    "sock-web": """# Socket 编程练习：简易 Web 服务器

> 对应教材 **Chapter 2 · Application Layer** 2.7 节 ｜ 建议 50 分钟 ｜ 难度 ★★☆

## 这个练习在干什么

浏览器和 Web 服务器之间那一问一答，这次轮到你来当服务器：用 Python 的 `socket`
模块搭一个单线程 HTTP 服务器，接到请求后从磁盘读出文件、回一个带状态行的 HTTP 响应。
写完它，你就亲手实现了 HTTP 报文“响应”的那一半 —— 响应行、状态码、正文都经你的手。

## 开始之前

- 需要的背景：TCP 套接字怎么建、怎么收发（第 2 章“网络套接字编程”那张知识卡片）。
- **初始代码里全是 TODO**，你只需要补全处理请求的函数体，外层的架子别动。
- 判题引擎会在沙箱里运行你的代码 —— 你的服务器只能在自己的回环上被访问，这很正常。

## 判题会怎么检查

点击“运行测试”后，判题程序会用随机端口启动你的服务器，然后以客户端身份连上来：

1. 发一个 `GET /index.html`，期望你的响应状态行是 **`200 OK`**；
2. 再发一个 `GET /missing.html`，期望你的响应是 **`404 Not Found`**。

两个检查都通过才算完成。判题看重的是**状态行**，正文内容随文件走。

## 实现步骤

1. **建监听套接字** —— `socket(AF_INET, SOCK_STREAM)`，绑定端口、`listen()`，然后循环 `accept()`。端口从环境变量 `PORT` 读，不要写死。
2. **读请求行** —— `recv(1024)` 拿到请求，按空格切出文件名（注意去掉开头的 `/`）。
3. **打开文件** —— 用 `try/except IOError` 包住 `open()`：成功就准备 200，失败就准备 404。
4. **写响应** —— 200 时先发 `HTTP/1.1 200 OK` 再加文件内容；404 时发 `HTTP/1.1 404 Not Found`。
5. **关连接** —— 处理完就 `close()`，让客户端知道响应结束了。

卡住时点编辑器右上角的“提示”按钮，它会一级一级给你提示（最后一层是参考答案）。

## 常见问题

**判题说“端口未就绪或进程退出”？** 十有八九是你的服务器没从环境变量 `PORT` 读端口，或者一启动就崩了。先在终端里看判题日志中你自己的 stderr。

**`open(filename[1:])` 是什么鬼？** 请求行里的路径带前导 `/`（如 `/index.html`），当文件名用时要把第一个字符去掉。

**本地自测要绑哪个端口？** 判题每次都会注入一个空闲端口（通过 `PORT`），所以判题时不会撞；你本地自测直接跑就行（默认 8080），要改就改那个默认值 —— 别写死 80，那会撞上宿主机上的 nginx，而且非 root 用户根本绑不了。
""",
    "sock-web-client": """# Socket 编程练习：Web 客户端

> 对应教材 **Chapter 2 · Application Layer** 2.7 节 ｜ 建议 40 分钟 ｜ 难度 ★★☆

## 这个练习在干什么

上一个练习你当了服务器，这次当客户端：写一个模仿浏览器的 TCP 客户端，
向 `127.0.0.1` 上的参考服务器（端口从环境变量 `PORT` 读）发一个 `GET /hello.html` 请求，
把服务器返回的响应原样打印出来。
HTTP 请求报文的那一半 —— 请求行、头字段、空行结尾 —— 由你来拼。

## 开始之前

- 地址固定是 `127.0.0.1`，**端口从环境变量 `PORT` 读**（判题时会注入一个空闲端口，
  所以别写死端口号）：`serverPort = int(os.environ.get("PORT", 8080))`
- 判题时后端会在那个端口上起一个参考服务器，你只管连它。

## 判题会怎么检查

点击“运行测试”后，判题程序先在 `127.0.0.1` 的 `PORT` 端口起一个参考 HTTP 服务器
（`/hello.html` 返回 200），再运行你的客户端。**两条同时满足才通过**：

1. 参考服务器**确实收到了** `GET /hello.html` 请求；
2. 你的客户端**打印出了 `200 OK`** 状态行。

所以别只发送、不打印 —— 判题要看你的输出。

## 实现步骤

1. **建 TCP 套接字并连接** —— `socket(AF_INET, SOCK_STREAM)`，`connect(('127.0.0.1', serverPort))`。
2. **拼请求报文** —— 请求行 `GET /hello.html HTTP/1.1`，加 `Host` 头，最后**以空行结尾**（`\\r\\n\\r\\n`）。
3. **发送** —— `send()` 把整个报文发出去。
4. **循环接收直到连接关闭** —— `recv(4096)`，返回空串就说明服务器发完了；每段都打印。
5. **自己核对** —— 打印出的内容里应该有一行 `HTTP/1.1 200 OK`，这正是判题要找的那条。

## 常见问题

**服务器怎么没回应？** 请求报文结尾少了空行 —— HTTP 以空行标志请求头结束，不补上服务器会一直等。

**连接一直收不到关闭？** 请求头里带上 `Connection: close`，让服务器发完就关；判题的参考服务器是按这个约定做的。

**打印了响应但判题不认？** 判题找的是 `200 OK` 这个子串，大小写和空格别写错。
""",
    "sock-pinger": """# Socket 编程练习：UDP Pinger 客户端

> 对应教材 **Chapter 2 · Application Layer** 2.7 节 ｜ 建议 50 分钟 ｜ 难度 ★★☆

## 这个练习在干什么

实现教材 2.7 的经典例子：一个 UDP Ping 客户端。它给服务器连发 10 个 ping，
收到回显就打印 RTT，1 秒内没等到就打印 `lost`。你在亲手实现“超时与重传”
这套逻辑最原始的形态，同时体会 UDP 和 TCP 最大的区别：**发出去不等于送到了**。

## 开始之前

- 判题时后端会拉起一个 UDP 回显服务器（收到报文转大写回显），端口通过 `--port` 传给你的程序。
- 你只实现**客户端**那一半，服务器是判题方的。
- 报文内容随意，教材惯例是 `Ping <序号> <时间戳>`。

## 判题会怎么检查

判题程序起参考服务器后运行你的客户端，检查两点：

1. 参考服务器**收到了你的 ping 报文**；
2. 你的客户端打印了**回显**（输出含 `rtt` 或 `reply`），并且**超时分支打印了 `lost`**。

也就是说，就算 10 个 ping 有丢的，只要你打印了 `lost`，判题也能认 —— 它在验证你写了超时处理。

## 实现步骤

1. **建 UDP 套接字并设超时** —— `socket(AF_INET, SOCK_DGRAM)`，`settimeout(1.0)`。
2. **循环发 10 个 ping** —— 发送前记 `time.time()`，用 `sendto()` 把 `Ping i 时间戳` 发到 `127.0.0.1:<port>`。
3. **接收与 RTT** —— `recvfrom(2048)` 收到回显，用当前时间减发送时间得到 RTT 并打印。
4. **处理超时** —— `except socket.timeout` 时打印 `lost`，继续下一个 ping。
5. **关套接字**，结束前统计一下收到几个、丢了几个。

## 常见问题

**端口到底用哪个？** 判题通过 `--port` 传进来，别写死 12000 —— 那个只是本地自测的默认值。

**收不到回显？** 检查 `sendto` 和 `recvfrom` 用的地址是否一致。UDP 没有“连接”，每次都要带上目的地址。

**为什么 RTT 和 lost 都要出现？** 参考服务器按固定概率丢包（`seed=42`），10 次 ping 必然有丢的；两种打印都出现，说明超时分支真的走了。
""",
    "sock-pinger-server": """# Socket 编程练习：UDP Pinger 服务器

> 对应教材 **Chapter 2 · Application Layer** 2.7 节 ｜ 建议 50 分钟 ｜ 难度 ★★☆

## 这个练习在干什么

Pinger 的另一半：写一个 UDP 服务器，收到客户端的 ping 就转成大写回显，
并且**按固定概率丢包** —— 真实网络里丢包是常态，你在这里把它模拟出来。
上一份练习里客户端那些 `lost`，就是被这里的服务器丢出来的。

## 开始之前

- 端口通过 `--port` 参数读入（本地自测默认 12000）。
- 丢包要用 `random.seed(42)` 固定随机序列 —— 判题依赖这个可复现性。

## 判题会怎么检查

判题程序以 UDP 客户端身份连上你的服务器，**连发 11 个 ping**，然后看：

1. 至少能收到 **3 次回显**（所以丢包率不能太高，`4/11` 是安全值）；
2. 收到的回显内容**全部正确转成了大写**。

## 实现步骤

1. **建并绑定套接字** —— `socket(AF_INET, SOCK_DGRAM)`，`bind(('', port))`。
2. **固定随机种子** —— `random.seed(42)`，让丢包可复现。
3. **接收循环** —— `recvfrom(1024)` 拿到报文和客户端地址。
4. **转大写** —— `message.upper()`。
5. **模拟丢包** —— 生成 `randint(0, 10)`，小于 4 就 `continue` 不回复（即 4/11 丢包率）。
6. **回显** —— `sendto(大写报文, 客户端地址)`。

## 常见问题

**判题说“响应不足 3 次”？** 丢包概率设得太高，或者压根没回显。按步骤 5 的 `rand < 4` 写。

**为什么一定要 `random.seed(42)`？** 不用固定种子，每次运行丢包位置都不同，判题没法稳定复现你的程序行为。

**回复地址哪来的？** `recvfrom` 返回 `(data, address)`，`address` 就是你要 `sendto` 的目的地。
""",
    "sock-websocket": """# 第一章引导：Ping 命令

> 对应教材 **Chapter 1 · Computer Networks and the Internet** ｜ 建议 10 分钟 ｜ 难度 ★☆☆

## 这个练习在干什么

这是全站的第一个练习，目的不是考你，而是让你**熟悉这台“在线判题”是怎么工作的**：
你在编辑器里输入一条 `ping` 命令，后端在沙箱里拉起一个服务器，替你发出 `ping`，
服务器回一个 `pong` —— 全程什么都不用装，在浏览器里就能体验一次完整的
“客户端 ↔ 服务器”对话。

`ping` 正是最古老的网络排障命令：它发一个“你还活着吗”的探测包，对方回答“活着”，
往返时间就是 RTT。

## 界面怎么看

- **左边**：这份指南（往下拉还有作业文档）。
- **右边上半**：代码编辑器 —— 你要输入的内容都写在这里。
- **右边下半**：终端 —— 判题过程的所有输出按行实时打在这里。
- 顶部的“运行测试”按钮会把编辑器里的内容交给后端判题。

## 判题会怎么检查

你提交的“代码”其实是一行 `ping <主机>:<端口>` 命令。判题程序会：

1. 识别它是不是以 `ping` 开头、并解析出主机和端口；
2. 在解析出的端口上起一个回 `pong` 的 TCP 服务器；
3. 发一个 `ping`，收到 `pong` 就判定通过，并在终端打印 `pong，恭喜你成功通过测试`。

## 实现步骤

1. **把下面的命令打进编辑器**：

   ```text
   ping 127.0.0.1:8000
   ```

2. **点击“运行测试”**，看右下方终端里判题日志的实时输出。
3. **读终端** —— 它会先识别命令，然后起服务器、发 ping、收到 pong。
   看到 `pong，恭喜你成功通过测试` 就说明整条链路通了。
4. 试试把它改错（比如 `ping 127.0.0.1`，少个端口），再跑一次，看判题怎么告诉你没通过。

## 想一想

1. `ping 127.0.0.1:8000` 里的 `127.0.0.1` 是什么？`8000` 又是什么？
2. 是谁在“发 ping”，谁在“回 pong”？它们跑在同一台机器上还是两台机器上？

## 常见问题

**为什么这里的 ping 用 TCP 8000 端口，而别人说 ping 走 ICMP？**
这里为了让你不用管理员权限就能体验，用 TCP 模拟了 ping 的往返。
真正的 `ping` 命令发的是 ICMP 报文 —— 第 5 章的“ICMP Ping 客户端”练习会让你实现它。
""",
    "ws-dns": """# DNS 协议实验

> 对应教材 **Chapter 2 · Application Layer** ｜ 建议 40 分钟 ｜ 难度 ★★☆

## 这个实验要回答什么

浏览器里敲一个域名，到你真正连上服务器之间发生了什么？一次解析要发几个报文？
本地 DNS 服务器、根服务器、顶级域服务器各自负责哪一段？DNS 默认走 UDP，又为什么必须保留 TCP。

## 开始之前

- Wireshark 能正常抓包（见入门实验）。
- **先清空本机 DNS 缓存**，否则解析命中缓存、你一个查询报文都抓不到：
  - Windows：`ipconfig /flushdns`
  - macOS：`sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`
  - Linux：`sudo resolvectl flush-caches`
- 准备一个**你没访问过**的域名，效果最明显。

## 实验步骤

1. **清缓存**（见上），然后开始抓包，显示过滤器先填 `dns`，列表会只剩 DNS 报文，看着清爽。
2. **触发一次解析**：`nslookup www.qq.com`（Windows 直接可用），或 `dig www.qq.com`。
3. 停止捕获，找到查询报文，展开 Domain Name System，记录 Transaction ID、Questions 里的查询名与查询类型（A / AAAA / CNAME）。
4. 找到它对应的响应报文，对比两者的 Transaction ID，在 Answers 里读出解析结果、TTL，以及是否存在 CNAME 链。
5. **制造一次失败**：`nslookup this-name-should-not-exist-12345.com`，观察响应里的 Flags → Reply code（NXDOMAIN）。
6. 指定服务器再查一次：`nslookup www.qq.com 8.8.8.8`，对比走的 DNS 服务器变了、报文内容有什么不同。
7. （可选）找一个响应很大的解析，看是否出现 TC（Truncated）标志并回退到 TCP 53。

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `dns` | 只看 DNS |
| `dns.flags.response == 0` | 只看查询 |
| `dns.flags.response == 1` | 只看响应 |
| `dns.qry.name contains "qq"` | 按查询的域名筛 |
| `dns.flags.rcode != 0` | 只看解析出错的 |
| `udp.port == 53` / `tcp.port == 53` | 分别看 UDP / TCP 上的 DNS |

## 要交付什么

一张表，把一次完整的解析记下来（这比抄教科书有用得多）：

| 项 | 查询 | 响应 |
| --- | --- | --- |
| 源 / 目的 IP:端口 | | |
| Transaction ID | | |
| 查询名 / 类型 | | |
| 解析结果 / TTL | — | |

## 思考题

1. 查询和响应为什么用同一个 Transaction ID？
2. UDP 53 和 TCP 53 分别在什么情况下用？EDNS0 又改变了什么？
3. TTL 到期之后会发生什么？它和 DNS 的“缓存”是怎么配合的？

## 常见问题

**一个 DNS 报文都没抓到？** 缓存命中就不会发查询。先清缓存，或者换一个从没访问过的域名。

**抓到一大堆奇怪的查询？** 那是 mDNS / LLMNR 之类的局域网设备发现在刷屏，用 `dns and ip.addr != 224.0.0.251` 排掉。

**nslookup 查的好像不是我想的那个服务器？** 不加参数时它走系统配置的解析器，用 `nslookup 域名 8.8.8.8` 显式指定。
""",
    "ws-tcp": """# TCP 协议实验

> 对应教材 **Chapter 3 · Transport Layer** ｜ 建议 60 分钟 ｜ 难度 ★★★

## 这个实验要回答什么

三次握手具体交换了什么？序号和确认号是怎么一字节一字节推进的？
为什么发送速率要“慢启动”？丢包和重传在抓包里长什么样？

## 开始之前

- 抓包位置要在**你本机**和你访问的服务器之间（本机抓包就是你发出的和收到的）。
- 想看清拥塞行为，**下载一个大文件**是最有效的办法：数据多、速率变化明显。
- 用 `curl` 比浏览器干净（浏览器会有预连接、缓存、多条并发流来干扰）。

## 实验步骤

1. 开始抓包，显示过滤器填 `tcp`（想更聚焦就 `tcp.port == 80`）。
2. 用命令行下载一个大文件，例如 `curl -o /dev/null http://speedtest.tele2.net/10MB.zip`。
3. 停止捕获，找到开头的 **SYN → SYN/ACK → ACK** 三条报文，记录双方的初始序号与窗口大小（Window Size）。
4. 打开 `Statistics → Flow Graph`，把 `tcp.stream` 对应的那条流画出来，直观看到报文往返与时序。
5. 挑一个数据段，对照它的 Sequence Number 与 Acknowledgement Number，验证“确认号 = 期望收到的下一个字节序号”。
6. 打开 `Statistics → TCP Stream Graphs → Time Sequence (Stevens)`，看吞吐随时间上升的过程（慢启动 → 拥塞避免）。
7. 找重传：过滤器 `tcp.analysis.retransmission`。没出现说明网络太好，可换弱网（手机热点 / 限速）再试。
8. 看连接如何结束：找 FIN/ACK 四次挥手；如果突然中断，会看到 RST。
9. （可选）找零窗口：`tcp.analysis.zero_window`，说明接收方处理不过来、让发送方暂停。

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `tcp` | 只看 TCP |
| `tcp.flags.syn == 1 and tcp.flags.ack == 0` | 所有握手请求 |
| `tcp.stream eq 0` | 只看第 0 条流（包太多时的救命过滤器） |
| `tcp.analysis.retransmission` | 重传 |
| `tcp.analysis.zero_window` | 零窗口通告 |
| `tcp.window_size < 1000` | 窗口很小的时候 |
| `tcp.flags.reset == 1` | 连接被重置 |

## 要交付什么

- 握手三条报文各自的标志位与序号/确认号。
- 该连接的吞吐随时间的变化描述（哪一段涨得快、哪一段平了）。
- 有没有出现重传 / 零窗口，出现时前后各发生了什么。

## 思考题

1. 初始序号为什么是随机的，而不是从 0 开始？
2. 确认号为 N 时，它确认的到底是哪个字节？
3. 快速重传为什么要等到 3 个重复 ACK，而不是 1 个？

## 常见问题

**抓到的全是加密流量，看不到 HTTP？** 现在多数站点是 HTTPS。TCP 这一层照样能看（握手、序号、窗口、重传都不受影响），只是应用层内容需要解密，见 SSL 实验。

**抓不到握手？** 你开始抓包之前连接已经建好了。重新发起一次连接。

**包太多根本看不过来？** 用 `tcp.stream eq N` 只留一条流；`Statistics → Conversations` 可以查出每条流的编号。
""",
    "ws-udp": """# UDP 协议实验

> 对应教材 **Chapter 3 · Transport Layer** ｜ 建议 40 分钟 ｜ 难度 ★★☆

## 这个实验要回答什么

UDP 头部比 TCP 少了什么？为什么 DNS、QUIC、实时音视频都选 UDP？
一个“无连接”的协议，抓包里看到的是什么样子？

## 开始之前

- UDP 没有连接建立过程，抓到的是一堆互不相关的报文，所以要**主动制造几个典型场景**：
  - DNS 查询（端口 53）—— 最容易复现
  - QUIC（HTTP/3，端口 443/UDP）—— 用浏览器访问支持 HTTP/3 的站点
  - 自己发包：Linux/macOS 用 `nc -u`，Windows 可用 PowerShell 的 `UdpClient`
- 注意 `ping` **不产生 UDP**（它走的是 ICMP），别用它来制造 UDP 流量。

## 实验步骤

1. 开始抓包，显示过滤器填 `udp`。
2. 触发流量：`nslookup www.baidu.com`，再让浏览器访问一个支持 HTTP/3 的网站。
3. 点开一个 UDP 报文，记录四个头部字段：Source Port、Destination Port、Length、Checksum。
4. **核对 Length**：UDP 长度 = 8 字节头部 + 数据长度。用下面的报文总长反推数据部分有多长，验证字段值对不对。
5. 找一个 DNS 响应，看它的 UDP 长度有没有超过 512 字节，有没有被分片。
6. 把显示过滤器换成 `udp.port == 53`，只留 DNS，统计这次一共发了几个查询、收到几个响应。
7. 找 QUIC 流量：过滤器 `quic`，对比它和普通 UDP 在 Wireshark 里显示上的差别（Wireshark 会把它识别成 QUIC 而不是裸 UDP）。

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `udp` | 只看 UDP |
| `udp.port == 53` | DNS |
| `udp.length > 512` | 较大的 UDP 报文 |
| `dns` / `quic` | 按应用层协议识别 |
| `udp.stream eq 0` | 只看一组收发 |
| `udp and not quic` | 排除 QUIC，只看“裸”UDP |

## 要交付什么

- 这次抓包里 UDP 报文按目的端口的分布（哪些协议在用 UDP）。
- 选一个报文，写出四个头部字段的值，并用报文总长验证 Length 字段。

## 思考题

1. UDP 校验和是“可选”的，为什么可以不要？IPv4 里怎么表示“没有算校验和”？
2. IPv6 里 UDP 校验和还是可选的吗？
3. DNS 超过 512 字节时为什么要考虑换 TCP，而不是让 UDP 分片？

## 常见问题

**UDP 报文很少？** 很多基于 UDP 的应用都加了密，Wireshark 里看起来只是乱码。用 DNS 和 QUIC 最容易观察。

**想看“裸 UDP”但全被识别成 QUIC？** 新版 Wireshark 会自动把 443/UDP 认成 QUIC，用 `udp and not quic` 排掉。

**抓到的 UDP 长度都是 0 或很小？** 那是空载荷的保活 / 探测报文，找数据报文再看。
""",
    "ws-ip": """# IP 协议实验

> 对应教材 **Chapter 4 · Network Layer: Data Plane** ｜ 建议 50 分钟 ｜ 难度 ★★★

## 这个实验要回答什么

IP 数据报头里每个字段到底干什么用？TTL 怎么防止环路？
数据报什么时候会分片？IPv4 和 IPv6 的头部差在哪里？

## 开始之前

- 抓包位置决定了你能看到什么：在你自己机器上抓，看到的是“原始发送 + 最终接收”的包，地址不会中间变化。
- 想看到 TTL 递减的效果，需要 `tracert` / `traceroute` 帮忙。

## 实验步骤

1. 开始抓包，显示过滤器填 `ip`。
2. 另开一个终端执行 `ping 1.1.1.1`（Windows：`ping -n 4 1.1.1.1`），产生一批 IP 报文。
3. 停止捕获，挑一个报文展开 Internet Protocol Version 4，逐个记录：
   Version、Header Length、Total Length、Identification、Flags、Fragment offset、TTL、Protocol、Header checksum、Source / Destination Address。
4. **验证字段单位**：Header Length 的单位是 4 字节（值为 5 就是 20 字节），Total Length 的单位是 1 字节。用它们核对“头部 + 数据 = 总长”。
5. 看 Protocol 字段的值（1=ICMP、6=TCP、17=UDP），对照你在列表里看到的协议名。
6. 执行 `tracert -d 1.1.1.1`（Linux/macOS：`traceroute -n 1.1.1.1`），观察 TTL 从 1 开始递增，以及沿途路由器回的 ICMP 超时报文。
7. **找分片**：过滤器 `ip.flags.mf == 1 or ip.fragment.offset > 0`。现代网络大多不会分片，可以主动制造：
   `ping -l 2000 1.1.1.1`（Windows）/ `ping -s 2000 1.1.1.1`（Linux/macOS）。
8. （可选）过滤器换 `ipv6`，对比 IPv6 头部：固定 40 字节、没有首部校验和、路由器不分片。

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `ip` | 只看 IPv4 |
| `ip.addr == 1.1.1.1` | 与某个地址有关的全部报文 |
| `ip.ttl < 10` | TTL 较小的（快到目的地或经过很多跳） |
| `ip.flags.df == 1` | 设置了“不分片” |
| `ip.flags.mf == 1` | 后面还有分片 |
| `ip.fragment.offset > 0` | 非首片分片 |
| `ipv6` | 只看 IPv6 |

## 要交付什么

- 一个 IPv4 报文的**完整头部字段表**（每个字段的值 + 它代表什么）。
- TTL 值与 `tracert` 跳数的对应关系，说明 TTL 主要用来做什么。
- 有没有观察到分片？如果有，分片之间靠什么字段重组？

## 思考题

1. TTL 字面意思是“秒”，实际按什么递减？
2. IPv6 为什么去掉了首部校验和？这样做有什么代价？
3. 分片在哪里重组？为什么路由器默认不分片（IPv6 直接禁止）？

## 常见问题

**看不到分片？** 正常。路径 MTU 发现和 MSS 协商已经避免了大包分片。用 `ping -l 2000` 之类的超大包强制制造。

**只看到本机收发的包，看不到别人的？** 正常，除非你所在交换机配了镜像端口，否则抓不到别人的流量。

**Header Length 一直是 5？** 没有 IP 选项时就是 5（20 字节），这是最常见的值。
""",
    "ws-icmp": """# ICMP 协议实验

> 对应教材 **Chapter 5 · Network Layer: Control Plane** 5.6 节 ｜ 建议 40 分钟 ｜ 难度 ★★☆

## 这个实验要回答什么

`ping` 和 `traceroute` 底层发的都是 ICMP，分别是哪种类型？
路由器回差错报文时带回了多少原始信息，为什么这些信息足够让 traceroute 工作？

## 开始之前

- 需要能对外发包（普通家用网络就行）。
- 有些网络或目标会禁 ICMP，某次 ping 不通不代表实验做不了，换一个目标即可。

## 实验步骤

1. 开始抓包，显示过滤器填 `icmp`。
2. 执行 `ping 1.1.1.1`（Windows：`ping -n 4 1.1.1.1`），停止捕获。
3. 找到成对的 **Echo Request（Type 8）** 与 **Echo Reply（Type 0）**，记录 Identifier、Sequence Number、Data 长度，以及 Wireshark 算出的往返时间。
4. 看数据部分的内容：`ping` 默认填的是一串递增模式，这也是它能检测出数据损坏的原因。
5. 执行 `tracert -d 1.1.1.1`（Linux/macOS：`traceroute -n 1.1.1.1`），你会看到每一跳回来的 **Time-to-live exceeded（Type 11）**。
6. 展开一个 Time exceeded 报文，往里看它的 IP 载荷：里面装着**被丢弃那个包的 IP 头 + 前 8 字节**。这正是 traceroute 能知道“这一跳是谁”的原因。
7. 制造一次不可达：`ping 1.1.1.1 -i 1`（或访问一个不存在的端口），观察 **Destination unreachable（Type 3）** 及其 Code 字段的取值。
8. 统计：这次抓包中 ICMP 各类型的数量分布。

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `icmp` | 只看 ICMP（不含 ICMPv6） |
| `icmp.type == 8` / `== 0` | Echo 请求 / 应答 |
| `icmp.type == 11` | TTL 超时 |
| `icmp.type == 3` | 目的不可达 |
| `icmp.ident == 0x1234` | 按 Identifier 认出发起方 |
| `icmpv6` | ICMPv6（另一套，别和 ICMP 混） |

## 要交付什么

- `ping` 的往返统计：发了几个、回了几个、各自 RTT。
- `tracert` 每一跳的 IP 与回包类型（哪些是 Type 11、哪一跳是 Type 0）。
- 差错报文里携带的原始信息具体是什么，为什么只需要这么少。

## 思考题

1. traceroute 是怎么知道每一跳的地址的？它靠的是谁的“错误”？
2. 为什么有的跳显示为 `*`？这时发生了什么？
3. ICMP 差错报文只带原始 IP 头 + 8 字节，够用吗？为什么不做成带回整包？

## 常见问题

**ping 不通，但抓到了 Request 没有 Reply？** 目标或中间设备禁了 ICMP，这是很常见的策略，换个目标即可。

**`tracert` 特别慢？** 每一跳都要等超时确认，属正常。加 `-d` 关掉反向解析会快一些。

**过滤器 `icmp` 抓不到 IPv6 的报文？** ICMPv6 是独立协议，用 `icmpv6`。
""",
    "ws-dhcp": """# DHCP 协议实验

> 对应教材 **Chapter 4 · Network Layer: Data Plane** ｜ 建议 40 分钟 ｜ 难度 ★★☆

## 这个实验要回答什么

一台新机器插上网线后，是怎么自动拿到 IP、网关和 DNS 的？
四步交互各自解决什么问题？为什么客户端一开始得用 `0.0.0.0` 当源地址？

## 开始之前

- 这个实验需要你能**触发一次 DHCP 交互**：
  - 笔记本连 Wi-Fi / 网线时最方便（可以直接断开重连）
  - 云服务器、大部分虚拟机里抓不到（地址由平台下发），这种情况请看实验文档里给出的官方 trace
- 记住当前网络配置，方便之后对比。

## 实验步骤

1. 先记下当前配置：`ipconfig /all`（Windows）或 `ip addr` + `ip route`（Linux）。
2. 开始抓包，显示过滤器填 `bootp`（Wireshark 里 DHCPv4 的协议名就是 BOOTP）。
3. **释放并重新获取**：
   - Windows：`ipconfig /release` 然后 `ipconfig /renew`
   - Linux：`sudo dhclient -r && sudo dhclient -1`
   - 或者干脆断开 Wi-Fi 再重连
4. 停止捕获，找到四条报文：**Discover → Offer → Request → ACK**（看 Options 里的 DHCP Message Type）。
5. 看 Discover 的地址与端口：源 `0.0.0.0:68`，目的 `255.255.255.255:67`。想清楚“还没有 IP 的机器是怎么把包发出去的”。
6. 在 Offer / ACK 里展开 Option，逐条记录：Subnet Mask(1)、Router(3)、DNS(6)、Lease Time(51)、Server Identifier(54)。
7. 对比第 1 步记下的配置，确认它们就是从这里来的。
8. （可选）看一次续租：租期过半时客户端会单播发 Request，服务器回 ACK，这次没有 Discover/Offer。

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `bootp` | 只看 DHCPv4 |
| `bootp.option.dhcp == 1` | Discover |
| `bootp.option.dhcp == 2` | Offer |
| `bootp.option.dhcp == 3` | Request |
| `bootp.option.dhcp == 5` | ACK |
| `udp.port == 67 or udp.port == 68` | 按端口筛 |

## 要交付什么

- 四步报文的源 / 目的 IP 与端口对照表。
- 从 Offer 里拿到的完整网络配置（掩码、网关、DNS、租期）。
- 租期是多长？客户端会在什么时候开始续租？

## 思考题

1. 为什么 Discover 用 `0.0.0.0` 作源地址、用广播作目的地址？
2. Offer 之后为什么还要一次 Request？它在确认什么？
3. 如果局域网里接了两台 DHCP 服务器，会发生什么？

## 常见问题

**抓不到 `bootp`？** 说明所在网络不需要 DHCP（比如平台直通、静态配置），换成手机热点或家里路由器重试。

**只看到 ACK，看不到前三条？** 抓包开始得太晚了。先开始抓包，再去 renew。

**Linux 上没有 `dhclient`？** 用 `sudo networkctl reconfigure <接口>`，或者直接重连网卡。
""",
    "ws-nat": """# NAT 实验

> 对应教材 **Chapter 4 · Network Layer: Data Plane** ｜ 建议 50 分钟 ｜ 难度 ★★★

## 这个实验要回答什么

家里只有一个公网 IP，为什么手机、电脑、电视能同时上网？
NAT 表里到底存了什么？为什么外面的机器主动连不进来？

## 开始之前

**这个实验需要两条路，先看清楚：**

- **自己在机器上抓包，只能看到改写后的一侧。** 因为地址改写在路由器内部完成，你自己这台机器看不到转换过程。
- **要看完整的改写过程，需要同时抓到 NAT 两侧的官方 trace**（教材提供的抓包文件里就有）：
  下载地址 <https://www-net.cs.umass.edu/wireshark-labs/wireshark-traces.zip>，
  具体用哪个文件以你正在读的实验文档为准。

另外注意：**私网地址段**是 `10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16` —— 认得出这个，你就能一眼分出哪侧是内网。

## 实验步骤

**A. 自己抓包，先建立直觉**

1. 记下自己的内网地址：`ipconfig`（Windows）或 `ip addr`（Linux/macOS），通常是 `192.168.x.x`。
2. 查自己的公网地址：浏览器打开 <https://ifconfig.me>，或 `curl ifconfig.me`。
3. 开始抓包，显示过滤器填 `ip.addr == <你的内网IP>`，然后访问一个网站。
4. 观察你发出的包：**源 IP 就是你的内网地址** —— 说明改写发生在路由器上，你这侧是看不到的。

**B. 用官方 trace 看改写**

5. 打开 trace 里 NAT 实验对应的抓包文件，找到**内网侧**与**公网侧**同一时刻的同一个连接（看端口号和时序能对上）。
6. 对比两侧的 源 IP:端口 与 目的 IP:端口，填出下面这张 NAT 转换表。
7. 用 `Statistics → Conversations` 看：这个公网 IP 上同时承载了多少条内网连接？

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `ip.addr == 192.168.1.100` | 锁定内网那台机器 |
| `tcp.flags.syn == 1 and tcp.flags.ack == 0` | 每次新建连接（最容易看出端口分配规律） |
| `tcp.port == 80` | 只看某个服务的连接 |
| `ip.src == 203.0.113.5` | 只看某个地址发出的包 |

## 要交付什么

| 方向 | 内网侧 | 公网侧 |
| --- | --- | --- |
| 源 IP:端口 | | |
| 目的 IP:端口 | | |

再补一句话：这个公网 IP 同时承载了多少条内网连接，NAT 靠什么区分它们。

## 思考题

1. NAT 为什么必须改写端口，只改 IP 不行吗？
2. NAT 对 P2P 下载、对外提供服务意味着什么？为什么需要打洞或端口映射？
3. 为什么说 NAT“破坏了端到端原则”？它带来了什么好处作为交换？

## 常见问题

**自己抓包看不到任何地址改写？** 这是正常的，改写发生在路由器内部。要看改写过程必须用官方 trace（同时有两侧抓包）。

**官方 trace 里找不到实验文档说的那个文件？** 以文档里给出的文件名为准；trace 包里同时包含多个实验的文件。

**分不清哪侧是内网、哪侧是公网？** 看地址：私网地址（`10.` / `172.16-31.` / `192.168.`）那侧就是内网。
""",
    "ws-ethernet-arp": """# 以太网与 ARP 实验

> 对应教材 **Chapter 6 · The Link Layer and LANs** ｜ 建议 50 分钟 ｜ 难度 ★★★

## 这个实验要回答什么

以太网帧头里那 6+6 字节的 MAC 地址是哪来的？
IP 地址是怎么“翻译”成 MAC 的？为什么 ARP 请求必须广播，而响应可以单播？

## 开始之前

- 需要你和至少一台设备处于**同一个广播域**（家里路由器、实验室交换机都可以）。
- 查 ARP 缓存的命令：
  - Windows：`arp -a`
  - Linux：`ip neigh`
  - macOS：`arp -a`

## 实验步骤

1. 先看当前 ARP 缓存（命令见上），**记下网关的 MAC 地址**。
2. 开始抓包，显示过滤器填 `arp`。
3. **清掉网关那条缓存**，制造一次真正的 ARP：
   - Windows（管理员）：`arp -d <网关IP>`
   - Linux：`sudo ip neigh del <网关IP> dev <网卡名>`
4. 立刻 `ping <网关IP>`，触发地址解析。
5. 停止捕获，找到 **Request**：目的 MAC 是 `ff:ff:ff:ff:ff:ff`（广播），Target MAC 全 0（还不知道答案）。
6. 找到 **Reply**：它是单播回来的，在里面对比第 1 步记下的网关 MAC，确认一致。
7. 把过滤器换成 `eth`，点开任意一帧，记录帧头：目的 MAC、源 MAC、Type。对照 Type 取值：`0x0800`=IPv4、`0x0806`=ARP、`0x86dd`=IPv6。
8. （可选）找一次“免费 ARP”（gratuitous ARP）：某台设备主动广播自己的映射关系，用于检测地址冲突或宣告变更。

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `arp` | 只看 ARP |
| `arp.opcode == 1` / `== 2` | 请求 / 响应 |
| `eth.dst == ff:ff:ff:ff:ff:ff` | 所有广播帧 |
| `eth.type == 0x0806` | 按类型筛 ARP |
| `eth.src == <MAC>` | 锁定某台设备 |

## 要交付什么

- 一对 ARP 请求 / 响应的全字段（含各地址字段的值）。
- 一个以太网帧的头部字段，以及 Type 值的含义。
- 清缓存前后网关 MAC 的比对结果。

## 思考题

1. 为什么 ARP 请求必须广播？能不能先查表再单播？
2. 如果 ARP 表项永不过期，会出现什么问题？
3. **跨网段**通信时，你发出的帧的目的 MAC 是谁的？为什么不是最终服务器的？

## 常见问题

**`arp -d` 提示权限不足？** 需要管理员 / root。

**清完缓存 ping 一下，还是没看到 ARP？** 顺序问题：先开始抓包，再清缓存，然后马上 ping。

**抓到大量 IPv6 的邻居请求 / 通告？** 那是 ARP 在 IPv6 里的对应物（Neighbor Solicitation / Advertisement），用 `icmpv6` 看，属正常现象。
""",
    "ws-80211": """# 802.11 无线局域网实验

> 对应教材 **Chapter 7 · Wireless and Mobile Networks** ｜ 建议 60 分钟 ｜ 难度 ★★★

## 这个实验要回答什么

802.11 帧和以太网帧差在哪里？为什么无线链路层要单独做确认（ACK）？
一个数据帧从空口上看，完整的样子是什么？

## 开始之前

**先说清楚现实条件：抓 802.11 需要网卡支持监听模式（monitor mode）。**

- Linux + 支持监听的网卡：可以真抓（下面 A 路线）。
- Windows / macOS 的普通网卡：**抓不到管理帧**，系统只给你“伪以太网”帧。这时请走 B 路线。
- A 路线不可用完全不影响做这个实验，B 路线本身就是教材的经典做法。

**官方 trace**：<https://www-net.cs.umass.edu/wireshark-labs/wireshark-traces.zip>
（用哪个文件以你正在读的实验文档为准。）

## 实验步骤

**A. 有监听条件的（Linux，进阶）**

1. 把网卡切到监听模式：`sudo airmon-ng start wlan0`（会多出一个 `wlan0mon`）。
2. 在 Wireshark 里选监听接口开始抓包，显示过滤器填 `wlan`。
3. 用手机连一下 Wi-Fi、打开网页，制造真实流量。
4. 观察三类帧：管理帧（Beacon / Probe / Auth / Assoc）、控制帧（ACK / RTS / CTS）、数据帧。

**B. 用官方 trace（推荐，绝大多数人走这条）**

5. 打开 802.11 实验对应的抓包文件，过滤器 `wlan.fc.type == 0` 只看管理帧。
6. 找一个 **Beacon** 帧（`wlan.fc.subtype == 8`），记录：SSID、支持速率、信道、Beacon interval。
7. 过滤器换成 `wlan.fc.type == 1` 看控制帧，找 **ACK**（subtype 12）。
   想清楚一件以太网没有的事：**无线的每个单播数据帧都要单独被确认**。
8. 过滤器换成 `wlan.fc.type == 2` 看数据帧，展开 802.11 头，和以太网头对比：
   它最多有 **4 个地址字段**（Address 1/2/3/4）、还有 Duration 与 Sequence Control。
9. 如果抓包带 **radiotap** 头，记录信道、信号强度（dBm）、数据率 —— 这是无线特有的“物理层元信息”。

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `wlan` | 只看 802.11 |
| `wlan.fc.type == 0` / `== 1` / `== 2` | 管理 / 控制 / 数据帧 |
| `wlan.fc.subtype == 8` | Beacon |
| `wlan.fc.subtype == 12` | ACK |
| `wlan.ssid == "你的SSID"` | 按 SSID 筛 |
| `radiotap.channel.freq` | 按信道频点筛 |

## 要交付什么

- 一个 Beacon 帧的字段表（SSID、速率、信道、间隔）。
- 一对“数据帧 + 独立 ACK”，说明它和以太网“不确认”的差别。
- 802.11 头比以太网头多出来的字段，以及各地址字段分别在什么场景下使用。

## 思考题

1. 为什么 802.11 需要链路层 ACK，而以太网不需要？
2. RTS/CTS 解决的是什么问题？它有什么代价？
3. 四个地址字段分别在什么拓扑下才会用到？

## 常见问题

**接口列表里没有监听接口？** 网卡或驱动不支持监听模式，走官方 trace 即可，实验效果一样。

**抓到的全是 Beacon，没有数据帧？** 没制造流量，或者信道不对（监听要落在设备实际用的信道上）。

**Windows 上看到的帧“不像 802.11”？** 系统会把无线帧转成伪以太网帧再交给抓包程序，所以看不到 802.11 头。这也是为什么推荐用官方 trace。
""",
    "ws-ssl": """# SSL / TLS 安全实验

> 对应教材 **Chapter 8 · Security in Computer Networks** ｜ 建议 60 分钟 ｜ 难度 ★★★

## 这个实验要回答什么

TLS 握手到底交换了什么？为什么抓到包里看不到明文？
TLS 1.3 相比 1.2 在抓包上有什么明显变化？加密保护了哪些信息、又暴露了哪些？

## 开始之前

- 用 `curl` 最干净（浏览器会并发多条连接、还有连接复用）。
- 想看明文内容，需要让客户端**导出会话密钥**（见步骤 7），这是唯一正当的“解密”方式。

## 实验步骤

1. 开始抓包，显示过滤器填 `tls`（老版本 Wireshark 里叫 `ssl`，两个都试）。
2. 发起一个 HTTPS 请求：`curl -v https://www.example.com`，或浏览器访问任意 HTTPS 站点。
3. 停止捕获，找到 **Client Hello**，记录：TLS 版本、支持的密码套件列表、SNI（明文里的域名）、ALPN（有没有 `h2`）。
4. 找到 **Server Hello**，记录：服务器选中的密码套件、协商出的版本、服务器随机数。
5. 看握手之后的内容，注意这个关键差别：
   - **TLS 1.2**：还能看到 Certificate 明文，能看到证书链与公钥。
   - **TLS 1.3**：Certificate 已经被加密，你只能看到 Application Data。
6. 数一下握手需要几个往返：TLS 1.2 通常 2-RTT，TLS 1.3 只要 1-RTT（会话恢复甚至 0-RTT）。
7. **（强烈推荐）解密看看**：让客户端导出密钥，Wireshark 就能还原明文。
   - Linux / macOS：`export SSLKEYLOGFILE=~/keys.log`，然后**从同一个终端**启动浏览器或用 curl。
   - Windows：设置用户环境变量 `SSLKEYLOGFILE`，然后重启浏览器。
   - Wireshark：`Preferences → Protocols → TLS → (Pre)-Master-Secret log filename` 选中该文件。
   - 顺序很重要：**先开抓包 → 设好变量 → 启动浏览器 → 访问**，只有这次会话的密钥能解这次抓包。
8. 解密之后回看一遍：体会 TLS 保护的是**内容**，而 IP、端口、SNI、报文大小与时序这些**元数据仍然暴露**。

## 过滤器速查

| 过滤器 | 作用 |
| --- | --- |
| `tls` | 只看 TLS |
| `tls.handshake.type == 1` | Client Hello |
| `tls.handshake.type == 2` | Server Hello |
| `tls.handshake.extensions_server_name` | 带 SNI 的握手报文 |
| `tls.record.content_type == 23` | Application Data（加密内容） |
| `tcp.port == 443` | 按端口筛 |

## 要交付什么

- 一次握手的报文顺序表（谁先发、发了什么类型）。
- Client Hello 里的密码套件候选与 SNI；Server Hello 里选中的那一个。
- 能否看到 Certificate？对应的是哪个 TLS 版本？
- 解密前 / 解密后分别能看到什么，列一张对照表。

## 思考题

1. TLS 保护了哪些信息？哪些信息在加密通道之外仍然可见？
2. TLS 1.3 为什么把证书也加密了？这给网络管理带来了什么影响？
3. 如果服务器启用了 ECH（Encrypted Client Hello），SNI 还看得到吗？

## 常见问题

**过滤器 `ssl` 提示无效？** 新版改名成了 `tls`，用 `tls`；两者都试一下最快。

**看不到 Certificate？** 说明你走的是 TLS 1.3，证书已被加密 —— 这是正常的，也是这个实验该观察到的结论之一。

**设了 `SSLKEYLOGFILE` 但解密不生效？** 三个常见原因：变量是在浏览器**启动之后**才设的；抓包与密钥不是同一次会话；Wireshark 里没指定密钥文件路径。

**抓到的全是 QUIC 没有 TLS？** HTTP/3 走 UDP，用 `quic` 过滤器看。
""",
    "sock-smtp": """# Socket 编程练习：SMTP 邮件客户端

> 对应教材 **Chapter 2 · Application Layer** 2.7 节 ｜ 建议 50 分钟 ｜ 难度 ★★☆

## 这个练习在干什么

电子邮件不是“点一下发送”那么神秘 —— 底层就是一段固定格式的 TCP 对话。
你来实现 SMTP 客户端：连接 `127.0.0.1` 上的参考服务器（端口从环境变量 `PORT` 读），
按 SMTP 的规矩依次说 `HELO → MAIL FROM → RCPT TO → DATA → 正文 → QUIT`，
把一封邮件“投递”给服务器。

## 开始之前

- SMTP 是**一问一答**式协议：每发一条命令，服务器回一个三位数状态码（如 `220`、`250`），你要收了应答再发下一条。
- 命令与正文都以 `\\r\\n` 结尾；正文结束的标志是单独一行 `.`。
- 地址固定是 `127.0.0.1`，**端口从环境变量 `PORT` 读**（判题时会注入一个空闲端口）：
  `serverPort = int(os.environ.get("PORT", 2500))`。别写死 25 —— 它是特权端口，
  Linux 上非 root 用户绑不了，判题的参考服务器也不会跑在 25 上。

## 判题会怎么检查

判题程序在 `127.0.0.1` 的 `PORT` 端口起一个参考 SMTP 服务器，运行你的客户端，然后核对
服务器日志里是否**完整收到了这五条命令**：`HELO`、`MAIL`、`RCPT`、`DATA`、`QUIT`。
缺任何一条都判失败（判题结果会写明缺的是哪条）。正文内容随意。

## 实现步骤

1. **连接并收问候** —— `connect(('127.0.0.1', serverPort))`，先 `recv` 服务器发来的 `220` 欢迎行。
2. **逐条发命令** —— 按顺序 `send` 并 `recv`：`HELO`、`MAIL FROM:<发件人>`、`RCPT TO:<收件人>`。
3. **进入正文** —— 发 `DATA`，等 `354` 应答后发送正文。
4. **结束正文** —— 正文后发 `\\r\\n.\\r\\n`（单独一个点），表示“我说完了”。
5. **道别** —— 发 `QUIT`，等服务器回 `221`，关连接。

## 常见问题

**判题说我少了 RCPT / DATA？** 多半是某条命令拼错了，或者没等应答就抢着发下一条。终端里的判题日志会打印服务器实际收到的内容。

**`recv` 卡住不动？** 服务器不会主动断连接。按上面“一问一答”的节奏收，别把 `recv` 放在还没发命令的时候。

**正文里的点被当成结束标志？** SMTP 约定行首单独一个 `.` 就是正文结束，这是协议的一部分，正文里别这么写。
""",
    "sock-proxy": """# Socket 编程练习：Web 代理服务器

> 对应教材 **Chapter 2 · Application Layer** 2.7 节 ｜ 建议 60 分钟 ｜ 难度 ★★★

## 这个练习在干什么

写一个 Web 代理：浏览器不直接连服务器，而是把请求交给你的代理，由代理转给真正的
服务器、再带回结果，还要顺带做**缓存**。这是本组练习里最“像工程”的一个 ——
转发、缓存、多连接都要你自己兜住。

## 开始之前

- 代理从 `sys.argv[1]` 读监听端口（判题用现分配的空闲端口启动它）。
- 源服务器端口从 `sys.argv[2]` 读（判题同样会传一个空闲端口；没传就用默认值 8080）。
  别写死 80 —— 那是宿主机上 nginx 占着的端口，非 root 用户也绑不了。
- 教材的约定：客户端发给代理的请求路径形如 `GET /127.0.0.1/hello.html HTTP/1.0`，
  代理要从中拆出“源服务器地址”和“真正要的文件路径”。

## 判题会怎么检查

判题程序先在空闲端口上起源服务器（那里放了一个带标记的页面），再把你的代理启动在
`sys.argv[1]` 端口上，然后**把请求发给你的代理**，两条都满足才算通过：

1. 能连上你的代理并读到响应；
2. 响应内容里包含源服务器的标记 `PROXY_ORIGIN_HELLO` —— 证明流量真的经过你的代理
   转发到了源服务器再回来，而不是你自己编造的响应。

## 实现步骤

1. **读端口并监听** —— `sys.argv[1]` 拿端口，`bind + listen`，循环 `accept()`。
2. **解析请求** —— 从请求行拆出形如 `/127.0.0.1/hello.html` 的路径，得到源主机与文件名。
3. **查缓存** —— 在本地 `WEB/` 目录缓存拿过的文件：命中就直接回，没命中才去源服务器取。
4. **转发** —— 建一条到 `127.0.0.1` 上源服务器端口（`sys.argv[2]`）的连接，把文件路径以 `GET /hello.html` 转发过去。
5. **回传** —— 把源服务器的响应（至少状态行 + 正文）转给客户端，写缓存，关连接。

## 常见问题

**“无法连接代理”？** 代理没起来或端口没读对。先看终端里你自己的 stderr —— 判题日志会带上它。

**转发了却判不过？** 判题在响应里找 `PROXY_ORIGIN_HELLO` 标记，你的响应必须是源服务器的真实内容，不能自己伪造。

**缓存要做到什么程度？** 判题不检查缓存实现，但教材要求有 —— 至少把“命中 → 直接返回”这条路走通，这也是代理区别于普通转发的核心。
""",
    "sock-icmp": """# Socket 编程练习：ICMP Ping 客户端

> 对应教材 **Chapter 5 · Network Layer: Control Plane** 5.6 节 ｜ 建议 60 分钟 ｜ 难度 ★★★

## 这个练习在干什么

用 Python 的原始套接字（raw socket）实现真正的 `ping`：手搓一个 ICMP Echo Request
报文 —— 包括**亲手算校验和** —— 发出去，再收 Echo Reply、量出 RTT。
这次没有服务器替你模拟，报文长什么样完全由你决定 —— 这正是第 1 章“Ping 命令”
练习背后被我们简化掉的东西。

## 开始之前

- 需要背景：ICMP 报文格式与校验和算法（对应 5.6 节，先看知识卡片）。
- 原始套接字需要 **root / CAP_NET_RAW** 权限才能真的发包。因此本练习的判题
  **不实际发包**，而是静态检查 + 单独验证你的校验和函数（见下）。
- 初始代码里要补全 `sendOnePing` 与 `doOnePing` 两处 TODO。

## 判题会怎么检查

判题程序对你的代码做两件事：

1. **静态结构检查** —— 代码里必须出现原始套接字的创建（`socket(AF_INET, SOCK_RAW, ...)`）、
   ICMP Echo Request 报文头的构造（type=8、code=0、id、sequence）与 `sendto` 发送逻辑；
2. **校验和实测** —— 把你的 `checksum` 函数单独放进沙箱执行一次，用固定的 8 字节
   ICMP 头（type=8, code=0, id=1, seq=1）喂给它，结果必须与参考答案一致。

所以哪怕你写不出完整 ping，**先把校验和写对**也有一条检查能过。

## 实现步骤

1. **打包报文头** —— `struct.pack("bbHHh", type, code, checksum, id, sequence)`，Echo Request 是 type=8、code=0。
2. **算校验和** —— 先把 checksum 字段按 0 打包，对 `header + data` 求校验和（相邻 16 位相加、进位回卷、取反），写回后 `socket.htons()` 转字节序。
3. **建原始套接字** —— `socket.socket(AF_INET, SOCK_RAW, socket.getprotobyname("icmp"))`。
4. **发送** —— `sendto(packet, (destAddr, 1))`（ICMP 的“端口”位置通常填 1）。
5. **接收与 RTT** —— `recvfrom(1024)` 收 Echo Reply，减去发送时间得 RTT；返回报文带 IP 头，取 ICMP 部分时注意偏移。
6. **本地自测** —— 原始套接字需要管理员权限：以管理员身份跑终端再 `python ch5_icmp.py 1.1.1.1`。

## 常见问题

**判题不实际发包，那我怎么验证程序对不对？** 判题用静态检查 + 校验和比对兜底；你自己在本地用管理员权限 ping 一个真实地址自测。

**校验和总不对？** 两个经典坑：忘了先把 checksum 字段置 0 再计算；结果没有用 `htons` 转成网络字节序。

**`getprotobyname("icmp")` 返回什么？** ICMP 的协议号 1，等于告诉原始套接字“我只收/发 ICMP”。
""",
}

# --------------------------------------------------------------------------
# 分级提示（前端“提示”按钮逐级揭示；下标顺序即揭示顺序，最后一步之前都是引导）
# --------------------------------------------------------------------------

HINTS: dict[str, list[str]] = {
    "sock-pinger": [
        "先建一个 UDP socket：`socket.socket(socket.AF_INET, socket.SOCK_DGRAM)`，并用 `sock.settimeout(1.0)` 设 1 秒接收超时。",
        "发送前记录 `time1 = time.time()`，把 `f\"Ping {i} {time1}\".encode()` 用 `sock.sendto(data, (SERVER_NAME, port))` 发出去。",
        "用 `sock.recvfrom(2048)` 收回显（返回 `(data, addr)`），`RTT = time.time() - time1`；捕获 `socket.timeout` 并打印 `lost`。",
    ],
    "sock-web-client": [
        "用 `socket.socket(socket.AF_INET, socket.SOCK_STREAM)` 建 TCP socket，然后 `connect(('127.0.0.1', serverPort))`（serverPort 从环境变量 `PORT` 读）。",
        "构造请求 `f\"GET {path} HTTP/1.1\\r\\nHost: {SERVER_NAME}\\r\\nConnection: close\\r\\n\\r\\n\"`，用 `send()` 发出。",
        "循环 `recv(4096)` 直到返回空串（表示连接已关闭），每段都用 `print(..., end='')` 打印。",
    ],
    "sock-web": [
        "建 TCP socket：`socket(AF_INET, SOCK_STREAM)`，`bind(('', serverPort))`（serverPort 从环境变量 `PORT` 读），`listen(1)`，然后循环 `accept()`。",
        "`recv(1024)` 读请求，用 `message.split()[1]` 取出文件名，`open(filename[1:])` 打开并 `read()` 内容。",
        "文件存在就发 `HTTP/1.1 200 OK` + 内容；`IOError` 则发 `HTTP/1.1 404 Not Found`，最后 `connectionSocket.close()`。",
    ],
    "sock-pinger-server": [
        "建 UDP socket：`socket(AF_INET, SOCK_DGRAM)`，`bind(('', 12000))`，并用 `random.seed(42)` 固定丢包模式。",
        "循环 `recvfrom(1024)` 收报文和地址，用 `message.upper()` 转大写。",
        "`rand = random.randint(0, 10)`，若 `rand < 4` 就 `continue` 丢包，否则 `sendto(message, address)` 回显。",
    ],
    "sock-smtp": [
        "建 TCP socket，`connect(('127.0.0.1', serverPort))`（serverPort 从环境变量 `PORT` 读），先收 `220` 问候。",
        "依次 `send` 并 `recv`：`HELO`、`MAIL FROM`、`RCPT TO`、`DATA`，每步收响应。",
        "发送正文 + `\\r\\n.\\r\\n`，再发 `QUIT`，每次收响应并打印。",
    ],
    "sock-proxy": [
        "从 `sys.argv[1]` 读端口，建 TCP socket，`bind(('', port))` + `listen`，循环 `accept()`。",
        "`recv(1024)` 读请求，用 `message.split()[1].partition('/')[2]` 取出文件名。",
        "先查 `WEB/` 缓存；未命中则连源服务器（端口取 `sys.argv[2]`）取内容、写缓存，再把 `200 OK` 响应回传客户端。",
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
