<script setup>
/**
 * LabDetailView.vue —— Lab 详情页（左右分栏 · 暗色开发者 UI）
 *
 * 依赖安装：npm i markdown-it highlight.js
 * 路由：自动读取 route.params.chapterId / route.params.labId（也可通过 props.labId 显式传入）
 *
 * 后端契约（与 backend/app/api/labs.py 对齐）：
 *   GET  /api/v1/chapters/{chapter_id}/labs/{lab_id}      -> Lab（含 guide 全文 / starter_code / document_path / test_cases）
 *   POST /api/v1/chapters/{chapter_id}/labs/{lab_id}/run  -> 返回 JSON 判题结果（见 runBackendTests）
 */
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import hljs from '../highlight'
import ChapterNav from './ChapterNav.vue'
import LabGuide from './LabGuide.vue'
import { useChapter } from '../composables/useChapter'
import PdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

// PDF 预览器按需加载：vue-pdf-embed + pdfjs-dist 合计约 1 MB，而只有带作业文档（PDF）的
// Lab 才会用到，所以丢进独立 chunk，真正渲染 PDF 时才下载。
// worker 用 ?url 导入，只产出一个静态资源文件，不会把 pdfjs 的代码并入本 chunk。
const VuePdfEmbed = defineAsyncComponent(async () => {
  const mod = await import('vue-pdf-embed/dist/index.essential.mjs')
  // 手动配置 PDF.js worker：默认全量包用 blob worker，在 Vite 下常加载失败导致 PDF 不渲染；
  // 改用 essential 构建 + ?url 导入 worker 更稳定。
  mod.GlobalWorkerOptions.workerSrc = PdfWorker
  return mod.default
})

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
const props = defineProps({
  /** 实验室 id；不传时回退到路由参数 labId */
  labId: { type: String, default: '' },
})

// ---------------------------------------------------------------------------
// 常量
// ---------------------------------------------------------------------------
// 后端地址可通过 .env 的 VITE_API_BASE 覆盖，默认同源。
const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const DEFAULT_CODE =
  '# 初始代码模板\n# Socket 练习请在此编写并点击“运行测试”；Wireshark 实验以左侧指南为准。\n'

// ---------------------------------------------------------------------------
// 状态
// ---------------------------------------------------------------------------
const route = useRoute()
const lab = ref(null)
const loading = ref(true)
const error = ref('')
const code = ref(DEFAULT_CODE)
const starterCode = ref(DEFAULT_CODE)
const running = ref(false)
const logs = ref([])
const terminalRef = ref(null)
const editorEl = ref(null)
const highlightEl = ref(null)
let abortController = null

// 分栏拖拽调整大小
const leftRatio = ref(0.6)   // 左栏（指南）占整体宽度比例
const editorRatio = ref(0.6) // 编辑器占右栏高度比例
const mainEl = ref(null)     // 左右分栏容器（水平拖拽基准）
const rightEl = ref(null)    // 右栏容器（垂直拖拽基准）
let dragKind = null          // 'h' | 'v'

const labId = computed(() => props.labId || route.params.labId)
const chapterId = computed(() => route.params.chapterId)

// 左侧“本章导航”要列出本章所有实验，需要章节概览；与卡片页共用同一份缓存（见 useChapter）
const chapter = useChapter(chapterId)

// ---------------------------------------------------------------------------
// 派生数据
// ---------------------------------------------------------------------------
const typeLabel = computed(() =>
  lab.value?.type === 'wireshark' ? 'Wireshark 实验' : 'Socket 练习',
)
const isWireshark = computed(() => lab.value?.type === 'wireshark')

// 作业文档（PDF）的展开状态。
// Socket 练习照旧直接展开；Wireshark 实验默认收起 —— 这些 PDF 每份 2 MB 上下、
// 7~8 页，一进来就自动下载并渲染，既慢又把上面那份指南彻底盖住。
const showPdf = ref(false)
watch(isWireshark, (value) => (showPdf.value = !value), { immediate: true })

const langLabel = computed(
  () => ({ python: 'Python', c: 'C', java: 'Java' })[lab.value?.language] ?? 'text',
)

// 编辑器实时高亮：用 highlight.js 把 code 转成带颜色的 HTML，铺在透明 textarea 之下。
// 语言取 Lab 的 language 字段（python / c / java）；未识别时退回纯文本转义。
const hljsLanguage = computed(() => {
  const lang = lab.value?.language ?? ''
  return hljs.getLanguage(lang) ? lang : ''
})
const highlightedCode = computed(() => {
  const src = code.value
  try {
    const value = hljsLanguage.value
      ? hljs.highlight(src, { language: hljsLanguage.value, ignoreIllegals: true }).value
      : escapeHtml(src)
    // 末尾补一个换行，保证高亮层与 textarea 的尾行对齐。
    return value + '\n'
  } catch {
    return escapeHtml(src) + '\n'
  }
})

const codeAttachment = computed(() => lab.value?.attachments?.find((a) => a.kind === 'code') ?? null)
const editorFileName = computed(() => codeAttachment.value?.name ?? 'main.py')
const documentUrl = computed(() => lab.value?.document_path ?? '')
const documentName = computed(() => (lab.value?.document_path ?? '').split('/').pop() || '作业要求文档.pdf')
const answerCode = computed(() => lab.value?.reference_code ?? '')
const referenceServerCode = computed(() => lab.value?.reference_server_code ?? '')
const hints = computed(() => lab.value?.hints ?? [])
const hintLevel = ref(0)
const showAnswer = ref(false)
const showServer = ref(false)
const copied = ref(false)
const copiedServer = ref(false)
const pdfError = ref('')

function onPdfError(e) {
  console.error('[VuePdfEmbed] 加载/渲染失败:', e)
  pdfError.value = '文档加载失败，请检查 PDF 文件或稍后重试。'
}

// ---------------------------------------------------------------------------
// 数据加载
// ---------------------------------------------------------------------------
async function fetchLab() {
  abortController?.abort()
  abortController = new AbortController()
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`${API_BASE}/api/v1/chapters/${chapterId.value}/labs/${labId.value}`, {
      signal: abortController.signal,
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    lab.value = await res.json()
    loadStarterCode()
  } catch (e) {
    if (e.name !== 'AbortError') error.value = `加载失败：${e.message}`
  } finally {
    loading.value = false
  }
}

function loadStarterCode() {
  starterCode.value = lab.value?.starter_code?.trim() || DEFAULT_CODE
  code.value = starterCode.value
  hintLevel.value = 0
  showAnswer.value = false
  showServer.value = false
}

function escapeHtml(str) {
  return str.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c])
}

/** 把 textarea 的滚动同步到高亮层，保证两者始终对齐。 */
function syncScroll() {
  const ta = editorEl.value
  const pre = highlightEl.value
  if (ta && pre) {
    pre.scrollTop = ta.scrollTop
    pre.scrollLeft = ta.scrollLeft
  }
}

// ---------------------------------------------------------------------------
// 编辑器 Tab 键缩进：Tab 插入缩进，Shift+Tab 反缩进（阻止焦点跳走）。
// ---------------------------------------------------------------------------
const TAB_INDENT = '    ' // 4 空格缩进

function onEditorKeydown(e) {
  if (e.key !== 'Tab') return
  e.preventDefault()
  const ta = editorEl.value
  if (!ta) return
  const start = ta.selectionStart
  const end = ta.selectionEnd

  if (e.shiftKey) {
    outdentLines(start, end)
  } else if (start === end) {
    // 光标处插入 4 空格
    code.value = code.value.slice(0, start) + TAB_INDENT + code.value.slice(end)
    setCursor(start + TAB_INDENT.length)
  } else {
    indentLines(start, end)
  }
}

/** 选中区（或光标）所在行首的下标。 */
function lineStartIndex(text, pos) {
  return text.lastIndexOf('\n', pos - 1) + 1
}

function indentLines(start, end) {
  const text = code.value
  const ls = lineStartIndex(text, start)
  const nl = text.indexOf('\n', end - 1)
  const blockEnd = nl === -1 ? text.length : nl
  const block = text.slice(ls, blockEnd)
  const indented = block.split('\n').map((l) => TAB_INDENT + l).join('\n')
  code.value = text.slice(0, ls) + indented + text.slice(blockEnd)
  setCursor(ls, ls + indented.length)
}

function outdentLines(start, end) {
  const text = code.value
  const ls = lineStartIndex(text, start)
  const nl = text.indexOf('\n', end - 1)
  const blockEnd = nl === -1 ? text.length : nl
  const block = text.slice(ls, blockEnd)
  const outdented = block.split('\n').map((l) => l.replace(/^(?: {1,4}|\t)/, '')).join('\n')
  code.value = text.slice(0, ls) + outdented + text.slice(blockEnd)
  setCursor(ls, ls + outdented.length)
}

function setCursor(start, end = start) {
  nextTick(() => {
    const ta = editorEl.value
    if (ta) {
      ta.selectionStart = start
      ta.selectionEnd = end
    }
  })
}

// ---------------------------------------------------------------------------
// 分栏拖拽（水平：指南 ↔ 编辑器；垂直：编辑器 ↔ 终端）
// ---------------------------------------------------------------------------
function startDrag(kind, e) {
  dragKind = kind
  document.body.style.userSelect = 'none'
  document.body.style.cursor = kind === 'h' ? 'col-resize' : 'row-resize'
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', endDrag)
}

function onDrag(e) {
  if (dragKind === 'h' && mainEl.value) {
    const rect = mainEl.value.getBoundingClientRect()
    const ratio = (e.clientX - rect.left) / rect.width
    leftRatio.value = Math.min(0.8, Math.max(0.2, ratio))
  } else if (dragKind === 'v' && rightEl.value) {
    const rect = rightEl.value.getBoundingClientRect()
    const ratio = (e.clientY - rect.top) / rect.height
    editorRatio.value = Math.min(0.85, Math.max(0.15, ratio))
  }
}

function endDrag() {
  dragKind = null
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', endDrag)
}

// ---------------------------------------------------------------------------
// Terminal 日志流
// ---------------------------------------------------------------------------
const LOG_COLORS = {
  cmd: 'text-tertiary',
  info: 'text-muted',
  ok: 'text-brand',
  err: 'text-danger',
  warn: 'text-warning',
}

function pushLog(text, level = 'info') {
  logs.value.push({
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    text,
    level,
  })
  nextTick(() => {
    const el = terminalRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function clearLogs() {
  logs.value = []
}

function logColor(level) {
  return LOG_COLORS[level] ?? LOG_COLORS.info
}

// ---------------------------------------------------------------------------
// 运行测试
// ---------------------------------------------------------------------------
async function runTests() {
  if (running.value || !lab.value) return
  if (!code.value.trim()) {
    pushLog('请先编写代码，再运行测试', 'warn')
    return
  }
  running.value = true
  clearLogs()
  pushLog(`$ 运行测试：${lab.value.id}`, 'cmd')
  try {
    await runBackendTests()
  } catch (e) {
    pushLog(`判题失败：${e.message}`, 'err')
  } finally {
    running.value = false
  }
}

/** 调用 POST /api/v1/chapters/{chapter_id}/labs/{lab_id}/run，解析 JSON 判题结果。 */
async function runBackendTests() {
  const res = await fetch(`${API_BASE}/api/v1/chapters/${chapterId.value}/labs/${labId.value}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code: code.value }),
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const data = await res.json()
      if (typeof data.detail === 'string') detail = data.detail
    } catch {
      /* 非 JSON 响应 */
    }
    throw new Error(detail)
  }
  const result = await res.json()
  renderResult(result)
}

/** 把后端判题结果渲染到终端：实时日志 + 逐条 check + 结论。 */
function renderResult(result) {
  for (const line of result.logs ?? []) pushLog(line, 'info')
  for (const c of result.checks ?? []) {
    pushLog(`${c.passed ? '✓' : '✗'} ${c.name} — ${c.detail}`, c.passed ? 'ok' : 'err')
  }
  pushLog(result.summary ?? (result.passed ? '通过' : '未通过'), result.passed ? 'ok' : 'err')
}

function refreshCode() {
  code.value = starterCode.value
  hintLevel.value = 0
  showAnswer.value = false
}

function nextHint() {
  if (hintLevel.value < hints.value.length) hintLevel.value++
}

function openAnswer() {
  showAnswer.value = true
}

function closeAnswer() {
  showAnswer.value = false
}

async function copyAnswer() {
  try {
    await navigator.clipboard.writeText(answerCode.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    /* 剪贴板不可用时忽略 */
  }
}

function openServer() {
  showServer.value = true
}

function closeServer() {
  showServer.value = false
}

async function copyServer() {
  try {
    await navigator.clipboard.writeText(referenceServerCode.value)
    copiedServer.value = true
    setTimeout(() => (copiedServer.value = false), 2000)
  } catch {
    /* 剪贴板不可用时忽略 */
  }
}

// ---------------------------------------------------------------------------
// 生命周期
// ---------------------------------------------------------------------------
watch(
  [labId, chapterId],
  () => {
    if (!labId.value || !chapterId.value) {
      loading.value = false
      error.value = '未提供 chapter_id / lab_id 参数'
      return
    }
    fetchLab()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  abortController?.abort()
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', endDrag)
})
</script>

<template>
  <div class="flex h-full w-full overflow-hidden text-primary antialiased">
    <!-- 最左侧：本章位置导航（拿到 lab 后再显示，避免加载态时白占一块） -->
    <ChapterNav
      v-if="lab && !error"
      :chapter-id="chapterId"
      :chapter="chapter"
      current-kind="lab"
      :current-id="labId"
      class="hidden lg:flex"
    />

    <!-- 分栏容器：只包住指南 / 分隔条 / 编辑器，拖拽比例才不会被左侧导航带偏 -->
    <div ref="mainEl" class="flex min-w-0 flex-1 overflow-hidden">
      <!-- 加载中 -->
      <div v-if="loading" class="flex w-full items-center justify-center gap-3 text-muted">
        <span class="h-4 w-4 animate-spin rounded-full border-2 border-line-strong border-t-theme"></span>
        正在加载 Lab…
      </div>

      <!-- 加载失败 -->
      <div v-else-if="error" class="m-auto flex flex-col items-center gap-4 text-center">
        <div class="text-4xl">⚠️</div>
        <p class="text-tertiary">{{ error }}</p>
        <button
          class="rounded-lg bg-btn-alt px-4 py-2 text-sm font-medium text-btn-alt-text transition hover:bg-btn-alt-hover"
          @click="fetchLab"
        >
          重试
        </button>
      </div>

      <!-- 主体：左右分栏 -->
      <template v-else-if="lab">
        <!-- 左栏：Markdown 指南（宽度可拖拽调整） -->
        <section class="flex min-w-0 flex-col" :style="{ width: isWireshark ? '100%' : `${leftRatio * 100}%` }">
          <header class="border-b border-line px-6 py-4">
            <div
              class="flex flex-wrap items-center gap-x-3 gap-y-2"
              :class="isWireshark ? 'mx-auto max-w-6xl' : ''"
            >
              <RouterLink
                :to="`/chapters/${chapterId}`"
                class="shrink-0 text-sm text-muted transition hover:text-primary"
              >
                ← 返回章节
              </RouterLink>
              <span
                class="rounded-full px-2.5 py-0.5 text-xs font-medium ring-1"
                :class="
                  lab.type === 'wireshark'
                    ? 'bg-brand/10 text-brand ring-brand/30'
                    : 'bg-theme/10 text-theme-light ring-theme/30'
                "
              >{{ typeLabel }}</span>
              <h1 class="text-lg font-semibold text-primary">{{ lab.title }}</h1>
              <span class="text-xs text-faint">{{ lab.summary }}</span>
            </div>
          </header>

          <div class="flex-1 overflow-y-auto">
            <div :class="isWireshark ? 'mx-auto max-w-6xl px-6 py-6' : 'px-6 py-6'">
              <!-- Wireshark 实验：指南 + 引导栏（步骤进度 / 本页目录 / 过滤器速查 + 前后实验导航） -->
              <LabGuide v-if="isWireshark" variant="wireshark" :lab="lab" :chapter="chapter" />
              <!-- Socket 练习：只放指南，代码编辑器在右栏 -->
              <LabGuide v-else variant="socket" :lab="lab" :chapter="chapter" />

              <!-- 作业要求文档（PDF） -->
              <section v-if="documentUrl" class="mt-10">
                <!-- 未展开时只放一个按钮：这些 PDF 每个 2 MB 上下，
                     不该在打开页面的瞬间就白白下载并渲染 -->
                <button
                  v-if="!showPdf"
                  type="button"
                  class="flex w-full items-center gap-3 rounded-lg border border-line bg-card px-4 py-3 text-left text-sm text-secondary transition hover:bg-elevated hover:text-primary"
                  @click="showPdf = true"
                >
                  <span aria-hidden="true">📄</span>
                  <span class="font-medium">打开官方实验文档</span>
                  <span class="text-xs text-faint">{{ documentName }}</span>
                  <span class="ml-auto text-xs text-faint">点击加载 ↓</span>
                </button>

                <template v-else>
                  <div class="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1">
                    <h2 class="text-sm font-semibold text-secondary">官方实验文档</h2>
                    <span class="text-xs text-faint">{{ documentName }}</span>
                    <a
                      :href="documentUrl"
                      target="_blank"
                      rel="noopener"
                      class="text-xs text-theme-light transition hover:underline"
                    >
                      在新窗口打开 ↗
                    </a>
                    <button
                      v-if="isWireshark"
                      type="button"
                      class="ml-auto text-xs text-faint transition hover:text-muted"
                      @click="showPdf = false"
                    >
                      收起
                    </button>
                  </div>

                  <div class="px-12">
                    <div class="w-full rounded-md bg-white shadow-sm">
                      <VuePdfEmbed
                        :source="documentUrl"
                        @loading-failed="onPdfError"
                        @rendering-failed="onPdfError"
                      />
                    </div>
                  </div>
                </template>

                <p v-if="pdfError" class="mt-3 text-center text-sm text-danger">{{ pdfError }}</p>
              </section>
            </div>
          </div>
        </section>

        <!-- 水平分隔条：拖拽调整指南 / 编辑器宽度（仅 Socket 练习显示） -->
        <div
          v-if="!isWireshark"
          class="w-1.5 shrink-0 cursor-col-resize bg-elevated/70 transition-colors hover:bg-brand/70 active:bg-brand"
          title="拖拽调整宽度"
          @mousedown="startDrag('h', $event)"
        ></div>

        <!-- 右栏：编辑器 + 终端（仅 Socket 练习显示，宽度自适应剩余空间） -->
        <section v-if="!isWireshark" ref="rightEl" class="flex min-w-0 flex-1 flex-col">
          <!-- 代码编辑器（高度可拖拽调整） -->
          <div class="flex min-h-0 flex-col" :style="{ height: `${editorRatio * 100}%` }">
            <div class="flex items-center gap-3 border-b border-line px-4 py-2">
              <div class="flex gap-1.5">
                <span class="h-3 w-3 rounded-full bg-rose-500/80"></span>
                <span class="h-3 w-3 rounded-full bg-amber-500/80"></span>
                <span class="h-3 w-3 rounded-full bg-emerald-500/80"></span>
              </div>
              <span class="flex items-center gap-1.5 font-mono text-xs text-muted">
                <span class="text-brand" aria-hidden="true">&lt;/&gt;</span>
                代码
              </span>
              <span class="rounded bg-elevated px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted">
                {{ langLabel }}
              </span>
              <div class="ml-auto flex items-center gap-3">
                <button
                  v-if="hints.length"
                  class="text-xs text-faint transition hover:text-secondary disabled:cursor-not-allowed disabled:opacity-40"
                  :disabled="hintLevel >= hints.length"
                  @click="nextHint"
                >
                  提示（{{ hintLevel }}/{{ hints.length }}）
                </button>
                <button
                  class="text-xs text-faint transition hover:text-secondary"
                  @click="openAnswer"
                >
                  参考答案
                </button>
                <button
                  v-if="referenceServerCode"
                  class="text-xs text-faint transition hover:text-secondary"
                  @click="openServer"
                >
                  服务器端
                </button>
              </div>
            </div>
            <!-- 分级提示面板：点击“提示”逐级揭示，最后才建议看参考答案 -->
            <div
              v-if="hintLevel > 0"
              class="shrink-0 border-b border-amber-500/20 bg-amber-500/5 px-4 py-3"
            >
              <div class="mb-1 flex items-center justify-between">
                <span class="text-xs font-semibold uppercase tracking-wide text-warning">
                  💡 提示 {{ hintLevel }}/{{ hints.length }}
                </span>
              </div>
              <ul class="space-y-1.5">
                <li
                  v-for="(h, i) in hints.slice(0, hintLevel)"
                  :key="i"
                  class="text-sm leading-6 text-tertiary"
                >
                  <span class="mr-1 text-warning/[var(--alpha-soft)]">{{ i + 1 }}.</span>{{ h }}
                </li>
              </ul>
            </div>
            <div class="code-editor relative flex-1 overflow-hidden bg-card font-mono text-sm leading-6">
              <!-- 高亮层（位于透明 textarea 之下，显示带颜色的代码） -->
              <pre
                ref="highlightEl"
                aria-hidden="true"
                class="pointer-events-none absolute inset-0 m-0 overflow-hidden whitespace-pre p-4 text-secondary"
                v-html="highlightedCode"
              ></pre>
              <!-- 输入层：文字透明只留光标，透过它看到下面的高亮文字 -->
              <textarea
                ref="editorEl"
                v-model="code"
                wrap="off"
                spellcheck="false"
                placeholder="# 在这里编写代码…"
                class="absolute inset-0 resize-none overflow-auto whitespace-pre bg-transparent p-4 font-mono text-sm leading-6 text-transparent caret-brand outline-none placeholder:text-faint"
                @scroll="syncScroll"
                @keydown="onEditorKeydown"
              ></textarea>
            </div>
          </div>

          <!-- 垂直分隔条：拖拽调整编辑器 / 终端高度 -->
          <div
            class="h-1.5 shrink-0 cursor-row-resize bg-elevated/70 transition-colors hover:bg-brand/70 active:bg-brand"
            title="拖拽调整高度"
            @mousedown="startDrag('v', $event)"
          ></div>

          <!-- 终端日志（高度自适应剩余空间） -->
          <div class="flex min-h-0 flex-1 flex-col">
            <div class="flex items-center gap-2 border-b border-line px-4 py-2">
              <span class="h-2 w-2 rounded-full bg-brand"></span>
              <span class="text-xs font-medium text-muted">Terminal</span>
              <div class="ml-auto flex items-center gap-2">
                <button
                  class="rounded-md px-2 py-1 text-xs text-muted transition hover:bg-elevated"
                  @click="refreshCode"
                >
                  重置
                </button>
                <button
                  :disabled="running"
                  class="inline-flex items-center gap-1.5 rounded-md bg-btn-alt px-3 py-1 text-xs font-medium text-btn-alt-text transition hover:bg-btn-alt-hover disabled:cursor-not-allowed disabled:opacity-50"
                  @click="runTests"
                >
                  <span
                    v-if="running"
                    class="h-3 w-3 animate-spin rounded-full border border-white border-t-transparent"
                  ></span>
                  {{ running ? '运行中…' : '运行测试' }}
                </button>
              </div>
            </div>
            <div
              ref="terminalRef"
              class="flex-1 overflow-y-auto bg-card p-3 font-mono text-xs leading-5"
            >
              <p v-if="!logs.length" class="text-faint">// 等待运行，点击“运行测试”查看输出…</p>
              <p v-for="(l, i) in logs" :key="i" :class="logColor(l.level)">
                <span class="select-none text-faint">[{{ l.time }}]</span> {{ l.text }}
              </p>
              <span v-if="running" class="animate-pulse text-muted">▋</span>
            </div>
          </div>
        </section>
      </template>

        <!-- 参考答案弹窗 -->
      <div
        v-if="showAnswer"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"
        @click.self="closeAnswer"
      >
        <div class="flex h-full max-h-[80vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-line bg-card">
          <div class="flex items-center justify-between border-b border-line px-4 py-3">
            <span class="text-sm font-semibold text-primary">参考答案 — {{ editorFileName }}</span>
            <div class="flex items-center gap-2">
              <button
                class="rounded-md px-2 py-1 text-xs text-muted transition hover:bg-elevated"
                @click="copyAnswer"
              >
                {{ copied ? '已复制' : '复制' }}
              </button>
              <button
                class="rounded-md px-2 py-1 text-xs text-muted transition hover:bg-elevated"
                @click="closeAnswer"
              >
                关闭
              </button>
            </div>
          </div>
          <pre
            v-if="answerCode"
            class="flex-1 overflow-auto bg-page p-4 font-mono text-sm leading-6 text-secondary"
          >{{ answerCode }}</pre>
          <p v-else class="grid flex-1 place-items-center text-sm text-faint">暂无参考答案</p>
        </div>
      </div>

      <!-- 参考服务器弹窗（学生写客户端时，后端判题对端的服务器实现） -->
      <div
        v-if="showServer"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"
        @click.self="closeServer"
      >
        <div class="flex h-full max-h-[80vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-line bg-card">
          <div class="flex items-center justify-between border-b border-line px-4 py-3">
            <span class="text-sm font-semibold text-primary">参考服务器（后端判题对端）</span>
            <div class="flex items-center gap-2">
              <button
                class="rounded-md px-2 py-1 text-xs text-muted transition hover:bg-elevated"
                @click="copyServer"
              >
                {{ copiedServer ? '已复制' : '复制' }}
              </button>
              <button
                class="rounded-md px-2 py-1 text-xs text-muted transition hover:bg-elevated"
                @click="closeServer"
              >
                关闭
              </button>
            </div>
          </div>
          <pre
            v-if="referenceServerCode"
            class="flex-1 overflow-auto bg-page p-4 font-mono text-sm leading-6 text-secondary"
          >{{ referenceServerCode }}</pre>
          <p v-else class="grid flex-1 place-items-center text-sm text-faint">暂无参考服务器代码</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/*
 * 编辑器注释配色：注释（# / // 等）用品牌绿着色，一眼可辨。
 * 高亮层是 v-html 注入的着色节点，Vue scoped 样式打不到，故此处用全局样式，
 * 通过 .code-editor 容器类限定作用范围，不影响左侧 Markdown 指南里的代码块。
 */
.code-editor .hljs-comment,
.code-editor .hljs-quote {
  color: rgb(var(--brand));
}
.code-editor .hljs-meta {
  color: rgb(var(--brand-light));
}
</style>
