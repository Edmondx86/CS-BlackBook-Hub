<script setup>
// 实验 / 练习的阅读区 + 引导栏（Wireshark 实验与 Socket 练习共用）。
//
// 为什么单独抽一个组件：LabDetailView 已经有 700+ 行，而且两类练习的阅读区诉求相同 ——
// 「一份能读得下去的指南 + 随时知道做到哪一步」。
//
// 这里做四件事：
//   1. 渲染指南正文（沿用全局的 markdown 渲染器，样式与知识卡片一致）
//   2. 把「实现步骤 / 实验步骤」解析成可勾选的清单，进度存 localStorage —— 下次进来知道做到哪了
//   3. 右侧常驻：进度、本页目录（滚动高亮）、过滤器速查（若指南里有，点一下即复制）
//   4. 底部：上一个 / 下一个实验（按章节页的顺序：先 Wireshark 再 Socket）
//
// 解析规则和 mock_data.py 里指南的标题结构是配套的，见该文件 GUIDES 的写法。
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
// 解析指南：拆出目录、步骤清单、过滤器速查
// ---------------------------------------------------------------------------
// 两类内容的步骤标题不同：Wireshark 实验用「实验步骤」，Socket 练习用「实现步骤」。
const FILTER_SECTION = '过滤器速查'
const stepsSectionTitle = computed(() =>
  props.lab.guide.includes('## 实现步骤') ? '实现步骤' : '实验步骤',
)

// 侧栏是纯文本渲染（不走 markdown），所以要自己把记号清掉，
// 否则清单里会露出 <http://…>、[文本](url)、`代码` 这些东西。
function stripMd(text) {
  return text
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1') // [文本](url) -> 文本
    .replace(/<([^>]+)>/g, '$1') // <url> -> url
    .replace(/[*`]/g, '')
    .trim()
}

// 清单标签：优先用步骤开头的 **加粗短语**（写指南时就按这个约定写）；
// 没有加粗就退而取第一个分句并限长，避免整行挤进侧栏。
function stepLabel(text) {
  const bold = text.match(/^\*\*(.+?)\*\*/)
  if (bold) return stripMd(bold[1])
  const clause = stripMd(text.split(/[，。：；（(]/)[0])
  return clause.length > 16 ? `${clause.slice(0, 16)}…` : clause
}

const parsed = computed(() => {
  const sections = []
  const steps = []
  const filters = []
  let current = ''

  for (const line of props.lab.guide.split('\n')) {
    const heading = line.match(/^##\s+(.+?)\s*$/)
    if (heading) {
      current = heading[1]
      sections.push({ title: current, index: sections.length })
      continue
    }

    if (current === stepsSectionTitle.value) {
      const item = line.match(/^\d+\.\s+(.+)$/)
      if (item) {
        steps.push({ label: stepLabel(item[1]), full: stripMd(item[1]) })
      }
    }

    if (current === FILTER_SECTION) {
      const row = line.match(/^\|\s*`([^`]+)`\s*\|(.*)\|\s*$/)
      if (row) filters.push({ filter: row[1].trim(), desc: row[2].trim() })
    }
  }

  return { sections, steps, filters }
})

const guideHtml = computed(() => md.render(props.lab.guide))

// ---------------------------------------------------------------------------
// 步骤进度（按实验 id 分别存）
// ---------------------------------------------------------------------------
const storageKey = computed(() => `labSteps:${props.lab.id}`)
const done = ref([])
const doneSet = computed(() => new Set(done.value))
const percent = computed(() =>
  parsed.value.steps.length ? Math.round((done.value.length / parsed.value.steps.length) * 100) : 0,
)
const allDone = computed(() => parsed.value.steps.length > 0 && done.value.length === parsed.value.steps.length)

watch(
  storageKey,
  (key) => {
    try {
      const raw = JSON.parse(localStorage.getItem(key) ?? '[]')
      done.value = Array.isArray(raw) ? raw.filter((i) => Number.isInteger(i)) : []
    } catch {
      done.value = []
    }
  },
  { immediate: true },
)

function toggleStep(index) {
  const next = new Set(done.value)
  next.has(index) ? next.delete(index) : next.add(index)
  done.value = [...next].sort((a, b) => a - b)
  localStorage.setItem(storageKey.value, JSON.stringify(done.value))
}

function resetSteps() {
  done.value = []
  localStorage.removeItem(storageKey.value)
}

// ---------------------------------------------------------------------------
// 本页目录 + 滚动高亮
// ---------------------------------------------------------------------------
const articleEl = ref(null)
const activeSection = ref(0)
let scrollHost = null

function headings() {
  return articleEl.value ? [...articleEl.value.querySelectorAll('h2')] : []
}

function syncActive() {
  const list = headings()
  if (!list.length) return
  const base = articleEl.value.getBoundingClientRect().top
  let index = 0
  list.forEach((h, i) => {
    if (h.getBoundingClientRect().top - base <= 90) index = i
  })
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
  scrollHost?.addEventListener('scroll', syncActive, { passive: true })
  syncActive()
})

onBeforeUnmount(() => {
  scrollHost?.removeEventListener('scroll', syncActive)
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
          class="inline-flex max-w-[46%] items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition"
          :class="
            allDone
              ? 'border-brand bg-brand/10 text-brand hover:bg-brand/20'
              : 'border-line-strong text-secondary hover:bg-elevated hover:text-primary'
          "
        >
          <span class="truncate">{{ nextLab.title }}</span>
          <span aria-hidden="true">→</span>
        </RouterLink>
        <span v-else></span>
      </nav>

      <p v-if="allDone" class="mt-4 rounded-lg bg-brand/10 px-4 py-3 text-center text-sm text-brand">
        这一步清单都打勾了 —— 记得把「{{ isWireshark ? '要交付什么' : '判题会怎么检查' }}」里的要求过一遍，再进下一个。
      </p>

      <!-- 署名：实验原作者明确要求，若在网站上发布这些实验需注明来源与版权 -->
      <p v-if="isWireshark" class="mt-8 border-t border-line pt-4 text-xs leading-relaxed text-faint">
        本页指南由本站整理改编；实验设计与「官方实验文档」来自
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
        <!-- 步骤进度 -->
        <section v-if="parsed.steps.length" class="rounded-xl border border-line bg-card p-4">
          <div class="flex items-center justify-between">
            <h3 class="text-xs font-semibold uppercase tracking-widest text-brand">
              {{ isWireshark ? '实验进度' : '练习进度' }}
            </h3>
            <button
              v-if="done.length"
              type="button"
              class="text-[11px] text-faint transition hover:text-muted"
              @click="resetSteps"
            >
              重置
            </button>
          </div>

          <div class="mt-2 flex items-center gap-2">
            <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-elevated">
              <div class="h-full rounded-full bg-brand transition-all" :style="{ width: `${percent}%` }"></div>
            </div>
            <span class="shrink-0 text-[11px] tabular-nums text-muted">{{ done.length }}/{{ parsed.steps.length }}</span>
          </div>

          <ul class="mt-3 space-y-1.5">
            <li v-for="(step, i) in parsed.steps" :key="i">
              <label class="flex cursor-pointer items-start gap-2 text-xs leading-snug">
                <input
                  type="checkbox"
                  class="mt-0.5 h-3.5 w-3.5 shrink-0 accent-[rgb(var(--brand))]"
                  :checked="doneSet.has(i)"
                  @change="toggleStep(i)"
                />
                <span :class="doneSet.has(i) ? 'text-faint line-through' : 'text-tertiary'" :title="step.full">
                  {{ step.label }}
                </span>
              </label>
            </li>
          </ul>
        </section>

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
