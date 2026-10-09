# 部署手册（阿里云轻量服务器 · 宿主机 nginx · 不用 Docker）

> 适用形态：服务器已装 nginx、**未装 Docker**、**nginx 专供本项目**。
> 域名：**`csblackbookhub.com`**（含 `www`）
> 目录约定：`/srv/cs-blackbook`（后端源码 + venv）、`/var/www/cs-blackbook`（前端构建产物）。
> 配套文件：[nginx-cs-blackbook.conf](nginx-cs-blackbook.conf)、[csbb-backend.service](csbb-backend.service)

---

## 0. 前置检查

### 0.1 域名备案 ✅ 已完成（两个号都齐了）

| 类型 | 备案号 | 公示位置 / 链接 |
| --- | --- | --- |
| ICP 备案 | **辽ICP备2026021355号** | 首页页脚 → <https://beian.miit.gov.cn/> |
| 公安联网备案 | **辽公网安备21011202001420号** | 首页页脚 → <https://beian.mps.gov.cn/> |

两者是**两套系统、两个号**：ICP 备案在工信部（阿里云代提交），
公安联网备案在公安部全国互联网安全管理服务平台（依据《计算机信息网络国际联网安全保护管理办法》，
需在网站开通之日起 30 日内申请）。换域名或换主体时本节才需要重做。

阿里云**中国大陆地域**的服务器，域名解析过去后必须完成 ICP 备案，否则运营商侧会拦截
80/443 的 Web 访问 —— 表现是“DNS 能解析、但浏览器打不开、curl 超时”，
很容易误判成 nginx 配错了。服务器在**香港/新加坡等境外地域**则不需要备案。

```bash
# 部署时确认解析是否已生效
ping csblackbookhub.com        # 或 nslookup csblackbookhub.com
```

### 0.2 DNS 解析 ✅ 已完成

两个域名都已解析到同一台服务器（实测确认）：

| 记录类型 | 主机记录 | 记录值 |
| --- | --- | --- |
| A | `@` | `47.103.218.113` |
| A | `www` | `47.103.218.113` |

```bash
nslookup csblackbookhub.com        # 应返回 47.103.218.113
nslookup www.csblackbookhub.com    # 同上
```

> `nslookup` 显示“非权威应答”是正常的 —— 那只是递归解析器的缓存答案。

### 0.3 安全组放行 ✅ 已完成

实测从公网探测：**22 / 80 / 443 均可达**，**8000 不可达**（正确 —— uvicorn 只监听回环，
公网绝不该通）。无需再改安全组。

```bash
# 想复核的话，在本地机器执行
for p in 22 80 443; do
  timeout 5 bash -c "cat < /dev/null > /dev/tcp/csblackbookhub.com/$p" && echo "$p 通" || echo "$p 不通"
done
```

### 0.4 Python 版本必须是 3.11+

`requirements.lock.txt` 里的 `websockets==17.1` 要求 **Python >= 3.11**。先查一下：

```bash
python3 --version
```

| 系统 | 默认 Python | 能否直接用 |
| --- | --- | --- |
| Ubuntu 24.04 | 3.12 | ✅ |
| Debian 12 | 3.11 | ✅ |
| **Ubuntu 22.04** | **3.10** | ❌ 需要先装 3.11+ |
| CentOS 7 / 8 | 3.6 / 3.9 | ❌ 需要先装 3.11+ |

如果是 3.10 及以下，装一个新版本（Ubuntu 系）：

```bash
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.11 python3.11-venv
```

之后把本文所有 `python3 -m venv` 换成 `python3.11 -m venv` 即可。

### 0.5 安装 bubblewrap（判题隔离，强烈建议）

判题会执行访客提交的代码。没有容器时，**bubblewrap（bwrap）**是这里最合适的隔离手段：
用 Linux 命名空间 + 只读根文件系统把学生代码关起来，没有守护进程、几乎零开销。

```bash
apt install -y bubblewrap

# 确认它真的能用（部分发行版默认禁止非特权用户建 user namespace）
bwrap --unshare-user --ro-bind / / --dev /dev true && echo "bwrap 可用"
```

如果上面报错，基本可以断定是 Ubuntu 23.10+ 的
`kernel.apparmor_restrict_unprivileged_userns=1` 挡掉了非特权 user namespace。

**✅ 已在真实服务器上验证通过的解法**（Ubuntu 24.04 + bubblewrap 0.9.0，
`apparmor_restrict_userns=1`）：给 bwrap **单独**放行，而不是全局关掉这个内核限制 ——
其他程序仍然受保护，只有 bwrap 能建 userns：

```bash
# 1) 确认确实被限制
sysctl kernel.apparmor_restrict_unprivileged_userns     # 输出 1 就是它

# 2) 只给 bwrap 加放行策略
tee /etc/apparmor.d/bwrap >/dev/null <<'EOF'
abi <abi/4.0>,
include <tunables/global>
profile bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,
  include if exists <local/bwrap>
}
EOF

systemctl reload apparmor

# 3) 用判题真正会用的那个低权限用户复验（关键：不能用 root 验，root 不受此限制）
sudo -u csbb bwrap --unshare-user --ro-bind / / --dev /dev true \
  && echo "✅ csbb 下 bwrap 可用"
```

> ⚠️ **一定要用 `csbb` 这个用户去验**。以 root 执行永远会成功，root 不受该限制 ——
> 用 root 验会得到“明明能用但判题全挂”的假结论。

如果连上面的策略也不生效（极少数发行版/内核组合），再退化为
`sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`（全局放开，影响面大），
或接受退化为“systemd 沙箱 + iptables 出站封锁”这一层 —— 判题仍能工作，
但会失去命名空间隔离（后端日志里会有明确的 warning）。

### 0.6 系统依赖清单（一次装齐）

Ubuntu 24.04 的**最小化镜像默认不装 `python3-venv`** —— 缺了它 `python3 -m venv` 会报
`ensurepip is not available`。别一个个撞上去，一开始就装齐：

```bash
apt update
apt install -y python3-venv bubblewrap iptables
```

| 包 | 用途 | 缺了会怎样 |
| --- | --- | --- |
| `python3-venv` | 建虚拟环境（提供 ensurepip） | `python3 -m venv` 报 `ensurepip is not available` |
| `bubblewrap` | 判题命名空间隔离 | 判题退化为无隔离（见 0.5） |
| `iptables` | 按 uid 封锁判题出站（第 7 节） | 第 7 节无法执行 |

> 撞上 `ensurepip is not available` 时，装完包**必须删掉残缺的 venv 重建** ——
> 报错信息里的 “recreate your virtual environment” 就是这个意思，
> 半成品目录里连 `pip` 都没有：
> `rm -rf venv && python3 -m venv venv`。
>
> 不需要 `build-essential` / Rust：`requirements.lock.txt` 里所有包在
> cp312 / manylinux x86_64 上都有预编译 wheel（可用
> `pip install --dry-run --python-version 3.12 --abi cp312 --platform manylinux2014_x86_64 --only-binary=:all: -r requirements.lock.txt` 预先核对）。

---

## 1. 部署形态与取舍（先看这段）

| | 宿主机部署（本文） | Docker（`docker-compose.yml`） |
| --- | --- | --- |
| 前置条件 | 已有 nginx，装 Python + bubblewrap 即可 | 需装 Docker + 拉镜像（国内经常很慢） |
| 前端 | 本地 `npm run build`，上传 `dist/` | 容器内构建 |
| 后端 | systemd + venv | 容器 |
| **判题隔离** | **bwrap 命名空间隔离** + systemd 沙箱 + 限流 + 出站封锁 | 理论上更强（cgroup 限额），但**现有 Docker 路径跑不通**，见下 |
| 资源占用 | 低 | 多一层 |

**结论**：走本文这条路。

> **为什么不用 Docker 跑判题**（我实测过，不是想当然）：
> 1. `sandbox.py` 的 Docker 路径用 `--network <internal>` + `-p` 发布端口，而 Docker 在 internal
>    网络上**会静默忽略端口发布** —— 实测 `docker ps` 只显示 `80/tcp`、宿主机连不上，
>    裁判因此永远连不上学生容器（`[moby/moby #53256](https://github.com/moby/moby/discussions/53256)`）；
> 2. 即便改直连容器 IP，8 个 Lab 里有 6 个的学生代码按教材写法**硬编码连 `127.0.0.1`**
>    （`ch2_smtp.py` / `ch2_web_client.py` / `ch2_udp_pinger.py`），而容器里的 `127.0.0.1`
>    不是宿主机 —— 要支持它们必须让参考服务器与容器共享网络命名空间，是另一套改造。
>
> bwrap 保留网络命名空间，所以 8 个 Lab 都能原样工作；出站则由第 7 节的 iptables 按 uid 封锁。
> 这也是本文第 5、7 两节**不是可选优化**的原因。
>
> 顺带记录：**国内直连 Docker Hub 拉不到镜像**（`auth.docker.io` 超时），实测
> `docker.m.daocloud.io` 可用。若将来要试 Docker 方案，先配好镜像加速。

---

## 2. 本地构建前端产物

前端**不需要**在服务器上构建（服务器不用装 Node）：

```bash
cd frontend
npm ci
npm run build          # 产物在 frontend/dist/
```

> 之前踩过的坑：本机若正在跑 `npm run dev`，`npm ci` 会因为 vite 占用
> `node_modules/@rollup/*.node` 而报 EBUSY。先停掉 dev server。

上传到服务器：

```bash
# 在本地执行（把 <你的服务器IP> 换掉）
ssh root@<你的服务器IP> "mkdir -p /var/www/cs-blackbook"
scp -r frontend/dist/* root@<你的服务器IP>:/var/www/cs-blackbook/
```

## 3. 上传后端源码

只需要 `backend/`（**不要**带 `venv/`、`__pycache__/`）：

```bash
# 在本地执行
scp -r backend root@<你的服务器IP>:/srv/cs-blackbook/
```

服务器上：

```bash
ssh root@<你的服务器IP>

# 建专用低权限用户（判题代码会以它执行，绝不能用 root）
useradd --system --create-home --shell /usr/sbin/nologin csbb

# 装 Python 与 venv（Ubuntu/Debian；CentOS 用 yum install python3 python3-pip）
apt update && apt install -y python3 python3-venv python3-pip

# 建虚拟环境并装依赖（装的是完整锁定文件）
cd /srv/cs-blackbook/backend
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.lock.txt

chown -R csbb:csbb /srv/cs-blackbook
```

> `requirements.lock.txt` 里的版本已确认在 cp311/manylinux 上有 wheel。
> 如果你的服务器是 **Python 3.10 或更低**，`websockets==17.1` 会装不上
> （它要求 >=3.11）—— 先确认 `python3 --version`。

### 3.1 单独上传作业 PDF（不在仓库里）

`backend/static/docs/` 下的 16 个作业要求 PDF 合计约 24 MB，**不随仓库分发**
（原因与清单见该目录里的 `README.md`）。代码传完之后，PDF 要再单独传一次：

```bash
# 在本地执行；服务器上目录已存在，直接同步进去即可
rsync -av backend/static/docs/ \
      root@<你的服务器IP>:/srv/cs-blackbook/backend/static/docs/
```

**不用重启后端** —— `/static` 是静态目录挂载，文件到位就能访问：

```bash
curl -sI http://127.0.0.1:8000/static/docs/ws-tcp.pdf | head -1     # 期望 HTTP 200
```

漏传了也不要紧，但要知道症状：后端在文件不存在时返回 `document_path: null`
（`mock_data._document_path()` 会先查磁盘），前端拿到 `null` 就不渲染 PDF 区块 ——
所以后果是“实验页少了文档阅读区”，**不会**出现加载失败的面板，
指南、代码编辑、判题都不受影响。

如果以后想把 PDF 放到对象存储，改 `backend/app/mock_data.py` 里的 `DOCUMENTS`
字典即可（它存的本来就是 URL 路径），届时 `_document_path()` 的存在性检查要一并去掉。

## 4. 配置后端服务

```bash
cp /srv/cs-blackbook/deploy/csbb-backend.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now csbb-backend

systemctl status csbb-backend --no-pager
journalctl -u csbb-backend -n 30 --no-pager

# 冒烟：应返回 8 个章节
curl -s http://127.0.0.1:8000/api/v1/chapters | head -c 120
```

## 5. 确认 systemd 沙箱生效

```bash
systemd-analyze security csbb-backend
```

关注两点：整体暴露分应明显低于默认值；并且**确认判题可用**（沙箱限制过严会误伤）：

```bash
# 用参考答案打一次判题（应输出 True）
curl -s http://127.0.0.1:8000/api/v1/chapters/ch5/labs/sock-icmp \
  | python3 -c "import sys,json;open('/tmp/ref.py','w').write(json.load(sys.stdin)['reference_code'])"

python3 - <<'PY'
import json, urllib.request
code = open('/tmp/ref.py').read()
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/chapters/ch5/labs/sock-icmp/run',
    data=json.dumps({'code': code}).encode(),
    headers={'Content-Type': 'application/json'},
)
print('passed =', json.load(urllib.request.urlopen(req))['passed'])
PY
```

若这一步失败，多半是 `ProtectSystem=strict` 挡住了临时目录写入 ——
检查 `PrivateTmp=yes` 是否生效，必要时在 unit 里加 `ReadWritePaths=/srv/cs-blackbook/backend`。

### 5.1 确认判题真的进了 bubblewrap 沙箱

默认配置是 `JUDGE_SANDBOX=auto`：能用 bwrap 就用，用不了就退回普通子进程并在日志里打 warning。
“静默退化”不算好，所以**部署时按下面这一步做一次确定性验证**：

```bash
# 临时改成严格模式：bwrap 用不了就拒绝判题（宁可失败，也不要无隔离地跑）
sed -i 's/^Environment=JUDGE_ENABLED=true/Environment=JUDGE_ENABLED=true\nEnvironment=JUDGE_SANDBOX=bwrap/' \
    /etc/systemd/system/csbb-backend.service
systemctl daemon-reload && systemctl restart csbb-backend

# 重跑上面那段“用参考答案打一次判题”——能 passed 就说明 bwrap 真的生效了
```

验证通过后，把 `Environment=JUDGE_SANDBOX=bwrap` 删掉恢复 `auto` 即可（避免内核/发行版日后
调整 userns 策略时把判题整个拖挂）。想随时知道隔离状态，看日志里的 warning：

```bash
journalctl -u csbb-backend | grep -i bwrap
```

> 判题隔离一共三层，缺一层就少一道防线：
> **bwrap**（命名空间 + 只读根 + 私有 /tmp）→ **systemd**（`ProtectSystem` / `NoNewPrivileges` /
> 内存与 CPU 上限）→ **iptables 按 uid 封锁出站**（第 7 节）。

## 6. 配置 nginx

> **⚠️ 这台服务器的 nginx 与证书都已经就绪了**，不要按“先装配置、再 certbot 签发”的老流程走 ——
> 那会丢掉已有的 HTTPS 配置。实测现状：
>
> | 项 | 现状 |
> | --- | --- |
> | nginx | `nginx/1.24.0 (Ubuntu)` 已在跑 |
> | HTTP → HTTPS | 已配 301 跳转 |
> | 证书 | Let's Encrypt，`CN=csblackbookhub.com`，**SAN 含 `www`** |
> | 首页 | 一个占位页“黑皮书技术笔记” |
> | `/api/` | 404（还没有反代配置，后端也没部署） |
>
> 仓库里的 [nginx-cs-blackbook.conf](nginx-cs-blackbook.conf) **已自带 443 段**
> （证书路径按 certbot 默认布局写好），所以可以整体替换现有站点配置。

### 6.1 先看清现状，再替换

```bash
# 找出当前承载这个域名的配置文件（可能在 conf.d/ 或 sites-enabled/）
nginx -T 2>/dev/null | grep -n 'server_name csblackbookhub'
ls -l /etc/nginx/conf.d/ /etc/nginx/sites-enabled/

# 确认证书目录名（若不是 csblackbookhub.com，要改新配置里的 ssl_certificate 两行）
ls -l /etc/letsencrypt/live/

# 备份现有配置
cp -a /etc/nginx/conf.d/cs-blackbook.conf /root/cs-blackbook.conf.bak 2>/dev/null || \
  cp -a /etc/nginx/sites-enabled/default /root/nginx-default.bak 2>/dev/null || true
```

### 6.2 装新配置并替换掉旧站点

```bash
# 装仓库里的配置（已含 443 段与证书路径）
cp /srv/cs-blackbook/deploy/nginx-cs-blackbook.conf /etc/nginx/conf.d/cs-blackbook.conf

# ⚠️ 必须移除旧的站点配置，否则 server_name 重复，nginx 只会用先加载的那个
rm -f /etc/nginx/sites-enabled/default
# 如果 `ls /etc/nginx/conf.d/` 里还有别的承载本域名的 .conf，也一并移走

nginx -t && systemctl reload nginx
```

> `nginx -t` **失败也不会导致线上中断** —— reload 之前 nginx 仍在用内存里的旧配置，
> 所以放心改、改到 `nginx -t` 通过再 reload。失败最常见的原因是证书路径写错，按 6.1 核对。

### 6.3 确认 HTTPS 与续期

```bash
curl -s -o /dev/null -w 'http  %{http_code} -> %{redirect_url}\n' http://csblackbookhub.com/
curl -s -o /dev/null -w 'https %{http_code}\n' https://csblackbookhub.com/
curl -s -o /dev/null -w 'www   %{http_code}\n' https://www.csblackbookhub.com/
curl -s -o /dev/null -w 'api   %{http_code}\n' https://csblackbookhub.com/api/v1/chapters

systemctl status certbot.timer        # 自动续期是否启用
certbot renew --dry-run               # 试跑一次续期，确认换个 nginx 配置后仍然能续
```

证书是 2026-12-20 到期，续期若失效会在到期日当天整站打不开 —— 所以 `--dry-run` 这一步别省。

### 6.4 HSTS（确认 HTTPS 正常后再加）

HSTS 会让浏览器**强制**只用 HTTPS，一旦开启且证书出问题，用户短时间内无法回退。
新配置里已经预留了注释掉的那一行，确认无误后取消注释再 reload：

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

建议先用小 `max-age`（如 `300`）观察几天，没问题再调成 `31536000`。

## 7. 封锁判题代码的出站网络（重要）

没有容器边界时，学生提交的代码可以以 `csbb` 用户身份访问外网 —— 有被当作跳板去攻击
第三方、或把服务器 IP 刷进黑名单的风险。用 iptables 按 uid 封掉：

```bash
# 只允许 csbb 访问回环（后端本身不需要任何外网访问），其余出站一律拒绝
iptables -A OUTPUT -m owner --uid-owner csbb -d 127.0.0.0/8 -j ACCEPT
iptables -A OUTPUT -m owner --uid-owner csbb -j REJECT

# 持久化（重启后仍生效）
apt install -y iptables-persistent
netfilter-persistent save
```

验证（应超时/失败）：

```bash
sudo -u csbb curl -s -m 3 http://1.1.1.1 -o /dev/null; echo "exit=$?"   # 期望非 0
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/         # 期望 200（回环仍通）
```

## 8. 上线自检清单

```bash
# a) 后端在跑，且只监听回环
ss -lntp | grep 8000                      # 应显示 127.0.0.1:8000，不能是 0.0.0.0:8000

# b) HTTPS 与关键接口
curl -s -o /dev/null -w 'home    %{http_code}\n' https://csblackbookhub.com/
curl -s -o /dev/null -w 'www     %{http_code}\n' https://www.csblackbookhub.com/
curl -s -o /dev/null -w 'api     %{http_code}\n' https://csblackbookhub.com/api/v1/chapters
curl -s -o /dev/null -w 'static  %{http_code}\n' https://csblackbookhub.com/static/docs/ws-http.pdf   # 期望 200（PDF 已单独上传）
curl -s -o /dev/null -w 'docs    %{http_code}\n' https://csblackbookhub.com/docs      # 期望 404（已关）

# c) HTTP 应 301 跳到 HTTPS
curl -s -o /dev/null -w 'http->   %{http_code} %{redirect_url}\n' http://csblackbookhub.com/

# d) 8000 端口不能从公网直连（在本地机器执行；期望连不上）
curl -s -m 3 http://csblackbookhub.com:8000/ ; echo "exit=$?"

# e) 判题可用：参考答案应 passed=true
curl -s https://csblackbookhub.com/api/v1/chapters/ch5/labs/sock-icmp \
  | python3 -c "import sys,json;open('/tmp/ref.py','w').write(json.load(sys.stdin)['reference_code'])"
python3 - <<'PY'
import json, urllib.request
code = open('/tmp/ref.py').read()
req = urllib.request.Request(
    'https://csblackbookhub.com/api/v1/chapters/ch5/labs/sock-icmp/run',
    data=json.dumps({'code': code}).encode(),
    headers={'Content-Type': 'application/json'},
)
print('judge passed =', json.load(urllib.request.urlopen(req))['passed'])
PY

# f) 限流生效：连打 13 次，第 13 次应为 429
for i in $(seq 1 13); do
  curl -s -o /dev/null -w "$i:%{http_code} " -X POST \
    -H 'Content-Type: application/json' \
    -d '{"code":"pass"}' \
    https://csblackbookhub.com/api/v1/chapters/ch5/labs/sock-icmp/run
done; echo

# g) 判题代码确实打不出外网（期望非 0 退出码）
sudo -u csbb curl -s -m 3 http://1.1.1.1 -o /dev/null; echo "csbb 出站 exit=$?"
```

## 9. 日常运维

```bash
systemctl restart csbb-backend          # 改完代码后重启
journalctl -u csbb-backend -f           # 看日志

# 被刷了？一条命令止血（改 unit 里的 JUDGE_ENABLED 后重启）
sed -i 's/JUDGE_ENABLED=true/JUDGE_ENABLED=false/' /etc/systemd/system/csbb-backend.service
systemctl daemon-reload && systemctl restart csbb-backend

# 发新版本：本地重新 build → 覆盖 /var/www/cs-blackbook → 后端改了就 restart
```

## 10. 更新依赖版本时

```bash
# 本地改 backend/requirements.txt 的版本号
pip install --dry-run --ignore-installed --python-version 3.11 --implementation cp \
    --abi cp311 --platform manylinux2014_x86_64 --only-binary=:all: \
    --report report.json -r backend/requirements.txt
# 按 report.json 更新 requirements.lock.txt，再上传并重装
```
