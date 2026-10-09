<script setup>
// 实验 / 练习的阅读区 + 引导栏（Wireshark 实验与 Socket 练习共用）。
//
// 为什么单独抽一个组件：LabDetailView 已经有 700+ 行，而且两类练习的阅读区诉求相同 ——
// “一份能读得下去的指南 + 随时知道做到哪一步”。
//
// 这里做三件事：
//   1. 渲染指南正文（沿用全局的 markdown 渲染器，样式与知识卡片一致）
//   2. 右侧常驻：本页目录（滚动高亮）、过滤器速查（若指南里有，点一下即复制）
//   3. 底部：上一个 / 下一个实验（按章节页的顺序：先 Wireshark 再 Socket）
//
// 解析规则和 mock_data.py 里指南的标题结构是配套的，见该文件 GUIDES 的写法。
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { createMarkdown } from '../markdown'

const props = defineProps({
  lab: { type: Object, required: true },
  /** 章节概览（useChapter 的返回值），用于算上一个 / 下一个实验 */
  chapter: { type: Object, default: null },
  /** 'wireshark' | 'socket'：影响部分文案与是否显示版权署名 */
  variant: { type: String, default: 'wireshark' },
})

const md = createMarkdown()

const isWireshark = computed(() => props.variant !== 'socket')

// ---------------------------------------------------------------------------
// 解析指南：拆出本页目录与过滤器速查
// ---------------------------------------------------------------------------
const FILTER_SECTION = '过滤器速查'

const parsed = computed(() => {
  const sections = []
  const filters = []
  let current = ''

  for (const line of props.lab.guide.split('\n')) {
    const heading = line.match(/^##\s+(.+?)\s*$/)
    if (heading) {
      current = heading[1]
      sections.push({ title: current, index: sections.length })
      continue
    }

    if (current === FILTER_SECTION) {
      const row = line.match(/^\|\s*`([^`]+)`\s*\|(.*)\|\s*$/)
      if (row) filters.push({ filter: row[1].trim(), desc: row[2].trim() })
    }
  }

  return { sections, filters }
})

const guideHtml = computed(() => md.render(props.lab.guide))

// ---------------------------------------------------------------------------
// 本页目录 + 滚动高亮
// ---------------------------------------------------------------------------
const articleEl = ref(null)
const activeSection = ref(0)
let scrollHost = null
let resizeObserver = null

// 认为“标题滚到视口顶部 90px 以内”就算进入了这一节
const VIEWPORT_OFFSET = 90

function headings() {
  return articleEl.value ? [...articleEl.value.querySelectorAll('h2')] : []
}

// 基准点必须是**滚动容器（视口）的顶边**，不能用正文容器的顶边：
// 正文和标题是一起滚的，两者之差恒定不变，拿它比较的话 activeSection 永远不会更新
// （之前的 bug —— 目录只高亮第一项）。
function syncActive() {
  const list = headings()
  if (!list.length) return
  const viewportTop = scrollHost ? scrollHost.getBoundingClientRect().top : 0
  const threshold = viewportTop + VIEWPORT_OFFSET
  let index = 0
  list.forEach((h, i) => {
    if (h.getBoundingClientRect().top <= threshold) index = i
  })
  // 滚到底时直接标最后一项：最后一节内容通常不够高，标题到不了视口顶部，
  // 不加这一条的话末尾几项永远高亮不到。
  if (scrollHost && scrollHost.scrollTop + scrollHost.clientHeight >= scrollHost.scrollHeight - 4) {
    index = list.length - 1
  }
  activeSection.value = index
}

function goSection(index) {
  const target = headings()[index]
  if (!target) return
  activeSection.value = index
  target.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(() => {
  scrollHost = articleEl.value?.closest('.overflow-y-auto') ?? null
  if (scrollHost) {
    scrollHost.addEventListener('scroll', syncActive, { passive: true })
  } else {
    // 布局变了找不到滚动容器时退回窗口滚动，至少别让高亮彻底失效
    window.addEventListener('scroll', syncActive, { passive: true })
  }
  // 宽度变化（拖拽分栏、窗口缩放）会改变标题的折行位置，高亮需要跟着重算
  if (typeof ResizeObserver !== 'undefined' && articleEl.value) {
    resizeObserver = new ResizeObserver(() => syncActive())
    resizeObserver.observe(articleEl.value)
  }
  syncActive()
})

onBeforeUnmount(() => {
  scrollHost?.removeEventListener('scroll', syncActive)
  window.removeEventListener('scroll', syncActive)
  resizeObserver?.disconnect()
})

// ---------------------------------------------------------------------------
// 过滤器一键复制
// ---------------------------------------------------------------------------
const copied = ref('')
let copyTimer = null

async function copyFilter(text) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    return // 非安全上下文（http）下剪贴板不可用，静默跳过
  }
  copied.value = text
  clearTimeout(copyTimer)
  copyTimer = setTimeout(() => (copied.value = ''), 1500)
}

// ---------------------------------------------------------------------------
// 上一个 / 下一个实验（按章节页的顺序：先 Wireshark 再 Socket）
// ---------------------------------------------------------------------------
const siblings = computed(() => [
  ...(props.chapter?.wireshark_labs ?? []),
  ...(props.chapter?.socket_exercises ?? []),
])
const position = computed(() => siblings.value.findIndex((l) => l.id === props.lab.id))
const prevLab = computed(() => (position.value > 0 ? siblings.value[position.value - 1] : null))
const nextLab = computed(() =>
  position.value >= 0 && position.value < siblings.value.length - 1 ? siblings.value[position.value + 1] : null,
)
</script>

<template>
  <div class="flex gap-8">
    <!-- 正文 -->
    <div class="min-w-0 flex-1">
      <article ref="articleEl" class="markdown-body" v-html="guideHtml"></article>

      <!-- 底部：上一个 / 下一个实验 -->
      <nav class="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-6">
        <RouterLink
          v-if="prevLab"
          :to="`/chapters/${lab.chapter_id}/labs/${prevLab.id}`"
          class="inline-flex max-w-[46%] items-center gap-2 rounded-lg border border-line-strong px-4 py-2 text-sm font-medium text-secondary transition hover:bg-elevated hover:text-primary"
        >
          <span aria-hidden="true">←</span>
          <span class="truncate">{{ prevLab.title }}</span>
        </RouterLink>
        <span v-else></span>

        <RouterLink
          v-if="nextLab"
          :to="`/chapters/${lab.chapter_id}/labs/${nextLab.id}`"
          class="inline-flex max-w-[46%] items-center gap-2 rounded-lg border border-line-strong px-4 py-2 text-sm font-medium text-secondary transition hover:bg-elevated hover:text-primary"
        >
          <span class="truncate">{{ nextLab.title }}</span>
          <span aria-hidden="true">→</span>
        </RouterLink>
        <span v-else></span>
      </nav>

      <!-- 署名：实验原作者明确要求，若在网站上发布这些实验需注明来源与版权 -->
      <p v-if="isWireshark" class="mt-8 border-t border-line pt-4 text-xs leading-relaxed text-faint">
        本页指南由本站整理改编；实验设计与“官方实验文档”来自
        <a
          href="https://www-net.cs.umass.edu/wireshark-labs/"
          target="_blank"
          rel="noopener"
          class="text-theme-light transition hover:underline"
        >
          Kurose &amp; Ross 的 Wireshark Labs
        </a>
        （© J.F. Kurose, K.W. Ross），配套抓包文件也可在该页下载。
      </p>
    </div>

    <!-- 引导栏 -->
    <aside class="hidden w-64 shrink-0 xl:block">
      <div class="sticky top-6 space-y-4">
        <!-- 本页目录 -->
        <section v-if="parsed.sections.length" class="rounded-xl border border-line bg-card p-4">
          <h3 class="text-xs font-semibold uppercase tracking-widest text-brand">本页目录</h3>
          <ul class="mt-2 space-y-0.5">
            <li v-for="s in parsed.sections" :key="s.index">
              <button
                type="button"
                class="block w-full rounded px-2 py-1 text-left text-xs leading-snug transition"
                :class="
                  activeSection === s.index
                    ? 'bg-brand/10 font-medium text-brand'
                    : 'text-tertiary hover:bg-elevated hover:text-primary'
                "
                @click="goSection(s.index)"
              >
                {{ s.title }}
              </button>
            </li>
          </ul>
        </section>

        <!-- 过滤器速查（指南里有这个章节才显示） -->
        <section v-if="parsed.filters.length" class="rounded-xl border border-line bg-card p-4">
          <h3 class="text-xs font-semibold uppercase tracking-widest text-brand">过滤器速查</h3>
          <p class="mt-1 text-[11px] text-faint">点一下复制，粘到 Wireshark 的显示过滤器栏</p>
          <ul class="mt-2 space-y-1">
            <li v-for="f in parsed.filters" :key="f.filter">
              <button
                type="button"
                class="w-full rounded-md px-2 py-1 text-left font-mono text-[11px] transition"
                :class="copied === f.filter ? 'bg-brand/15 text-brand' : 'bg-elevated text-theme-light hover:bg-elevated/70'"
                :title="f.desc"
                @click="copyFilter(f.filter)"
              >
                {{ copied === f.filter ? '已复制 ✓' : f.filter }}
              </button>
            </li>
          </ul>
        </section>
      </div>
    </aside>
  </div>
</template>
