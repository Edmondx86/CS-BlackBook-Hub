# <span style="color: rgb(var(--brand));">Cisco Packet Tracer：网络拓扑仿真</span>

想亲手搭一个“网络”出来，又不可能真的买一堆路由器和交换机——**Cisco Packet Tracer** 就是为此而生的**网络拓扑仿真环境**。你可以像搭积木一样拖出路由器、交换机、主机，用网线把它们连起来，然后在“仿真模式”下一步步看着数据包在拓扑里转发。它是思科网络学院（Cisco Networking Academy）的官方教学工具。

## <span style="color: rgb(var(--brand-dark));">它能做什么</span>

- **拖拽搭建拓扑**：从设备栏拖出 PC、交换机、路由器、服务器，用线连成任意规模的网络。
- **真实设备仿真**：内置 Cisco IOS 的命令行（CLI），可以像真机一样敲 `enable`、`configure terminal` 等命令来配置路由器。
- **逐步观察转发**：切到 **Simulation 模式**，一个包一个包地“慢放”，看它从源到目的经过每一跳时，MAC 地址、IP 地址、TTL 是怎么变化的。
- **协议可视化**：直观看到 ARP 请求/应答、ICMP Echo、TCP 三次握手等协议交互。

## <span style="color: rgb(var(--brand-dark));">认识常用设备</span>

| 设备 | 作用 |
| --- | --- |
| PC / 服务器 | 发送/接收数据的端系统，可配 IP、网关、DNS |
| 交换机（Switch） | 二层转发，学习 MAC 地址表，在局域网内转发帧 |
| 路由器（Router） | 三层转发，根据路由表在不同网络间转发分组 |
| 集线器（Hub） | 无脑广播所有帧（用于对比交换机，已淘汰） |
| 线缆 | 直通线（异类设备）、交叉线（同类设备）、串口线（路由器互联） |

## <span style="color: rgb(var(--brand-dark));">快速上手：搭一个最小网络</span>

以“两台 PC + 一台交换机 + 一台路由器”为例：

1. **拖设备**：拖两台 PC、一台 2960 交换机、一台 2911 路由器到工作区。
2. **连线**：用直通线把 PC 接到交换机，再用直通线把交换机接到路由器（接口亮绿灯表示连通）。
3. **配 IP**：点开 PC → `Desktop` → `IP Configuration`，给每台 PC 设好 IP 和网关。
4. **配路由器**：点开路由器 → `CLI` 标签页，进入接口配置：

```text
Router> enable
Router# configure terminal
Router(config)# interface GigabitEthernet0/0
Router(config-if)# ip address 192.168.1.1 255.255.255.0
Router(config-if)# no shutdown
Router(config-if)# end
```

5. **测试连通**：回到 PC 的 `Command Prompt` 敲 `ping 192.168.1.2`，能 ping 通就说明搭成了。
6. **看转发**：切到 **Simulation 模式**，再 ping 一次，点“播放”，就能一帧一帧地看到分组如何在拓扑里转发。

## <span style="color: rgb(var(--brand-dark));">和课程怎么对应</span>

Packet Tracer 最适合配合第 4～6 章一起看：

| 章节 | 你可以观察什么 |
| --- | --- |
| 第 4 章 网络层数据平面 | 路由器查转发表转发分组、IP 地址与子网 |
| 第 5 章 网络层控制平面 | 在路由器上配静态路由 / RIP / OSPF，看路由表 `show ip route` |
| 第 6 章 链路层 | 交换机学习 MAC 地址表、ARP 请求广播找 MAC |

尤其是路由这一块，课本上的“转发 vs 路由选择”很抽象，但你在 Packet Tracer 里 `show ip route` 看到真实路由表、配一条 OSPF 再看路由自动收敛，概念立刻就落地了。

## <span style="color: rgb(var(--brand-dark));">和 Wireshark 的分工</span>

两个工具别搞混：**Wireshark 是“观察”真实网络的包**，**Packet Tracer 是“搭建”一个虚拟网络**。一个负责看，一个负责搭——前者看真实流量，后者在仿真环境里动手做实验。学转发和路由用 Packet Tracer，学协议字段和抓包用 Wireshark，配合起来就是完整的一条学习链。
