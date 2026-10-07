# <span style="color: rgb(var(--brand));">网络诊断工具：ping · traceroute · La/R</span>

当网页打不开、游戏卡成幻灯片、视频转圈圈时，第一反应不应该是“重启路由器”，而是先“量一量”网络到底哪里出了问题。本节介绍的三个诊断利器——**ping**、**traceroute** 与**流量强度 La/R**——就是你的“听诊器”和“体检报告”，它们分别回答三个问题：

- **ping**：我和对端“通不通”？往返要多久？丢包多不多？
- **traceroute**：数据包在路上“经过了哪些站”？卡在哪一站了？
- **La/R**：这条链路“是不是堵了”？堵到什么程度了？

## <span style="color: rgb(var(--brand-dark));">ping：给对端“敲门”</span>

`ping` 的原理很简单：向目标主机发一个 **ICMP Echo Request（回显请求）** 报文，目标主机收到后回一个 **ICMP Echo Reply（回显应答）**。你从发出到收到回应的这段时间，就是往返时延 **RTT（Round-Trip Time）**。

```bash
# Linux / macOS：发 4 个探测包后停止
ping -c 4 www.example.com

# Windows：默认发 4 个（-n 指定次数）
ping -n 4 www.example.com
```

一段典型的输出长这样：

```text
PING www.example.com (93.184.216.34): 56 data bytes
64 bytes from 93.184.216.34: icmp_seq=0 ttl=52 time=18.6 ms
64 bytes from 93.184.216.34: icmp_seq=1 ttl=52 time=19.1 ms
64 bytes from 93.184.216.34: icmp_seq=2 ttl=52 time=18.9 ms
64 bytes from 93.184.216.34: icmp_seq=3 ttl=52 time=18.7 ms

--- www.example.com ping statistics ---
4 packets transmitted, 4 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 18.6/18.8/19.1/0.2 ms
```

怎么读这份“体检报告”：

| 指标 | 含义 | 健康表现 |
| --- | --- | --- |
| `time=XX ms` | 单次往返时延（RTT） | 越小越好，内网通常 <1ms，跨洲可能上百 ms |
| `ttl=52` | 回包里的剩余生存时间 | 初始值（64/128/255）减去收到的值 ≈ 经过的跳数 |
| `packet loss` | 丢包率 | 0% 最好，持续高丢包说明链路拥堵或故障 |
| `stddev` | RTT 抖动 | 越小越稳定，抖动大时语音/游戏等实时应用会卡 |

> **小贴士**：`ping` 测的是“通不通、快不快”，但它不告诉你“卡在哪一段”。想知道具体卡在哪一站，得用下面这个。

## <span style="color: rgb(var(--brand-dark));">traceroute：看数据包“一路怎么走”</span>

`ping` 只知道“到了没到”，而 `traceroute`（Windows 下叫 `tracert`）能把你和目的地之间**每一跳路由器**都列出来。

它的原理很巧妙，利用了 IP 报头里的 **TTL（Time To Live）** 字段：每经过一个路由器，TTL 就减 1；当 TTL 减到 0 时，路由器会丢弃该包，并向源地址回一个 **ICMP Time Exceeded（超时）** 报文。于是：

1. 先发一个 `TTL=1` 的包 → 第一跳路由器把它拦下并回“超时” → 你就知道了第一跳是谁；
2. 再发 `TTL=2` → 第二跳回“超时”；
3. 依此类推，直到抵达目标，目标回一个“到达”信号。

```bash
# Linux / macOS（默认 UDP 探测，-I 改用 ICMP）
traceroute www.example.com

# Windows
tracert www.example.com
```

典型输出：

```text
traceroute to www.example.com (93.184.216.34), 64 hops max
 1  192.168.1.1 (192.168.1.1)  1.2 ms  0.9 ms  1.1 ms
 2  10.10.0.1 (10.10.0.1)  4.5 ms  4.2 ms  4.8 ms
 3  61.152.1.1 (61.152.1.1)  6.3 ms  6.1 ms  6.5 ms
 ...
 9  93.184.216.34 (93.184.216.34)  18.7 ms  18.9 ms  18.6 ms
```

每一行代表一跳，三个时间是对这一跳**发了三个探测包**分别测到的 RTT。如果你在某一行看到三个 `* * *`，说明这一跳的路由器**不回应**（可能被防火墙过滤，或这一跳就是超时），不代表一定故障——只要后面还能继续走到目的地就没事。

> **怎么定位故障**：如果从某一行开始后面全是 `* * *`，说明大概率卡在这一跳之后的链路上，问题往往出在你家网关到运营商之间，或运营商之间的互联点。

## <span style="color: rgb(var(--brand-dark));">流量强度 La/R：量化“堵不堵”</span>

前面两个是“测量工具”，这是一个“理论公式”。回到第一章讲性能时提到的排队时延——它一会短一会长，全看链路忙不忙。衡量“忙不忙”的指标就是**流量强度（traffic intensity）**：

```text
La/R = (每秒到达的数据量) / (链路每秒能发送的数据量)
```

- **L**：每个分组的平均长度（bit）
- **a**：每秒平均到达的分组数（个/秒）
- **R**：链路传输速率（bit/s）

套进三种情况：

| La/R | 含义 | 现象 |
| --- | --- | --- |
| 接近 0 | 链路很空 | 排队时延 ≈ 0，飞快 |
| 接近 1 | 来车速度 ≈ 处理速度 | 排队时延暴涨，开始堵车 |
| 大于 1 | 进得多出得少 | 队列越积越长，最终**丢包** |

这个公式就是理解“为什么高峰期网会卡”的钥匙：不是运营商在偷懒，而是那一瞬间 `La/R` 逼近甚至超过了 1。

## <span style="color: rgb(var(--brand-dark));">什么时候用哪一个</span>

| 场景 | 先用 | 说明 |
| --- | --- | --- |
| 网页/游戏打不开，怀疑连不上 | `ping` | 看通不通、丢不丢包 |
| 能 ping 通但很慢，想找瓶颈在哪段 | `traceroute` | 逐跳定位时延跳变 |
| 想从理论上理解拥堵与丢包 | La/R | 配合第一章性能指标一起看 |

这三个工具正好呼应第一章的**时延、丢包、吞吐量**，也和第 4、5 章的 **ICMP 协议**直接相关（ping 和 traceroute 底层用的都是 ICMP）。建议先在第一章的“Ping 命令引导”里亲手跑一遍 `ping`，再到第五章的“ICMP Ping 客户端”实验里，自己动手构造一个 ICMP Echo Request 报文。
