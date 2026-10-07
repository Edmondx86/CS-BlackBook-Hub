<script setup>
// 学习路线图：五层“自顶向下”天梯（L5 应用层 → L1 物理层）+ 右侧详情展板。
// 由 intro.md 里嵌入的独立 HTML/JS 迁移而来：交互改用 Vue 响应式，链接指向真实章节路由。
import { computed, ref } from 'vue'

// 每一层对应一个后端章节：L5→ch2、L4→ch3、L3→ch4（+ch5 控制平面）、L2→ch6、L1→ch1。
// 课程未单独设“物理层”章节，L1 指向基础章 ch1《计算机网络与因特网》。
const layers = [
  {
    level: 5,
    badge: 'L5',
    title: '应用层 (Application Layer)',
    subtitle: '网络应用程序及其应用层协议',
    chapter: {
      title: '第二章 · 应用层（Application Layer）',
      desc: '网络应用是构建计算机网络的理由。在此层你将理解 HTTP 响应流程、DNS 域名解析以及 Socket 编程。',
      protocols: ['HTTP / HTTPS', 'DNS', 'SMTP', 'WebSocket'],
      route: '/chapters/ch2',
    },
  },
  {
    level: 4,
    badge: 'L4',
    title: '运输层 (Transport Layer)',
    subtitle: '进程到进程的报文传输',
    chapter: {
      title: '第三章 · 运输层（Transport Layer）',
      desc: '剖析 TCP 协议的可靠数据传输机制、滑动窗口、流量控制与 UDP 的无连接高效传输。',
      protocols: ['TCP', 'UDP', 'QUIC'],
      route: '/chapters/ch3',
    },
  },
  {
    level: 3,
    badge: 'L3',
    title: '网络层 (Network Layer)',
    subtitle: '主机到主机的源到目的地数据报传送',
    chapter: {
      title: '网络层：数据平面 + 控制平面（Network Layer）',
      desc: '数据平面负责转发、控制平面负责路由选择。掌握 IP 编址与转发，以及 OSPF/BGP 路由算法与 SDN。',
      protocols: ['IPv4 / IPv6', 'ICMP', 'OSPF', 'BGP', 'SDN'],
      route: '/chapters/ch4',
      label: '数据平面',
      secondary: { label: '控制平面', route: '/chapters/ch5' },
    },
  },
  {
    level: 2,
    badge: 'L2',
    title: '链路层 (Link Layer)',
    subtitle: '相邻网络节点间的帧传输',
    chapter: {
      title: '第六章 · 链路层与局域网（The Link Layer and LANs）',
      desc: '局域网内的帧传输。探索 MAC 地址、ARP 寻址以及以太网的碰撞检测机制。',
      protocols: ['Ethernet', 'Wi-Fi (802.11)', 'ARP'],
      route: '/chapters/ch6',
    },
  },
  {
    level: 1,
    badge: 'L1',
    title: '物理层 (Physical Layer)',
    subtitle: '链路上的比特传输',
    chapter: {
      title: '第一章 · 计算机网络与因特网（Computer Networks and the Internet）',
      desc: '微观世界中的光电信号接力。了解分组交换、协议分层与物理传输介质的基本特性。',
      protocols: ['Manchester Code', 'Fiber', 'NRZ'],
      route: '/chapters/ch1',
    },
  },
]

const activeLevel = ref(5)
const active = computed(() => layers.find((l) => l.level === activeLevel.value))
</script>

<template>
  <div class="roadmap">
    <!-- 左侧天梯 -->
    <div class="ladder">
      <button
        v-for="layer in layers"
        :key="layer.level"
        type="button"
        class="layer-card"
        :class="{ active: layer.level === activeLevel }"
        @click="activeLevel = layer.level"
      >
        <div class="level-badge">{{ layer.badge }}</div>
        <div class="layer-info">
          <div class="layer-title">{{ layer.title }}</div>
          <div class="layer-subtitle">{{ layer.subtitle }}</div>
        </div>
      </button>
    </div>

    <!-- 右侧详情展板 -->
    <div class="detail-panel">
      <h3 class="detail-title">{{ active.chapter.title }}</h3>
      <p class="detail-desc">{{ active.chapter.desc }}</p>
      <h4 class="detail-sub">核心协议与概念：</h4>
      <div class="protocols">
        <span v-for="p in active.chapter.protocols" :key="p" class="protocol-tag">{{ p }}</span>
      </div>
      <RouterLink :to="active.chapter.route" class="btn-enter">{{ active.chapter.label ?? '进入关卡学习' }} ➔</RouterLink>
      <RouterLink
        v-if="active.chapter.secondary"
        :to="active.chapter.secondary.route"
        class="btn-enter btn-enter-secondary"
      >
        {{ active.chapter.secondary.label }} ➔
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
/* 站点主题色统一由 src/theme.css 定义（theme 主题紫 / brand 品牌青绿），
   此处仅做局部别名，不再硬编码色值。 */
.roadmap {
  --accent: rgb(var(--theme));
  --accent-soft: rgb(var(--theme) / 0.12);
  --accent-border: rgb(var(--theme) / 0.35);
  --accent-glow: rgb(var(--theme) / 0.18);

  display: flex;
  gap: 28px;
  align-items: stretch;
}
.ladder {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: relative;
}
/* 贯穿各关卡徽章的连接线 */
.ladder::before {
  content: '';
  position: absolute;
  left: 34px;
  top: 20px;
  bottom: 20px;
  width: 4px;
  background: rgb(var(--border-strong));
}
.layer-card {
  position: relative;
  z-index: 1;
  background: rgb(var(--bg-card));
  border: 1px solid rgb(var(--border-strong));
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  text-align: left;
  cursor: pointer;
  color: inherit;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.layer-card:hover {
  border-color: var(--accent);
  transform: translateX(8px);
  box-shadow: 0 4px 20px var(--accent-glow);
}
.layer-card.active {
  border-color: rgb(var(--brand));
  background: rgb(var(--bg-elevated));
}
.level-badge {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgb(var(--bg-elevated));
  border: 2px solid rgb(var(--border-strong));
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: var(--accent);
  flex-shrink: 0;
}
.layer-card:hover .level-badge {
  background: var(--accent);
  color: rgb(var(--text-inverse));
}
.layer-info {
  flex: 1;
}
.layer-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: rgb(var(--text-primary));
}
.layer-subtitle {
  font-size: 0.85rem;
  color: rgb(var(--text-muted));
  margin-top: 4px;
}
.detail-panel {
  flex: 1;
  background: rgb(var(--bg-card));
  border: 1px solid rgb(var(--border-strong));
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
}
.detail-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: rgb(var(--text-primary));
}
.detail-desc {
  color: rgb(var(--text-muted));
  line-height: 1.6;
  margin: 12px 0 0;
}
.detail-sub {
  color: rgb(var(--text-primary));
  font-size: 0.9rem;
  margin: 18px 0 8px;
}
.protocols {
  margin-bottom: 20px;
}
.protocol-tag {
  display: inline-block;
  background: var(--accent-soft);
  color: var(--accent);
  border: 1px solid var(--accent-border);
  padding: 4px 10px;
  border-radius: 6px;
  margin: 4px 4px 0 0;
  font-size: 0.85rem;
  font-family: monospace;
}
.btn-enter {
  margin-top: auto;
  background: rgb(var(--brand));
  color: rgb(var(--text-inverse));
  text-decoration: none;
  text-align: center;
  padding: 10px;
  border-radius: 6px;
  font-weight: 600;
  transition: background 0.2s;
}
.btn-enter:hover {
  background: rgb(var(--brand-dark));
}
.btn-enter-secondary {
  margin-top: 8px;
  background: var(--accent);
  color: rgb(var(--text-inverse));
}
.btn-enter-secondary:hover {
  background: var(--accent);
  filter: brightness(1.12);
}
/* 移动端改为上下堆叠 */
@media (max-width: 768px) {
  .roadmap {
    flex-direction: column;
  }
}
</style>
