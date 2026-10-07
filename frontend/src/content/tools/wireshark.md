# <span style="color: rgb(var(--brand));">Wireshark：网络抓包分析</span>

如果说 `ping` 是“量体温”，那 Wireshark 就是给网络做“全身 CT”——它能把你网卡上进进出出的**每一个数据包**都抓下来，然后逐层拆开给你看：从最外面的以太网帧，到里面的 IP 包，再到 TCP/UDP 段，最后到 HTTP、DNS 这样的应用层报文，一层不落。

## <span style="color: rgb(var(--brand-dark));">它是什么：包嗅探器</span>

Wireshark 是一个**数据包分析器（packet analyzer / sniffer）**。它把网卡切换到“混杂模式（promiscuous mode）”，这样网卡不再只收“发给自己的包”，而是把网络上**所有经过的包**都照单全收，再由 Wireshark 一个个解析、展示。

在学习计算机网络时，它的价值在于：课本上画的协议字段（首部、标志位、序列号……）不再是抽象符号，而是你能在抓包里**亲眼看到的一行行真实数据**。

## <span style="color: rgb(var(--brand-dark));">认识界面：三个面板</span>

打开 Wireshark 抓一段包，你会看到经典的三栏布局：

| 面板 | 位置 | 作用 |
| --- | --- | --- |
| 包列表（Packet List） | 顶部 | 每个包一行，显示序号、时间、源/目的地址、协议、长度、摘要 |
| 包详情（Packet Details） | 中部 | 选中某个包后，**逐层展开**它的协议字段（以太网 → IP → TCP → HTTP） |
| 字节视图（Packet Bytes） | 底部 | 这个包的原始字节（十六进制 + ASCII），最底层的真相 |

点开“包详情”里的任意一层，底部字节视图会同步高亮对应的字节——这就是“分层封装”最直观的证明：**外层协议的负载，就是内层协议的整个报文**。

## <span style="color: rgb(var(--brand-dark));">过滤器：从海量包里捞出你想要的</span>

一次抓包可能瞬间就有成千上万个包，全靠肉眼找会疯掉。Wireshark 提供两类过滤器：

**① 捕获过滤器（Capture Filter）**：在抓包前就设好，只抓符合条件的包，用的是 BPF 语法：

```text
host 192.168.1.1        # 只抓与该主机相关的包
tcp port 80             # 只抓 80 端口的 TCP 包
udp                     # 只抓 UDP 包
```

**② 显示过滤器（Display Filter）**：抓完后再筛选，功能更强大，用的是 Wireshark 自己的语法：

```text
http                    # 只看 HTTP 报文
dns                     # 只看 DNS 报文
ip.addr == 10.0.0.1     # 只看与某 IP 相关的包
tcp.port == 443         # 只看 443 端口的 TCP
tcp.flags.syn == 1      # 只看 TCP 三次握手的 SYN 包
http.request.method == "GET"   # 只看 HTTP GET 请求
```

> **新手建议**：先用捕获过滤器缩小范围，再用显示过滤器精确定位。过滤器是 Wireshark 最重要的基本功。

## <span style="color: rgb(var(--brand-dark));">进阶用法：跟着一条连接走</span>

抓包时最常用的一个操作是**跟踪流（Follow Stream）**：右键某个包 → `Follow` → `TCP Stream`（或 `HTTP Stream`），Wireshark 会把这条连接上的所有包按顺序拼起来，还原成一段完整对话——就像把一次通话的录音回放出来。看 HTTP 请求/响应、看 DNS 查询/应答，用这一招最直观。

另外几个高频功能：

- **Protocol Hierarchy（协议层级统计）**：一图看清这次抓包各层协议各占多少。
- **Conversations / Endpoints（会话 / 端点）**：谁和谁在通信、流量多少。
- **IO Graph**：画出流量随时间变化的曲线。

## <span style="color: rgb(var(--brand-dark));">TLS/HTTPS：抓包的“盲区”</span>

一个必须知道的限制：**HTTPS 的报文主体是加密的**。你抓到的 HTTPS 包，只能看到外面的 TLS 握手（ClientHello / ServerHello）和加密后的乱码，看不到里面的明文 HTTP 内容。这恰恰是 TLS 的意义——保证机密性。想分析明文 HTTP，得抓 HTTP（80 端口）的流量。

## <span style="color: rgb(var(--brand-dark));">跟着课程实验一起练</span>

本站各章节都配有对应的 Wireshark 实验，覆盖了协议栈的每一层：

| 章节 | 实验 |
| --- | --- |
| 第 1 章 网络基础 | Wireshark 入门 |
| 第 2 章 应用层 | HTTP、DNS |
| 第 3 章 运输层 | TCP、UDP |
| 第 4 章 网络层数据平面 | IP、DHCP、NAT |
| 第 5 章 网络层控制平面 | ICMP |
| 第 6 章 链路层 | 以太网与 ARP |
| 第 7 章 无线网络 | 802.11 |
| 第 8 章 网络安全 | SSL/TLS |

建议先完成第 1 章的“Wireshark 入门”熟悉基本操作，再按章节顺序逐个解锁。每个实验都会告诉你抓什么、过滤什么、观察哪个字段，把课本知识和真实报文对上号。
