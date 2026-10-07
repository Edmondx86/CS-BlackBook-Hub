# 上线前体检报告 · CS-BlackBook-Hub

> 范围：`backend/`、`frontend/`、根目录部署文件、git 仓库状态
> **状态：3 个阻塞项中的 2 个已修复并验证；A2（提交仓库）需要你确认提交范围；安全加固的「公网暴露」部分需要你拍板。**

## 修复进度总览

| 编号 | 问题 | 状态 |
| --- | --- | --- |
| A1 | 后端镜像漏拷 `judge/`，4 个练习 Docker 下判不了题 | ✅ 已修 |
| A2 | 仓库几乎什么都没提交 | ⏳ 待你确认后提交 |
| A3 | 判题接口任意代码执行（含一条绕开沙箱的 `exec`） | ✅ 已修：代码层加固 + 公网防护（见第七节） |
| B1 | 4 个练习的「参考服务器代码」按钮不出现 | ✅ 已修（现覆盖 5 个 lab） |
| B4 | API 声明 40 个不存在的附件路径 | ✅ 已修（现只返回真实存在的文件） |
| B6 | 两处过期注释误导维护 | ✅ 已修 |
| B5 | 白天模式注释说占位 | ✅ 注释已修；⏳ 视觉仍需肉眼看一遍 |
| B2 | 「友链」是空壳页 | ✅ 已修（页面已删除，链接移入工具页） |
| B3 | 顶栏「开发中」菜单项 | ✅ 已修（可点击 + 占位页） |
| C1 | 依赖不封顶 | ✅ 已修（后端完整锁定 + 前端改用 npm ci） |
| C2 | 前端 2.1 MB 单 chunk | ✅ 已修（首屏 2.3 MB → 123 kB） |
| C3 | 缺 `.env.example` / `.gitattributes` | 🔶 `.gitignore` 已补；其余待定 |
| C4 | compose 缺 healthcheck | ⏳ 待定 |
| C5 | 仓库死重量 | ⏳ 待定 |
| C6 | `sock-icmp` 静态判题 | ⏳ 设计选择，非缺陷 |

---

## 一、🔴 阻塞项

### A1. 后端镜像漏拷 `judge/` ✅ 已修

`backend/Dockerfile` 原来只有 `COPY app ./app` 和 `COPY static ./static`，而 `evaluator.py` 要从
`/app/judge/servers/` 读取判题对端脚本 —— 导致 `sock-websocket`、`sock-web-client`、`sock-smtp`、
`sock-proxy` 四个练习**在 Docker 部署下必然判题失败**，且本地（跑源码目录）测不出来。

**修法**：`backend/Dockerfile` 增加 `COPY judge ./judge`（含注释说明为何不能删）。

### A2. 仓库几乎什么都没提交 ⏳ 待你确认

* 仓库只有 2 个提交；工作区 **72 项变更**（21 改 / 10 删 / 41 未跟踪）
* `frontend/src` 磁盘上 **79 个文件，只有 7 个被跟踪**（缺全部 51 张知识卡片、组件、主题、图片、终端页）
* `backend` 磁盘 52 个源文件，只有 40 个被跟踪（缺 `judge/`、`sandbox.py`、`static/{starter,solutions}/*.py`）
* 10 个已删除但仍被跟踪的旧文件（`static/*/sock-*.py` 重命名残留）

**已做的准备**：`.gitignore` 补上了 `desktop.ini`、`Thumbs.db`、`.claude/`。
**待你决定**：`pic/`（9 MB 原图素材库）是否进仓库；
`terminal-src/`（第三方 Svelte 工程，138.7 MB，其中 node_modules 137 MB）**已确认删除** ——
运行时只需要 `frontend/public/terminal/`（1.7 MB），它才是 About 页的依赖，且**必须提交进仓库**。
确认后执行 `git add -A && git commit`。

### A3. 判题接口任意代码执行 ✅ 代码层面已修

| 子项 | 原状况 | 现状 |
| --- | --- | --- |
| `_verify_checksum` 在后端进程内 `exec` 学生代码 | 无子进程、无超时；`while True: pass` 会阻塞事件循环把服务卡死 | ✅ 改为「AST 只抽 `checksum` 函数 → 写进一次性临时目录 → 交给 `start_sandbox` 执行 → 3 s 硬超时 → 异常/超时都返回失败说明」 |
| 提交体积无上限 | `RunRequest.code` 只校验 `min_length=1` | ✅ 新增 `MAX_SUBMISSION_CHARS = 200_000`，超限由 FastAPI 返回 422 |
| 子进程中文日志乱码 | Windows 下子进程按 GBK 输出，父进程按 UTF-8 解码 → 判题提示全是乱码 | ✅ `sandbox._sanitized_env()` 增加 `PYTHONIOENCODING=utf-8` |
| 无鉴权 / 无限流 | 未改动 | ⏳ **需要你拍板** |

**对抗测试结果**（全部符合预期）：

| 用例 | 结果 | 耗时 |
| --- | --- | --- |
| 正常 `checksum` | ✅ 通过 | 0.14 s |
| `while True: pass` | ✅ 拦截，提示「执行超过 3.0s（疑似死循环）」 | **3.02 s**，且**无子进程泄漏**（跑前/跑后 python 进程数 4 → 4） |
| 返回非整数 | ✅ 提示「checksum 返回值不是整数」 | 0.07 s |
| 函数体内 `os.system(...)` | ✅ 失败（在沙箱内执行，未触及后端进程） | 0.12 s |
| 抛异常 / 未定义名字 | ✅ 提示可读（中文不再乱码） | 0.1 s |
| 语法错误 / 无 `checksum` 函数 | ✅ 提示明确 | < 0.01 s |
| 200 001 字符提交 | ✅ HTTP 422 | — |

**仍需你决定的 A3 剩余部分**：
1. 上线先**只在内网/校园网暴露**，还是要直接公网开放？
2. 若要公网开放：目前 compose 下 `docker_available()` 恒为 `False`（后端容器没有 docker CLI / 没挂 docker.sock），
   所以**学生代码仍跑在后端容器里**（有网络、无 CPU/内存配额）。要真正隔离，需要给后端挂 docker.sock
   并启用 `csbb-judge` 镜像（`backend/judge/Dockerfile` 已写好，但 compose 从不构建它；
   `sandbox.py:19-20` 还要求先手工 `docker network create --internal csbb-judge`）。
3. 是否给 `/run` 加限流（当前无任何频次限制）。

---

## 二、🟡 用户可见的功能缺口

### B1. 4 个练习的「参考服务器代码」不出现 ✅ 已修

原逻辑只从 `static/solutions/<starter名>_server.py` 取，但那 4 个对端脚本都在 `judge/servers/`；
前端 `LabDetailView.vue:529` 是 `v-if="referenceServerCode"`，为空就整块隐藏。

**修法**：`mock_data.py` 新增 `_read_server_code(lab_id, starter_code_path)`，先找 `static/solutions/`，
再回退 `judge/servers/`，并为文件名不符合约定的 `sock-proxy`（`ch2_proxy_origin_server.py`）加了显式映射。

**修复后实测**：

| lab | 参考服务器代码 |
| --- | --- |
| `sock-websocket` | 1184 字节 ✅（新增） |
| `sock-web-client` | 1908 字节 ✅（新增） |
| `sock-smtp` | 2694 字节 ✅（新增） |
| `sock-proxy` | 1316 字节 ✅（新增） |
| `sock-pinger` | 953 字节（原本就有） |
| `sock-web` / `sock-pinger-server` / `sock-icmp` | 0（它们本身就是服务器 / 无对端，符合预期） |

### B4. API 声明 40 个不存在的附件路径 ✅ 已修

`static/pcaps/`（12）、`static/guides/`（20）、`static/tests/`（8）三个目录都不存在，但 `attachments`
照报不误。**前端本来就不渲染 `attachments`，所以没有断链**，属于 API 说谎。

**修法**：`_lab_from_wireshark` / `_lab_from_socket` 改为只收录 `_file_exists()` 为真的附件。
实测：现在共返回 8 个附件，**全部真实存在**（即 8 个 Socket 练习的 starter 代码）；
Wireshark 实验因为既无 pcap 也无 guides 文件，`attachments` 为空数组。

> 若以后补上 `pcap`，附件会自动出现，无需改代码。`ADD_NEW_LAB.md` 已补充这条约定说明。

### B5. 白天模式 🔶 注释已修，视觉待验
`theme.css:8` 原写「白天模式（占位，后续完善）」，实际下面 40 多个 token 全都定义了，顶栏月亮/太阳
按钮也是通的（`App.vue:211-257`）。注释已改为「顶栏月亮/太阳按钮切换，选择持久化在 localStorage」。
**仍需你在浏览器里切一次白天模式，把首页 / 章节页 / Lab 页 / 卡片页各扫一眼** —— 配色脚本验证不了。

### B6. 过期注释 ✅ 已修
* `LabDetailView.vue:10`：「流式返回测试日志（按行 / NDJSON）」→「返回 JSON 判题结果」（实际是 `await res.json()`）
* `HomeView.vue:74, 93`：去掉「图标为占位 SVG，后续替换」（7 个图标其实都是完整 SVG）

### B2. 「友链」空壳页 ⏳ 待定
`views/LinksView.vue` 全文只有一个标题 +「相关资源与链接，内容待完善。」，而顶栏「说明 → 友链」
是指向它的活链接（`App.vue:195-200`）。要么补内容，要么先把它从菜单里摘掉。

### B3. 顶栏「《深入理解计算机系统》(开发中)」 ✅ 已修

原来是个不可点击的 `<div>`，点不动也没反馈。现已改成 `RouterLink` → `/csapp`，
落到新增的占位页 `src/views/ComingSoonView.vue`：一句「还什么都没有哦~」+
说明 + 「先去看看《计算机网络：自顶向下方法》」/「返回首页」两个出口。
书名走路由 `meta.title`，将来再添别的书只要加一条路由。

**顺带新增：章节内的左侧位置导航**（用户要求的另一个功能）

新增 `src/components/ChapterNav.vue`，卡片页与 Lab 页都会在最左侧显示：
章节号 / 书名 → 当前位置（如「知识卡片 3 / 8」）→ 知识卡片目录（当前项高亮）
→ 实验与练习目录（Wireshark / Socket 分组）。带折叠开关，状态存 localStorage。

* 章节概览抽成了 `src/composables/useChapter.js`（进程内缓存同一个 Promise），
  卡片页与导航共用一份数据，不重复请求；失败不缓存，网络恢复后重进即可重试
* Lab 页改造时把 `mainEl`（拖拽分栏的基准）收进了一层新容器，
  **导航放在它外面** —— 否则 `getBoundingClientRect().left` 会左移一个导航宽度，
  拖拽分割条时会跳到光标右侧约 240px
* 窄屏（<md / <lg）自动隐藏导航，改用页内已有的「上一张 / 下一张」
`App.vue:149`，纯文本 `<div>` 不是链接。属于有意的占位预告，但视觉上像一个坏掉的菜单项。

---

## 三、🟠 部署工程质量（均未改动）

| 编号 | 问题 | 影响 | 建议 |
| --- | --- | --- | --- |
| C1 | ~~`requirements.txt` 5 个依赖全用 `>=` 不封顶~~ | ~~构建不可复现~~ | ✅ **已修，见下节** |
| C2 | ~~前端产物 2.1 MB 单 chunk + 1.26 MB pdf worker~~ | ~~首屏偏慢，构建已警告~~ | ✅ **已修，见下节** |
| C3 | 缺 `.env.example` 与 `.gitattributes` | 环境变量无文档；git 反复警告 LF→CRLF | 补两个文件（`.gitignore` 已补） |
| C4 | compose 无 healthcheck，`depends_on` 无 `service_healthy` | 前端可能先于后端就绪 | 给后端加 healthcheck（复用 `GET /`） |
| C5 | 仓库死重量：`pic/` 9 MB、根 `desktop.ini`、根空 `package-lock.json`(88 B)、根 `Favicon.png`、`frontend/dist/` 旧产物 | 仓库臃肿、易误提交 | `terminal-src/` **已删除**（138.7 MB）；其余待定 |
| C6 | `sock-icmp` 是纯静态判题 | 判分严格度低于其他 7 个 lab | 设计选择（raw socket 需 root）；本次已把 `checksum` 那一步改成真执行 |

**C5 提醒**：`frontend/public/terminal/` 是 About 页的运行时依赖（Vite 会原样拷进 `dist/terminal/`），
**必须提交进仓库**。其中 8 个文件 = 上游 m4tt72/terminal 构建产物 5 个 + **手工放的 3 个**
（`config.json` / `banner.txt` / `p.txt`，都是运行时 fetch 的）—— 重建终端后要把这 3 个放回去，
否则终端拿不到配置与横幅。这条已写进 `frontend/src/views/AboutView.vue` 的注释里，
连同重建步骤，免得日后源码不在手边时踩空。

### C1 详情：依赖封顶（已完成）

**后端**

* `backend/requirements.txt` —— 5 个直接依赖全部改为 `==` 精确钉死
  （fastapi 0.141.1 / uvicorn[standard] 0.52.4 / pydantic 2.13.5 / httpx 0.28.1 / websockets 17.1）
* `backend/requirements.lock.txt` —— **新增**，21 个包（含 starlette、anyio、pydantic_core、
  httptools、watchfiles、PyYAML 等全部传递依赖）精确锁定
* `backend/Dockerfile` —— 改为 `pip install -r requirements.lock.txt`

一个必须知道的点：**只钉直接依赖并不能保证可复现**。本机 venv 是 Python 3.14，镜像却是
`python:3.11-slim`，同一份 `requirements.txt` 在两个 Python 上解析出的传递依赖是不同的
（实测 3.11 下是 `starlette 1.7.0` / `watchfiles 1.3.0` / `idna 3.20` / `python-dotenv 1.2.4`，
而本机 3.14 是 `1.6.0` / `1.2.0` / `3.19` / `1.2.3`）。锁文件解决的正是这个问题。

锁文件里的 21 个版本**都已验证在 `cp311 / manylinux2014_x86_64`（即镜像的目标平台）上有预编译
wheel**，用 pip 的跨平台解析确认过，无需真的建 Linux 环境：

```bash
pip install --dry-run --ignore-installed --python-version 3.11 --implementation cp \
    --abi cp311 --platform manylinux2014_x86_64 --only-binary=:all: \
    --report report.json -r backend/requirements.txt
```

**前端**

`frontend/Dockerfile` 原来只 `COPY package.json` 后 `npm install` —— **锁文件 (package-lock.json)
根本没进镜像**，等于每次构建都重新求解版本。已改为：

```dockerfile
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
```

顺带修掉一个会让 `npm ci` 直接报错的旧问题：`package-lock.json` 的根依赖块里**漏记了
`pdfjs-dist`**（包本身在 `node_modules/` 条目里有锁定，但根依赖没写），已用
`npm install --package-lock-only` 补齐（全文件只增加 1 行，其余 0 改动）。

> 注意：**本机跑 `npm ci` 会因为 vite dev server 占用 `node_modules/@rollup/*.node` 而失败**
> （EBUSY），这是 Windows 文件锁、不是锁文件问题 —— 已在隔离目录用真实 `npm ci` 验证通过
> （退出码 0，121 个包装好）。以后要本地跑 `npm ci`，先停掉 `npm run dev`。

### C2 详情：前端 chunk 拆分（已完成）

**改前的浪费非常离谱**：整站只有 1 个 JS chunk，体积 **2.31 MB（gzip 776 kB）** ——
打开首页就必须下载并解析全部代码，包括只有在 Lab 页才用的 1 MB PDF 库、以及
`highlight.js` 的 386 个语言文件（1.58 MB）。

四处改动：

| 改动 | 文件 | 效果 |
| --- | --- | --- |
| **highlight.js 按需注册** | 新增 `src/highlight.js`；`src/markdown.js`、`LabDetailView.vue` 改从这里引入 | 语言文件从 386 个（1.58 MB）降到 6 个：`vendor-highlight` 仅 **35 kB**（**2.2%**） |
| **PDF 预览器改异步组件** | `LabDetailView.vue` 用 `defineAsyncComponent(async () => import(...))` | pdfjs + vue-pdf-embed 独立成 `vendor-pdf`，**只在真正渲染 PDF 时才下载** |
| **路由级分割** | `main.js` 除首页外全部改成 `() => import()` | 每个页面各自成 chunk，首屏只加载首页所需 |
| **卡片/工具 Markdown 按需** | `FlashcardsView.vue`、`ToolView.vue` 去掉 `import.meta.glob` 的 `eager: true` | 51 张卡片正文从「一次性内联 245 kB」变成「每张一个 ~3 kB 小 chunk」 |
| **显式切分第三方库** | `vite.config.js` 增加 `build.rollupOptions.output.manualChunks` | vue / markdown-it / highlight.js / pdf 各自成 chunk，不重复打包 |

**实测对比**

| | 改前 | 改后 |
| --- | --- | --- |
| JS chunk 数 | **1** | **69** |
| 首屏 JS（打开首页） | 2,306 kB / gzip 776 kB | **123 kB / gzip 46.8 kB** |
| 卡片页增量 | （含在首屏里） | 9.9 kB + 一张卡 ~3 kB |
| Lab 页增量 | （含在首屏里） | 14.8 kB（PDF 另算 763 kB，懒加载） |
| 构建警告 | chunk > 500 kB | **无任何警告** |

**验证**（脚本解析 `dist` 的 chunk 引用图）：

* 入口 chunk 含首页文案、**不含**卡片正文 —— 卡片正文确实被拆出去了
* 入口与 `index.html` **都不含** pdfjs / `pdf.worker` —— PDF 确实是懒加载
* `LabDetailView` chunk 里能看到 `import("./vendor-pdf-…")`
* **69 个 chunk 无孤儿**，每一个都被引用
* 无 chunk 超过 800 kB 阈值（最大的 `vendor-pdf` 是懒加载的）

> 小提醒：路由改成懒加载后，弱网下点进新页面会有一瞬间空白（chunk 正在下载）。
> 目前没有加加载态，介意的话可以给 `<router-view>` 包一层过渡。

---

## 四、✅ 修复后的完整回归验证

| 验证项 | 结果 |
| --- | --- |
| **8 个 Socket 练习参考解答端到端判题** | ✅ **8/8 全 PASS**（sock-websocket 522 ms、sock-web 2988 ms、sock-web-client 606 ms、sock-pinger 6681 ms、sock-pinger-server 1028 ms、sock-smtp 611 ms、sock-proxy 1027 ms、sock-icmp 123 ms） |
| 判题日志中文可读性 | ✅ 全部 `readable`，无 U+FFFD 乱码 |
| checksum 沙箱对抗测试 | ✅ 7 个用例全部符合预期，无进程泄漏 |
| 附件只返回真实文件 | ✅ 8/8 存在 |
| 参考服务器代码覆盖 | ✅ 5 个 lab 有值 |
| 后端接口 | ✅ `/`、`/chapters`(8 章)、20 个 Lab 全部 200；未知章节 404 |
| 前端生产构建 | ✅ 383 模块，3.62 s |
| 51 张知识卡片 | ✅ 标题 51/51 一致、渲染零异常、引号规范 |

---

## 五、剩余待办（按建议顺序）

1. **A2**：确认 `pic/`（9 MB 原图库）去留 → `git add -A && git commit`（这是当前最大的风险。
   `frontend/public/terminal/` **一定要提交**，它是 About 页的依赖）
2. **服务器上验证 bwrap 真的生效**（手册 5.1 节）—— 本机 Windows 没有 bwrap，
   我只在特权容器里验证了参数与挂载行为（包括修掉的那个致命顺序 bug），
   真机上的 systemd + PrivateTmp 组合仍需实测一次
3. **A3 剩余**：确定暴露范围；若要公网开放，加限流 + 启用 docker 隔离
4. **C4 / C3 / C1**：healthcheck、`.env.example`、`.gitattributes`（C1 已完成）
5. **B5**：白天模式肉眼验收
6. **C5**：仓库瘦身（`terminal-src` 138.7 MB 已删；剩 `pic/` 9 MB 与几个根目录垃圾文件）
7. **死代码清理**：Docker 判题路径（`backend/judge/Dockerfile` + `sandbox.py` 里的
   `_start_docker` / `_ensure_network` / `_docker_rm`）已确认跑不通且默认不启用，
   留着容易误导后来的人 —— 建议删除或明确标注为「未完成」
8. **文档漂移**：`ADD_NEW_LAB.md` 写的策略名 `UdpPingerStrategy` 与代码里的
   `UdpPingerClientStrategy` 不一致，照着文档加 lab 会踩空
9. 可选：把 `backend/app/mock_data.py` 里 **92 处 `「」`**（渲染在 Lab 指南页上）
   统一成 `“ ”`，与前端保持一致

```bash
# 上线前执行
cd frontend && npm ci && npm run build
docker compose up --build -d
curl -s http://localhost/api/v1/chapters | head -c 120     # 应返回 8 个章节
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/ # 应返回 200
```

---

## 七、公网上线加固（本轮新增）

前提已确认为**公网直接开放**（不是内网/校园网），因此按公网威胁模型补了一层防护。

### 7.1 判题接口防护（代码层，已本地验证）

`/run` 会执行访客提交的代码，是整站唯一的高危面。新增 `backend/app/services/guard.py`：

| 防护 | 参数 | 超限行为 |
| --- | --- | --- |
| 单客户端限流 | 每 `60s` 最多 `12` 次（按 IP） | `429` + `Retry-After: 60` |
| 并发上限 | 同时最多 `4` 个判题 | `429` + `Retry-After: 5` |
| 熔断开关 | `JUDGE_ENABLED=false` | `503`（改环境变量重启即可止血，不用改代码） |

客户端 IP 取 `X-Forwarded-For` 首段 —— **这只有在「后端不对外暴露、仅由 nginx 反代」时才可信**，
所以下面的 7.2 是配套的，不能只做一半。

**实测结果**：

```
第 1~12 次 -> 200 passed=True
第 13 次   -> 429  Retry-After=60   提交过于频繁：每 60 秒最多 12 次
JUDGE_ENABLED=false -> 503 判题功能暂时关闭
同时申请 6 个名额 -> 4 个成功、2 个被拒；归还后 running 回到 0（无名额泄漏）
```

### 7.2 后端不再对外暴露（docker-compose）

改前 `ports: - "8000:8000"` —— 后端 API 和 `/docs` **直接暴露在公网**，绕过 nginx，
也会让 7.1 的限流可以被伪造 `X-Forwarded-For` 绕过。

```yaml
backend:
  expose: ["8000"]          # 只对同网络可见，不再发布到宿主机
  networks: [judge-net]
frontend:
  ports: ["80:80"]
  networks: [default, judge-net]   # 双网络：default 保证 80 对外可达
networks:
  judge-net:
    driver: bridge
    internal: true          # 无对外路由
```

**关键点**：后端只挂 `judge-net`（`internal: true`）→ **学生代码即使在后端容器里被执行，
也无法访问外网**，不会被当作跳板去压测/攻击第三方，或把服务器 IP 刷进黑名单。
前端同时挂 `default`，避免 `internal` 影响 80 端口的对外可达性。

### 7.3 nginx 加固（frontend/nginx.conf）

* `client_max_body_size 1m` —— 挡住超大请求体
* 安全响应头：`X-Content-Type-Options: nosniff`、`X-Frame-Options: SAMEORIGIN`、`Referrer-Policy`
  （注意**不能用 `DENY`**：`/about` 页用同源 iframe 内嵌了终端页）
* API 代理补 `X-Forwarded-Proto`，超时显式设为 `connect 5s / read 60s`（判题实测最慢约 7s）

### 7.4 文档与 schema 开关

`ENABLE_DOCS=false` 时 `/docs`、`/openapi.json`、`/redoc` 全部 404（默认开启，本地开发不受影响）。
compose 里已设为 `false`。

```
默认（本地）        : /docs 200、/openapi.json 200、/redoc 404
ENABLE_DOCS=false  : 三者全部 404
```

### 7.5 部署形态已确定：宿主机 nginx + systemd（不用 Docker）

服务器实况：**阿里云轻量服务器、已配好 nginx（专供本项目）、未装 Docker**；
域名 **`csblackbookhub.com`**（含 `www`）。因此本节的 Docker 方案（7.2 的 compose 改动）
作为**备选**保留，实际走宿主机部署，配置见 **`deploy/`**：

| 文件 | 作用 |
| --- | --- |
| [`deploy/DEPLOY.md`](deploy/DEPLOY.md) | 完整部署手册（含上线自检清单） |
| [`deploy/nginx-cs-blackbook.conf`](deploy/nginx-cs-blackbook.conf) | 宿主机 nginx 站点配置（`server_name` 已填域名） |
| [`deploy/csbb-backend.service`](deploy/csbb-backend.service) | systemd unit（含沙箱化与资源上限） |

**⚠️ 中国大陆节点的硬性前置条件：ICP 备案。**
阿里云大陆地域的服务器，域名解析过去后必须完成备案，否则运营商侧拦截 80/443 ——
表现是「DNS 能解析但打不开、curl 超时」，极易误判成 nginx 配错。若机器在境外地域则不需要。
手册第 0 节把备案、DNS 解析、安全组放行列为部署前三项检查。

**这个选择带来的最大变化，也是必须正视的一点**：没有 Docker，判题就**没有容器边界**。
为此做了两层补偿，手册里这三件事**不是可选优化，而是必做**：

1. **专用低权限用户** `csbb`（绝不能让判题以 root 跑）
2. **systemd 沙箱化**：`NoNewPrivileges` / `PrivateTmp` / `ProtectSystem=strict` / `ProtectHome` /
   `RestrictAddressFamilies` + `MemoryMax=1G` / `TasksMax=256` / `CPUQuota=150%`
3. **按 uid 封锁出站网络**（iptables `-m owner --uid-owner csbb -j REJECT`）：
   否则学生代码能以你的服务器 IP 去访问外网，有被当作跳板或刷进黑名单的风险

另外用户确认「可以装 Docker」，于是我把 Docker 判题路径**实测**了一遍，结论是**不要用**，
并顺手挖出了两个更严重的既有问题：

### 7.5.1 bubblewrap 隔离（已实现，并修掉一个致命顺序 bug）

`sandbox.py` 新增 bwrap 封装层：`--unshare-user/pid/ipc/uts/cgroup` + `--ro-bind / /`（只读根）
+ `--tmpfs /tmp` + `--die-with-parent`，通过 `JUDGE_SANDBOX=auto|bwrap|none` 控制。

**⚠️ 修掉了一个会让每个判题都失败的顺序 bug**（在特权容器里装了 bwrap 实测出来的）：

`--tmpfs /tmp` 会把 `/tmp` 换成空 tmpfs，而判题的工作目录是 `tempfile.mkdtemp()` 建在
`/tmp` 下的 —— 于是沙箱里根本没有学生脚本：

```
A. 原写法：bwrap: Can't chdir to /tmp/judge-x: No such file or directory   ← 每个判题都会挂
B. 修法  ：在 --tmpfs /tmp 之后追加 --ro-bind <cwd> <cwd>  → 正常执行
C. 附带确认：修复后 /tmp 仍是私有可写（ls /tmp 看不到宿主内容）
D. 附带确认：根文件系统只读
```

这个 bug 在本机（Windows 无 bwrap）永远测不出来，所以额外加了
`backend/tests/test_judge_sandbox.py`（标准库 unittest，9 个用例）把这几条不变量锁住：
不能出现 `--unshare-net`、工作目录重挂必须在 `--tmpfs /tmp` 之后、`--chdir` 必须在重挂之后、
根只读、隔离标志齐全、原命令完整保留、学生代码必须经 `start_sandbox`。

```bash
cd backend && python -m unittest discover -s tests
```

**刻意不加 `--unshare-net`**：这些 Lab 的裁判要经 localhost 与学生的进程对话，
切断网络命名空间会让裁判连不上学生 —— 出站改由 iptables 按 uid 封锁（第 7 节）。

### 7.5.2 ⚠️ 更严重：6 个 Lab 的学生代码此前**根本没进沙箱**

排查发现整个判题里只有 **2 处**调用 `start_sandbox`（基类 `judge` 与 ICMP 的 checksum 驱动），
`UdpPingerClient` / `WebClient` / `Smtp` 三个策略的学生客户端是**裸的 `create_subprocess_exec`**：
没有命名空间隔离、没有 rlimit、**连 `env=` 都没传**（把后端进程的全部环境变量透传给了不可信代码）。

已全部改为走 `_spawn_untrusted()` → `start_sandbox`。**沙箱覆盖从 4 个 Lab 提升到 7 个**
（`sock-websocket` 为 0 是正确的：`PingCommandStrategy` 根本不执行学生代码，裁判自己发 ping）。

用户可见影响为零，8 个 Lab 参考解答判题 **8/8 全通过**。

### 7.5.3 ⚠️ Docker 判题路径：实测跑不通，已改为显式 opt-in

本机起了 Docker Desktop 实测，三个结论：

| 实验 | 结果 |
| --- | --- |
| `docker run --network <internal> -p 127.0.0.1:18080:80` | **`docker ps` 只显示 `80/tcp`，宿主机连不上** —— 端口发布被静默忽略（[moby/moby #53256](https://github.com/moby/moby/discussions/53256)） |
| 从与 daemon 同 netns 的容器访问 bridge IP | **connect_ex = 0** —— 改直连容器 IP 可行 |
| internal 网络里的容器访问外网 | **connect_ex = 101** —— `internal` 确实封死出站 |

也就是说现有 Docker 路径下**裁判永远连不上学生容器**。而且即使修好这一点，
**6 个 Lab 的学生代码硬编码连 `127.0.0.1`**，容器里够不到宿主机的参考服务器，
要支持它们必须让参考服务器与容器共享网络命名空间 —— 另一套改造。

已把引擎改为 `JUDGE_ENGINE=subprocess`（默认，即 bwrap），Docker 降级为显式 opt-in，
并加了「镜像不存在就快速失败并回退」的检查 —— 因为实测发现**Docker 可用但镜像缺失时，
判题不是回退而是 5 个 Lab 全线失败**，且原因埋在日志里（`Unable to find image`）。

顺带记录：**国内直连 Docker Hub 拉不到镜像**（`auth.docker.io` 超时），实测 `docker.m.daocloud.io` 可用。

另外确认了两个会直接卡住安装的前置条件：

* **`websockets==17.1` 要求 Python >= 3.11** —— 而 **Ubuntu 22.04 默认是 3.10**，
  必须先装 3.11+（手册第 0 节给了命令）；Ubuntu 24.04 / Debian 12 可直接用
* 前端**不需要**在服务器上装 Node：本地 `npm run build`，把 `dist/` 上传即可

### 7.6 若将来想回到 Docker

`docker-compose.yml`（7.2 已按公网加固）与 `backend/Dockerfile`（含 `COPY judge`、
`requirements.lock.txt`）都保留着，装好 Docker 后可直接用，并且天然获得判题的容器边界。
唯一要注意：国内拉 `python:3.11-slim` / `node:20-alpine` / `nginx:1.25-alpine` 可能需要配镜像加速。
