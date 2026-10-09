# 作业要求 PDF（不随仓库分发）

这个目录里的 `*.pdf` 是各实验的作业要求文档，**不进版本库**。

## 为什么不入库

单个 2 MB 上下，11 个 Wireshark 实验文档合计约 24 MB —— 放进仓库会让 `.git`
从 6 MB 涨到 30 MB，每次 clone 都要拖下来，而它们改动极少、和代码也不同步。

## 文件清单

| 文件 | 对应实验 |
| --- | --- |
| `ws-intro.pdf` | Wireshark 入门 |
| `ws-http.pdf` / `ws-dns.pdf` / `ws-tcp.pdf` / `ws-udp.pdf` / `ws-ip.pdf` | 各协议抓包实验 |
| `ws-icmp.pdf` / `ws-dhcp.pdf` / `ws-nat.pdf` / `ws-ethernet-arp.pdf` | 网络层与链路层实验 |
| `ws-80211.pdf` / `ws-ssl.pdf` | 无线与 TLS 实验 |
| `web_server.pdf` / `udp_pinger.pdf` / `sock-smtp.pdf` / `sock-proxy.pdf` / `sock-icmp.pdf` | Socket 编程练习 |

路径与 lab id 的对应关系见 `backend/app/mock_data.py` 里的 `DOCUMENTS` 字典。

## 部署时要做什么

**代码可以只靠 `git clone` 拿到，PDF 必须单独上传一次。**

```bash
# 从开发机把 PDF 推到服务器（与代码放同一个 static 目录，后端就是从这里提供的）
rsync -av backend/static/docs/ \
      csbb@<服务器>:/srv/cs-blackbook/backend/static/docs/
```

传完后不需要重启后端：`/static` 是静态目录挂载，文件到位即可访问。
可以用下面这条确认：

```bash
curl -sI https://csblackbookhub.com/static/docs/ws-tcp.pdf | head -1   # 期望 200
```

## 如果 PDF 缺失会怎样

`mock_data._document_path()` 会先检查文件在不在磁盘上，不在就返回 `None`
（而不是给前端一个必然 404 的链接）。前端拿到 `null` 就不渲染 PDF 区块 ——
所以漏传 PDF 的后果是“实验页少了文档阅读区”，不会出现加载失败的面板，
其余功能（指南、代码编辑、判题）都不受影响。
