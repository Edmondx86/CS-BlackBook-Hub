<script setup>
// 首页：全屏走马灯 + 学习路线图 + 向下滚动后的“网站介绍”与“About Us”。
// 走马灯每 3 秒自动轮换（悬停不暂停）；每张幻灯片配有对应的名言 / 知识点。
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Roadmap from '../components/Roadmap.vue'
import { headerScrolled } from '../composables/useHeader'
import { tools } from '../data/tools'

// 主页标题“欢迎来到 CS-BlackBook-Hub”的滚动显现状态
const introSection = ref(null)
const introVisible = ref(false)
let revealObserver = null

// 滚动显现指令：v-reveal 让模块进入视口时从下方滑入，离开时隐藏（可重复）
const vReveal = {
  mounted(el) {
    el.classList.add('reveal')
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          el.classList.toggle('is-visible', entry.intersectionRatio >= 0.15)
        }
      },
      { threshold: [0, 0.15] },
    )
    observer.observe(el)
    el._revealObserver = observer
  },
  unmounted(el) {
    el._revealObserver?.disconnect()
  },
}

// 每张幻灯片的文字内容与背景明暗判定：
//   light = false 表示背景偏暗 → 使用白色文字；true 表示背景偏亮 → 使用黑色文字。
const slides = [
  {
    img: '/images/1.jpg',
    title: '"The Internet is a reflection of our society and that reflection is not always pretty."',
    sub: '"互联网是人类社会的投影，而这面镜子并非时刻尽善尽美。"',
    author: '— Vinton Cerf',
    light: true,
  },
  {
    img: '/images/2.jpg',
    title: '从浏览器发起请求的那一刻起，探索网络世界的入口。',
    sub: '',
    author: '',
    light: false,
  },
  {
    img: '/images/3.jpg',
    title: '"Fuck NVIDIA."',
    sub: '',
    author: '— Linus Torvalds',
    light: false,
  },
  {
    img: '/images/4.jpg',
    title: '在最近的距离交接光电，于最深的底层筑起相连。',
    sub: '',
    author: '',
    light: false,
  },
  {
    img: '/images/5.jpg',
    title: '"The Web as I envisaged it, we have not seen it yet. The future is still so much bigger than the past."',
    sub: '"我设想中的万维网尚未完全展现，未来的宏图远比过去更广阔。"',
    author: '— Tim Berners-Lee',
    light: true,
  },
]

// “为什么选择这里”特性
const whyChoose = [
  {
    title: '自顶向下天梯图',
    desc: '模块化拆解，像打游戏一样逐层通关。',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg>',
  },
  {
    title: 'Wireshark 官方 Lab',
    desc: '配套图解指导，一步步抓包验证。',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
  },
  {
    title: '在线 WebSocket 评测',
    desc: '内置 Client/Server 沙盒，即写即测。',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>',
  },
]

// “你将学到什么”四层特性
const learnLayers = [
  {
    title: '应用层 (L5)',
    desc: '深入 HTTP/DNS 机制，动手编写 Socket 与 WebSocket 实时通讯。',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>',
  },
  {
    title: '运输层 (L4)',
    desc: '剖析 TCP 可靠数据传输、超时重传与 UDP 高性能传输。',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>',
  },
  {
    title: '网络层 (L3)',
    desc: '搞懂 IP 编址、CIDR 子网划分与路由器转发逻辑。',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>',
  },
  {
    title: '链路层 (L2)',
    desc: '拆解 MAC 地址、ARP 协议与以太网碰撞检测。',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
  },
]

const current = ref(0)
let timer = null

function next() {
  current.value = (current.value + 1) % slides.length
}
function prev() {
  current.value = (current.value - 1 + slides.length) % slides.length
}
function go(i) {
  current.value = i
}

function startAuto() {
  stopAuto()
  timer = setInterval(next, 3000)
}
function stopAuto() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

// 标题滚动进入视口后向上滑出（可重复：进入显现、离开隐藏，再次进入再次显现）
function setupTitleReveal() {
  const title = introSection.value?.querySelector('.intro-hero')
  if (!title) return
  revealObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        introVisible.value = entry.intersectionRatio >= 0.2
      }
    },
    { threshold: [0, 0.2] },
  )
  revealObserver.observe(title)
}

onMounted(() => {
  startAuto()
  setupTitleReveal()
})
onBeforeUnmount(() => {
  stopAuto()
  revealObserver?.disconnect()
})

/* ==========================================================================
   支持本站：收款码弹窗（微信 + 支付宝两张并排）
   --------------------------------------------------------------------------
   图片约定：frontend/public/images/donate-wechat.png 与 donate-alipay.png。
   部署时图片可能尚未就位，此时该槽位的 <img> 的 @error 触发降级文案（不显示
   破图图标）；每次打开都会重置全部失败状态，所以之后把图片放进去，重新打开
   弹窗即可正常显示。两个槽位各自独立记录失败状态，因此可以出现
   “微信正常、支付宝降级”这种组合，不会因为一张缺失就把整个弹窗变成提示。
   ========================================================================== */
const donateOpen = ref(false)

// 收款码路径必须走 JS 常量 + :src 动态绑定：如果写成静态 src="/images/donate-wechat.png"，
// Vite 会在构建期尝试解析这两个尚不存在的文件并直接构建失败（Rollup failed to resolve
// import），@error 降级根本轮不到生效。
const donateWechatSrc = '/images/donate-wechat.png'
const donateAlipaySrc = '/images/donate-alipay.png'

// 两个槽位：标签放在图片下方，src 全部来自上面的常量。
const donateSlots = [
  { key: 'wechat', label: '微信', src: donateWechatSrc },
  { key: 'alipay', label: '支付宝', src: donateAlipaySrc },
]

// 按槽位 key 记录加载失败状态：{ wechat: false, alipay: false }。
const donateQrFailed = ref(Object.fromEntries(donateSlots.map((slot) => [slot.key, false])))
const donateTrigger = ref(null) // 触发按钮：关闭后把焦点还给它
const donateCloseBtn = ref(null) // 关闭按钮：打开后焦点移到这里
const scrollRoot = ref(null) // 首页真正的滚动容器（见模板根节点）

// 打开前的 overflow 快照，关闭 / 卸载时原样恢复，避免把页面锁死。
let bodyOverflowBefore = ''
let rootOverflowBefore = ''

// 打开时禁止背景滚动：任务要求锁 body；而首页的实际滚动发生在根节点
// （.h-full.overflow-y-auto）上，只锁 body 挡不住背景滚动，所以两者一起锁。
function lockScroll() {
  bodyOverflowBefore = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  if (scrollRoot.value) {
    rootOverflowBefore = scrollRoot.value.style.overflow
    scrollRoot.value.style.overflow = 'hidden'
  }
}

function unlockScroll() {
  document.body.style.overflow = bodyOverflowBefore
  if (scrollRoot.value) scrollRoot.value.style.overflow = rootOverflowBefore
}

function onDonateKeydown(e) {
  if (e.key === 'Escape') closeDonate()
}

function openDonate() {
  // 每次打开都重置两个槽位的失败状态：之后把图片放进去，重开弹窗即可正常显示。
  for (const slot of donateSlots) donateQrFailed.value[slot.key] = false
  donateOpen.value = true
}

function closeDonate() {
  donateOpen.value = false
}

// 打开：锁滚动 + Esc 监听 + 焦点移到关闭按钮；关闭：解锁 + 交还焦点。
watch(donateOpen, async (open) => {
  if (open) {
    lockScroll()
    document.addEventListener('keydown', onDonateKeydown)
    await nextTick()
    donateCloseBtn.value?.focus()
  } else {
    document.removeEventListener('keydown', onDonateKeydown)
    unlockScroll()
    donateTrigger.value?.focus()
  }
})

// 组件卸载（例如切换路由）时兜底：解除监听并恢复 overflow，不留副作用。
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onDonateKeydown)
  unlockScroll()
})

// 文字阴影：深色背景用深色阴影、浅色背景用浅色光晕，保证与背景的区分度。
function shadowFor(light) {
  return light
    ? '0 1px 2px rgba(255,255,255,0.9), 0 2px 20px rgba(255,255,255,0.55)'
    : '0 2px 4px rgba(0,0,0,0.85), 0 4px 24px rgba(0,0,0,0.55)'
}

// 底部渐变遮罩：为“中间偏下”的文字区域提供稳定底色。
function overlayFor(light) {
  return light
    ? 'bg-gradient-to-t from-white/55 via-white/10 to-transparent'
    : 'bg-gradient-to-t from-black/65 via-black/15 to-transparent'
}

// 平滑滚动到页面最底端的 About Us 区块。
function scrollToAbout() {
  document.getElementById('about')?.scrollIntoView({ behavior: 'smooth' })
}

// 首页滚动：滚动离开走马灯区域（约一屏高度）后，通知页头切换为半透明。
function onScroll(e) {
  headerScrolled.value = e.target.scrollTop > window.innerHeight - 150
}
</script>

<template>
  <div ref="scrollRoot" class="h-full overflow-y-auto" @scroll="onScroll">
    <!-- ======================= 全屏走马灯 ======================= -->
    <section class="relative h-full w-full overflow-hidden">
      <!-- 幻灯片（交叉淡入淡出） -->
      <div
        v-for="(slide, i) in slides"
        :key="slide.img"
        class="absolute inset-0 transition-opacity duration-1000 ease-in-out"
        :class="i === current ? 'z-10 opacity-100' : 'pointer-events-none z-0 opacity-0'"
      >
        <img
          :src="slide.img"
          alt=""
          class="absolute inset-0 h-full w-full object-cover"
        />
        <!-- 底部渐变遮罩，提升文字可读性 -->
        <div class="absolute inset-0" :class="overlayFor(slide.light)"></div>

        <!-- 文字：位于界面中间偏下 -->
        <div
          class="relative z-10 flex h-full translate-y-[14vh] flex-col items-center justify-center px-6 text-center"
          :class="slide.light ? 'text-black' : 'text-white'"
          :style="{ textShadow: shadowFor(slide.light) }"
        >
          <h2
            class="max-w-4xl text-2xl font-bold leading-tight tracking-tight sm:text-4xl lg:text-5xl"
          >
            {{ slide.title }}
          </h2>
          <p v-if="slide.sub" class="mt-4 max-w-3xl text-base font-medium sm:text-xl lg:text-2xl">
            {{ slide.sub }}
          </p>
          <p v-if="slide.author" class="mt-5 text-base font-medium italic sm:text-lg">
            {{ slide.author }}
          </p>

        </div>
      </div>

      <!-- 固定的 CTA：开始探索 + About Us（位置不随幻灯片变化） -->
      <div
        class="absolute inset-x-0 bottom-[12%] z-20 flex flex-wrap items-center justify-center gap- px-6"
      >
        <RouterLink
          to="/chapters"
          class="inline-flex items-center gap-6 rounded-full border border-white/20 bg-btn/70 px-10 py-4 text-lg font-semibold text-btn-text shadow-lg shadow-black/25 backdrop-blur-md transition duration-200 hover:scale-105 hover:bg-btn-hover/85"
        >
          开始探索
          <span aria-hidden="true">→</span>
        </RouterLink>
      </div>

      <!-- 左右切换箭头 -->
      <button
        type="button"
        aria-label="上一张"
        @click="prev"
        class="absolute left-4 top-1/2 z-20 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-black/25 text-2xl text-white/[var(--alpha-strong)] backdrop-blur-sm transition hover:bg-black/45 hover:text-white"
      >
        ‹
      </button>
      <button
        type="button"
        aria-label="下一张"
        @click="next"
        class="absolute right-4 top-1/2 z-20 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-black/25 text-2xl text-white/[var(--alpha-strong)] backdrop-blur-sm transition hover:bg-black/45 hover:text-white"
      >
        ›
      </button>

      <!-- 指示圆点 -->
      <div class="absolute bottom-6 left-1/2 z-20 flex -translate-x-1/2 gap-2">
        <button
          v-for="(slide, i) in slides"
          :key="slide.img"
          type="button"
          :aria-label="`切换到第 ${i + 1} 张`"
          @click="go(i)"
          class="h-2 rounded-full transition-all duration-300"
          :class="i === current ? 'w-6 bg-white' : 'w-2 bg-white/50 hover:bg-white/80'"
        ></button>
      </div>
    </section>

    <!-- ======================= Hero ======================= -->
    <section
      ref="introSection"
      class="intro-reveal mx-auto max-w-7xl px-6 py-24"
      :class="{ 'is-visible': introVisible }"
    >
      <h1 class="intro-hero">欢迎来到 CS-BlackBook-Hub<span class="intro-hero-cursor" aria-hidden="true"></span></h1>
      <h2 class="intro-sub text-2xl font-bold text-primary">计算机交互式自学平台</h2>
      <p class="intro-tagline mt-3 max-w-md text-lg text-muted">告别枯燥的"大黑书"，用图解、抓包与在线沙盒，轻松啃下计网硬骨头！（别问为什么是计网硬骨头，因为目前只做了计网的🫠）</p>
    </section>

    <!-- ======================= 学习路线图 ======================= -->
    <section v-reveal class="mx-auto max-w-7xl px-6 py-14">
      <h1 class="text-3xl font-bold text-primary">学习路线</h1>
      <p class="mt-2 text-xl text-tertiary">自顶向下，从应用层一路探到底层的比特传输。</p>
      <Roadmap class="mt-8" />
      <div class="mt-6 flex justify-center">
        <RouterLink
  to="/chapters/ch1"
  class="group relative flex items-center justify-center overflow-hidden rounded-xl border border-brand/30 bg-card/40 py-4 transition-transform duration-300 hover:scale-[1.03] hover:border-brand/70"
>
  <span class="relative z-10 px-16 text-lg font-semibold text-primary">从第一章开始</span>
  <span
    class="slide-panel absolute inset-y-0 right-0 flex w-[61.8%] translate-x-full items-center justify-end bg-gradient-to-l from-brand via-brand/70 to-transparent pr-8 transition-transform duration-300 ease-out group-hover:translate-x-0"
  >
    <span aria-hidden="true" class="transition-transform group-hover:translate-x-1">→</span>
  </span>
</RouterLink>
      </div>
    </section>

    <!-- ======================= 常见工具 ======================= -->
    <section v-reveal class="mx-auto max-w-7xl px-6 py-14">
      <h2 class="text-3xl font-bold text-primary">常见工具</h2>
      <p class="mt-2 text-xl text-tertiary">四个好帮手，覆盖抓包、诊断、编程与仿真。</p>

      <div class="mt-8 grid grid-cols-1 gap-6 md:grid-cols-10">
        <RouterLink
          v-for="(tool, i) in tools"
          :key="tool.title"
          :to="tool.route"
          class="group relative flex min-h-[300px] flex-col overflow-hidden rounded-xl border border-cardline bg-card/40 transition-colors hover:border-brand/40"
          :class="i === 0 || i === 3 ? 'md:col-span-3' : 'md:col-span-7'"
        >
          <!-- 网络诊断工具（MTR）sprite 背景（悬停播放帧动画） -->
          <div v-if="i === 0" class="mtr-sprite pointer-events-none absolute inset-0 z-0"></div>

          <!-- Wireshark sprite 背景（悬停播放帧动画） -->
          <div v-if="i === 1" class="ws-sprite pointer-events-none absolute inset-0 z-0"></div>

          <!-- Socket sprite 背景（悬停播放帧动画） -->
          <div v-if="i === 2" class="socket-sprite pointer-events-none absolute inset-0 z-0"></div>

          <!-- Cisco Packet Tracer sprite 背景（悬停播放帧动画） -->
          <div v-if="i === 3" class="cisco-sprite pointer-events-none absolute inset-0 z-0"></div>

          <!-- 图标（顶部） -->
          <div class="relative z-10 p-6 pb-0">
            <div
              class="origin-left text-brand transition-transform duration-300 ease-in-out group-hover:scale-75"
              v-html="tool.icon"
            ></div>
          </div>

          <!-- 文字（底部，下半部分） -->
          <div class="relative z-10 mt-auto p-6">
            <h3 class="text-left text-xl font-semibold text-secondary transition-colors group-hover:text-brand-light">{{ tool.title }}</h3>
            <p class="mt-1 max-w-lg text-left text-sm leading-relaxed text-muted">{{ tool.desc }}</p>
            <span class="mt-3 inline-flex items-center gap-2 text-sm font-medium text-brand opacity-0 transition-opacity duration-300 group-hover:opacity-100">
              了解更多
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg>
            </span>
          </div>

          <!-- 悬停高亮层 -->
          <div class="pointer-events-none absolute inset-0 transform-gpu transition-all duration-300 group-hover:bg-brand/5"></div>
        </RouterLink>
      </div>
    </section>

    <!-- ======================= 为什么选择这里 ======================= -->
    <section v-reveal class="mx-auto max-w-7xl px-6 py-14">
      <h2 class="text-3xl font-bold text-primary">为什么选择这里</h2>
      <div class="mt-8 grid grid-cols-1 gap-8 md:grid-cols-2">
        <div v-for="f in whyChoose" :key="f.title" class="flex flex-row items-start gap-4">
          <div
            class="flex h-14 w-14 shrink-0 items-center justify-center rounded-md border border-line text-brand transition-colors hover:bg-elevated/50"
            v-html="f.icon"
          ></div>
          <div class="flex flex-col">
            <h3 class="text-lg font-semibold text-primary">{{ f.title }}</h3>
            <p class="max-w-64 text-sm text-muted">{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ======================= 你将学到什么 ======================= -->
    <section v-reveal class="mx-auto max-w-7xl px-6 py-14">
      <h2 class="text-3xl font-bold text-primary">你将学到什么</h2>
      <div class="mt-8 grid grid-cols-1 gap-8 md:grid-cols-2">
        <div v-for="f in learnLayers" :key="f.title" class="flex flex-row items-start gap-4">
          <div
            class="flex h-14 w-14 shrink-0 items-center justify-center rounded-md border border-line text-brand transition-colors hover:bg-elevated/50"
            v-html="f.icon"
          ></div>
          <div class="flex flex-col">
            <h3 class="text-lg font-semibold text-primary">{{ f.title }}</h3>
            <p class="max-w-64 text-sm text-muted">{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ======================= 开源与致谢 ======================= -->
    <section v-reveal class="mx-auto max-w-7xl px-6 py-14">
      <h2 class="text-3xl font-bold text-primary">开源与致谢</h2>
      <p class="mt-3 max-w-4xl text-base text-tertiary">
        本站部分优质教学材料与实验设计借鉴了 GitHub 开源项目
        <a
          href="https://github.com/moranzcw/Computer-Networking-A-Top-Down-Approach-NOTES"
          target="_blank"
          rel="noopener"
          class="text-theme-light transition hover:underline"
        >Computer-Networking-A-Top-Down-Approach-NOTES</a>。
      </p>
      <ul class="mt-4 space-y-2 text-base text-tertiary">
        <li>
          <strong class="font-semibold text-primary">项目源码</strong>：
          <a href="#" class="text-theme-light transition hover:underline">GitHub 仓库</a>（欢迎 Star）
        </li>
        <li>
          <strong class="font-semibold text-primary">意见反馈</strong>：联系作者邮箱
          <code class="rounded bg-elevated px-1.5 py-0.5 text-sm">aide_0708@qq.com/aide0708@163.com</code>
        </li>
        <li>
          <strong class="font-semibold text-primary">支持本站</strong>：本站完全免费且由个人运维，如果对你有帮助，欢迎
          <button
            ref="donateTrigger"
            type="button"
            class="text-theme-light transition hover:underline"
            @click="openDonate"
          >请作者喝杯咖啡</button>！
        </li>
      </ul>
    </section>

    <!-- ======================= 开始学习 CTA ======================= -->
    <section v-reveal class="mx-auto max-w-7xl px-6 py-14 text-center">
      <h2 class="py-4 text-6xl font-bold text-primary">准备好开启你的网络之旅了吗？😽</h2>
      <div class="mt-6 flex justify-center">
        <RouterLink
          to="/chapters"
          class="group relative flex items-center justify-center overflow-hidden rounded-xl border border-brand/30 bg-card/40 py-4 transition-transform duration-300 hover:scale-[1.03] hover:border-brand/70"
        >
          <span class="relative z-10 px-16 text-lg font-semibold text-primary">立即进入章节学习</span>
          <span
            class="slide-panel absolute inset-y-0 right-0 flex w-[61.8%] translate-x-full items-center justify-end bg-gradient-to-l from-brand via-brand/70 to-transparent pr-8 transition-transform duration-300 ease-out group-hover:translate-x-0"
          >
            <span aria-hidden="true" class="transition-transform group-hover:translate-x-1">→</span>
          </span>
        </RouterLink>
      </div>
    </section>

    <!-- ======================= 品牌跑马灯 ======================= -->
    <section class="relative overflow-hidden py-16" aria-hidden="true">
      <div class="brand-marquee">
        <div class="brand-marquee-track">
          <span v-for="n in 6" :key="n" class="brand-marquee-item">CSBLACKBOOKHUB</span>
        </div>
      </div>
    </section>

    <!-- ======================= 页脚 ======================= -->
    <footer class="border-t border-line/60 px-6 py-10 text-center">
      <p class="text-sm italic text-muted">
        Top-Down Networking — Understanding the Internet, One Layer at a Time.
      </p>
      <p class="mt-3 text-xs text-faint">
        © 2026 Computer Network Top-Down Learning. Designed for Geeks &amp; Learners.<br />
        基于《Computer Networking: A Top-Down Approach》理念构建 | 遵守 MIT 开源协议
      </p>
      <!--
        备案信息：两套系统各一个号，按要求在网站底部公示。
        · ICP 备案      → 工信部备案管理系统
        · 公安联网备案  → 全国互联网安全管理服务平台
        公安备案的官方片段还带一枚公安徽标图片（备案平台“已备案网站”详情里可下载），
        需要的话把图标放到 frontend/public/ 下，在下面那个链接里加 <img> 即可。
      -->
      <p class="mt-3 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-faint">
        <a
          href="https://beian.miit.gov.cn/"
          target="_blank"
          rel="noopener noreferrer"
          class="transition hover:text-theme-light"
        >
          辽ICP备2026021355号
        </a>
        <a
          href="https://beian.mps.gov.cn/#/query/webSearch?code=21011202001420"
          target="_blank"
          rel="noopener noreferrer"
          class="transition hover:text-theme-light"
        >
          辽公网安备21011202001420号
        </a>
      </p>
    </footer>

    <!-- ======================= 收款码弹窗（Teleport 到 body，避免被父级裁切） ======================= -->
    <Teleport to="body">
      <!-- 遮罩：flex + overflow-y-auto + 卡片 m-auto，既能垂直居中，又不会在矮视口裁掉顶部 -->
      <div
        v-if="donateOpen"
        class="fixed inset-0 z-[100] flex overflow-y-auto bg-black/60 p-4 backdrop-blur-sm"
        @click.self="closeDonate"
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="donate-dialog-title"
          class="relative m-auto w-full max-w-md rounded-xl border border-line bg-card p-6 text-center text-primary shadow-2xl"
        >
          <button
            ref="donateCloseBtn"
            type="button"
            aria-label="关闭"
            class="absolute right-3 top-3 grid h-8 w-8 place-items-center rounded-lg text-muted transition hover:bg-elevated hover:text-primary"
            @click="closeDonate"
          >
            ✕
          </button>

          <h3 id="donate-dialog-title" class="text-xl font-semibold text-primary">请作者喝杯咖啡</h3>
          <p class="mt-2 text-sm text-muted">本站完全免费，由个人运维；如果对你有帮助，欢迎支持。</p>

          <!-- 收款码：微信 / 支付宝两个槽位，窄屏上下堆叠、宽屏并排；
               某个槽位的图片未就位时只有那一格降级为提示，不影响另一格。 -->
          <div class="mt-5 flex flex-col items-center justify-center gap-4 sm:flex-row sm:items-start">
            <div
              v-for="slot in donateSlots"
              :key="slot.key"
              class="flex w-full flex-col items-center sm:flex-1"
            >
              <img
                v-if="!donateQrFailed[slot.key]"
                :src="slot.src"
                :alt="`${slot.label}收款码`"
                class="w-full max-w-[200px] rounded border border-line/60 object-contain"
                @error="donateQrFailed[slot.key] = true"
              />
              <p
                v-else
                class="flex w-full max-w-[200px] min-h-[200px] items-center justify-center rounded border border-dashed border-line/60 bg-elevated/40 px-4 py-10 text-sm text-muted"
              >
                收款码准备中，稍后再来看看
              </p>
              <span class="mt-2 text-sm text-muted">{{ slot.label }}</span>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<style>
/* 主页 Hero：标题 / 副标题 / tagline 三行从下方滑上 + 淡入（错峰） */
.intro-reveal .intro-hero,
.intro-reveal .intro-sub,
.intro-reveal .intro-tagline {
  opacity: 0;
  transform: translateY(40px);
  transition:
    opacity 0.7s ease,
    transform 0.7s cubic-bezier(0.22, 1, 0.36, 1);
}
.intro-reveal.is-visible .intro-hero {
  opacity: 1;
  transform: translateY(0);
}
.intro-reveal.is-visible .intro-sub {
  opacity: 1;
  transform: translateY(0);
  transition-delay: 0.1s;
}
.intro-reveal.is-visible .intro-tagline {
  opacity: 1;
  transform: translateY(0);
  transition-delay: 0.2s;
}

/* 通用模块滚动显现（v-reveal） */
.reveal {
  opacity: 0;
  transform: translateY(64px);
  transition:
    opacity 0.7s ease,
    transform 0.7s cubic-bezier(0.22, 1, 0.36, 1);
}
.reveal.is-visible {
  opacity: 1;
  transform: translateY(0);
}

/* Wireshark 卡片 sprite 背景：悬停播放帧动画，非悬停显示第一帧并调暗 */
.ws-sprite {
  background-image: url('/images/wireshark-sprite.png');
  background-size: auto 480px;
  background-position: -5667px center;
  background-repeat: no-repeat;
  filter: brightness(0.2);
  transition: filter 0.3s ease;
}
.group:hover .ws-sprite {
  animation: ws-play 1.4s steps(6) infinite;
  filter: brightness(0.5);
}
@keyframes ws-play {
  from {
    background-position: -42px center;
  }
  to {
    background-position: -5667px center;
  }
}

/* 网络诊断工具（MTR）卡片 sprite 背景：悬停播放帧动画，非悬停显示第一帧并调暗 */
.mtr-sprite {
  background-image: url('/images/mtr-sprite.png');
  background-size: auto 402px;
  background-position: -7497px center;
  background-repeat: no-repeat;
  filter: brightness(0.5);
  transition: filter 0.3s ease;
}
.group:hover .mtr-sprite {
  animation: mtr-play 3s steps(21) infinite;
  filter: brightness(0.7);
}
@keyframes mtr-play {
  from {
    background-position: 0 center;
  }
  to {
    background-position: -7497px center;
  }
}

/* Socket 卡片 sprite 背景：悬停播放帧动画，非悬停显示第一帧并调暗 */
.socket-sprite {
  background-image: url('/images/socket-sprite.png');
  background-size: auto 500px;
  background-position: -34470px 80%;
  background-repeat: no-repeat;
  filter: brightness(0.5);
  transition: filter 0.3s ease;
}
.group:hover .socket-sprite {
  animation: socket-play 2s steps(24) infinite;
  filter: brightness(0.7);
}
@keyframes socket-play {
  from {
    background-position: -270px 8%;
  }
  to {
    background-position: -34470px 40%;
  }
}

/* Cisco Packet Tracer 卡片 sprite 背景：悬停播放帧动画，非悬停显示最后一帧并调暗 */
.cisco-sprite {
  background-image: url('/images/cisco-sprite.png');
  background-size: auto 456px;
  background-position: -13878px center;
  background-repeat: no-repeat;
  filter: brightness(0.22);
  transition: filter 0.3s ease;
}
.group:hover .cisco-sprite {
  animation: cisco-play 2s steps(26) infinite;
  filter: brightness(0.6);
}
@keyframes cisco-play {
  from {
    background-position: 0 center;
  }
  to {
    background-position: -13878px center;
  }
}

/* 品牌跑马灯：CSBLACKBOOKHUB 横向无限循环，文字上透明下白的竖向渐变 */
.brand-marquee {
  display: flex;
  overflow: hidden;
  user-select: none;
}
.brand-marquee-track {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  white-space: nowrap;
  animation: brand-marquee-scroll 24s linear infinite;
}
.brand-marquee-item {
  padding-right: 2.5rem;
  white-space: nowrap;
  /* 字号与“欢迎来到 CS-BlackBook-Hub”标题保持一致（clamp 响应式） */
  font-size: clamp(2.75rem, 8vw, 6rem);
  font-weight: 800;
  line-height: 1.08;
  letter-spacing: -0.02em;
  /* 上透明下主题色：背景渐变裁切到文字上 */
  background: linear-gradient(to bottom, rgb(var(--text-primary) / 0) 0%, rgb(var(--text-primary)) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}
@keyframes brand-marquee-scroll {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}

/* 白天模式：提亮工具卡片的 sprite 背景，避免暗色截图在浅色主题下压暗整卡 */
[data-theme='light'] .ws-sprite { filter: brightness(0.6); }
[data-theme='light'] .mtr-sprite { filter: brightness(0.75); }
[data-theme='light'] .socket-sprite { filter: brightness(0.75); }
[data-theme='light'] .cisco-sprite { filter: brightness(0.6); }
[data-theme='light'] .group:hover .ws-sprite { filter: brightness(0.8); }
[data-theme='light'] .group:hover .mtr-sprite { filter: brightness(0.9); }
[data-theme='light'] .group:hover .socket-sprite { filter: brightness(0.9); }
[data-theme='light'] .group:hover .cisco-sprite { filter: brightness(0.8); }
</style>
