# 新增 Lab 结构化样板（Wireshark / Socket）

> 核心约定：**一个 `id` 贯穿全系统**（GUIDES 的 key、DOCUMENTS 的 key、CHAPTERS 里注册的 id、
> 判题 STRATEGIES 的 key、路由 `/labs/{id}`），必须全局唯一。
>
> 前端是数据驱动的：只要后端数据正确，章节目录 / 章节页 / Lab 详情会自动出现，**前端零改动**。
> 改完 `mock_data.py` / `evaluator.py` 后要**重启后端**（`uvicorn --reload` 会自动重载）。

## 文件地图（一个 lab 涉及的所有位置）

| 位置 | 作用 |
| --- | --- |
| `backend/static/starter/<id>.py` | Socket 初始代码模板（含 TODO 提示） |
| `backend/static/solutions/<id>.py` | Socket 参考答案 |
| `backend/static/docs/<id>.pdf` | 作业要求文档（可选，Wireshark/Socket 都可用） |
| `backend/static/pcaps/<id>.pcap` | Wireshark 抓包文件（可选） |
| `backend/app/mock_data.py` → `GUIDES` | Markdown 指南内容（内联字符串） |
| `backend/app/mock_data.py` → `DOCUMENTS` | lab_id → PDF 路径映射 |
| `backend/app/mock_data.py` → `CHAPTERS` | 注册 `WiresharkLab` / `SocketExercise` |
| `backend/app/services/evaluator.py` → `STRATEGIES` | Socket 判题策略登记（仅 Socket） |

---

## 一、Wireshark 实验样板

以新增 `ws-dns`（DNS 协议实验）为例。

### 1. 放静态文件（可选）

```
backend/static/pcaps/dns.pcap        # 抓包文件
backend/static/docs/dns.pdf          # 作业要求文档（可选）
```

### 2. `backend/app/mock_data.py`

**① GUIDES 里加指南**（内联 Markdown）：

```python
"ws-dns": """# DNS 协议实验

> 对应教材 **Chapter 2**「Application Layer」。

## 实验目标
1. 观察 DNS 查询/响应的报文结构。
2. 理解递归查询与迭代查询。

## 实验材料
- 抓包文件：`dns.pcap`（见附件）

## 实验步骤
1. 打开 `dns.pcap`，过滤 `dns`。
2. 分析查询报文中的 Question 与响应报文中的 Answer 字段。

## 思考题
1. DNS 查询走 UDP 还是 TCP？为什么？
""",
```

**② DOCUMENTS 里加 PDF 映射**（有 PDF 才加）：

```python
"ws-dns": "/static/docs/dns.pdf",
```

**③ CHAPTERS 里注册**（找到所属章节的 `wireshark_labs` 列表）：

```python
wireshark_labs=[
    # ...已有实验...
    WiresharkLab(
        id="ws-dns",
        title="DNS 协议实验",
        pcap_path="static/pcaps/dns.pcap",
        guide_path="static/guides/ws-dns.md",   # 元数据，内容走 GUIDES
    ),
],
```

### 3. 检查清单

- [ ] `id` 全局唯一
- [ ] `GUIDES["ws-dns"]` 已加
- [ ] `CHAPTERS` 里已注册 `WiresharkLab`
- [ ] `pcap_path` / `guide_path` 以 `.pcap` / `.md` 结尾（schema 校验强制）
- [ ] （可选）PDF 已加 `DOCUMENTS`
- [ ] 重启后端

---

## 二、Socket 练习样板

以新增 `sock-tcp`（TCP 回显）为例。

### 1. 放静态文件

```
backend/static/starter/sock-tcp.py     # 初始模板（TODO 提示）
backend/static/solutions/sock-tcp.py   # 参考答案
backend/static/docs/sock-tcp.pdf       # 作业要求文档（可选）
```

`starter/sock-tcp.py`（模板，只给提示不给答案）：

```python
"""TCP 回显 —— 初始代码模板。

判题约定：通过 --port 或 PORT 读取端口。
"""

import argparse
import os
import socket

HOST = "127.0.0.1"


def handle_client(conn: socket.socket) -> None:
    # TODO: 读取一行数据，原样回显
    pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    port = args.port or int(os.environ.get("PORT", "6789"))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, port))
        server.listen(5)
        print(f"Listening on {HOST}:{port}", flush=True)
        while True:
            conn, _ = server.accept()
            with conn:
                handle_client(conn)


if __name__ == "__main__":
    main()
```

### 2. `backend/app/mock_data.py`

**① GUIDES**（同上，加 `"sock-tcp": """..."""`）

**② DOCUMENTS**（可选）：

```python
"sock-tcp": "/static/docs/sock-tcp.pdf",
```

**③ CHAPTERS 里注册**（所属章节的 `socket_exercises` 列表）：

```python
SocketExercise(
    id="sock-tcp",
    title="TCP 回显",
    language="python",
    starter_code_path="static/starter/sock-tcp.py",
    guide_path="static/guides/sock-tcp.md",   # 元数据
    test_cases=[
        TestCase(name="回显 hello", input="hello", expected="hello"),
        TestCase(name="回显 bye", input="bye", expected="bye"),
    ],
),
```

> `starter_code` / `reference_code` 无需手填，`_lab_from_socket` 会自动从
> `static/starter/` 和 `static/solutions/` 按文件名读入。

### 3. `backend/app/services/evaluator.py` 登记策略

```python
STRATEGIES: dict[str, JudgeStrategy] = {
    "sock-web": WebServerStrategy(),
    "sock-pinger": UdpPingerStrategy(),
    "sock-tcp": TcpEchoStrategy(),   # ← 新增（见下方自定义策略样板）
}
```

### 4. 检查清单

- [ ] `starter/<id>.py` 存在（否则编辑器显示占位符）
- [ ] `solutions/<id>.py` 存在（否则「参考答案」显示「暂无」）
- [ ] `GUIDES` + `DOCUMENTS`(可选) + `CHAPTERS` 已加
- [ ] `STRATEGIES` 已登记（否则 `/run` 返回「暂无判题策略」）
- [ ] 重启后端

---

## 三、test_cases 语义（按内置策略）

| 策略 | `input` 含义 | `expected` 含义 | 判定 |
| --- | --- | --- | --- |
| `WebServerStrategy` | 请求行，如 `GET /index.html HTTP/1.1` | 期望状态行，如 `HTTP/1.1 200 OK` | 实际状态码 == 期望状态码 |
| `UdpPingerStrategy` | 发送的 UDP 报文，如 `ping 1` | 期望回显，如 `ping 1` | 回显 == expected |

自定义策略可自行定义 `input`/`expected` 的语义。

---

## 四、自定义判题策略样板

在 `evaluator.py` 里新增（可参考 `WebServerStrategy`）：

```python
class TcpEchoStrategy(JudgeStrategy):
    """TCP 回显：逐条 test_case 建立连接、发送并比对回显。"""

    name = "tcp_echo"
    script_filename = "sock-tcp.py"

    def build_command(self, script, port):
        # 按需定制启动命令（默认是 python <script> --port <port>）
        return [sys.executable, str(script), "--port", str(port)]

    async def verify(self, proc, host, port, test_cases, request_timeout):
        checks: list[EvaluationCheck] = []
        all_passed = True
        for tc in test_cases:
            # 在这里实现交互逻辑（TCP 连接 / UDP 收发 / 发 HTTP 等）
            reply = await _tcp_echo_once(host, port, tc.input, request_timeout)
            ok = reply is not None and reply == tc.expected
            checks.append(EvaluationCheck(
                name=tc.name, passed=ok,
                detail=f"发送 {tc.input!r}，期望 {tc.expected!r}，实际 {reply!r}",
            ))
            all_passed = all_passed and ok
        return _VerifyOutcome(
            status="passed" if (all_passed and checks) else "failed",
            checks=checks,
        )
```

要点：
- `verify()` 返回 `_VerifyOutcome(status, checks, status_code, headers, body_preview)`。
- 启动 / 采日志 / 强杀进程 / 汇总 `EvaluationResult` 都由基类 `JudgeStrategy.judge()` 统一处理，子类只写「怎么校验」。
- 需要的 `import`：`EvaluationCheck`、`_VerifyOutcome`、`JudgeStrategy`（同文件内已可用）。

---

## 五、新增整章（可选）

若 lab 属于全新章节，在 `CHAPTERS` 里追加一个 `Chapter`：

```python
Chapter(
    id="ch3",
    number="Chapter 3",
    title="Transport Layer",
    summary="传输层：UDP/TCP 与可靠传输。",
    knowledge_points=[
        KnowledgePoint(id="kp-3-1", title="Multiplexing", summary="多路复用与分用"),
    ],
    wireshark_labs=[],
    socket_exercises=[],   # 把上面注册的 SocketExercise 放这里
),
```

新章节会自动出现在 `/chapters` 和 `/chapters/ch3`，无需前端改动。
