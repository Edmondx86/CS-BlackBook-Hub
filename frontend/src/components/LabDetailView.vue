<script setup>
/**
 * LabDetailView.vue —— Lab 详情页（左右分栏 · 暗色开发者 UI）
 *
 * 依赖安装：npm i markdown-it highlight.js
 * 路由：自动读取 route.params.chapterId / route.params.labId（也可通过 props.labId 显式传入）
 *
 * 后端契约（与 backend/app/api/labs.py 对齐）：
 *   GET  /api/v1/chapters/{chapter_id}/labs/{lab_id}      -> Lab（含 guide 全文 / starter_code / document_path / test_cases）
 *   POST /api/v1/chapters/{chapter_id}/labs/{lab_id}/run  -> 流式返回测试日志（按行 / NDJSON，见 runBackendTests）
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createMarkdown } from '../markdown'
import VuePdfEmbed, { GlobalWorkerOptions } from 'vue-pdf-embed/dist/index.essential.mjs'
import PdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

// 手动配置 PDF.js worker：默认全量包用 blob worker，在 Vite 下常加载失败导致 PDF 不渲染；
// 改用 essential 构建 + ?url 导入 worker 更稳定。
GlobalWorkerOptions.workerSrc = PdfWorker

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
  '# 初始代码模板\n# Socket 练习请在此编写并点击「运行测试」；Wireshark 实验以左侧指南为准。\n'

// ---------------------------------------------------------------------------
// Markdown 渲染器（markdown-it + highlight.js，见 src/markdown.js）
// ---------------------------------------------------------------------------
// 注意：html:false 会转义指南里的原始 HTML，降低 XSS 风险；
// 若指南可能来自不可信来源，建议再叠加 DOMPurify 做白名单清洗。
const md = createMarkdown()

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
let abortController = null

const labId = computed(() => props.labId || route.params.labId)
const chapterId = computed(() => route.params.chapterId)

// ---------------------------------------------------------------------------
// 派生数据
// ---------------------------------------------------------------------------
const renderedGuide = computed(() => (lab.value ? md.render(lab.value.guide ?? '') : ''))
const typeLabel = computed(() =>
  lab.value?.type === 'wireshark' ? 'Wireshark 实验' : 'Socket 练习',
)
const langLabel = computed(
  () => ({ python: 'Python', c: 'C', java: 'Java' })[lab.value?.language] ?? 'text',
)
const codeAttachment = computed(() => lab.value?.attachments?.find((a) => a.kind === 'code') ?? null)
const editorFileName = computed(() => codeAttachment.value?.name ?? 'main.py')
const documentUrl = computed(() => lab.value?.document_path ?? '')
const documentName = computed(() => (lab.value?.document_path ?? '').split('/').pop() || '作业要求文档.pdf')
const answerCode = computed(() => lab.value?.reference_code ?? '')
const showAnswer = ref(false)
const copied = ref(false)
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
  // 后端已在 Lab.starter_code 内联返回初始代码，直接使用即可，无需二次请求。
  // （之前这里 fetch 附件路径，未命中时走 SPA 回退拿到了 index.html，
  //   正是编辑器里显示一页 HTML 的原因。）
  starterCode.value = lab.value?.starter_code?.trim() || DEFAULT_CODE
  code.value = starterCode.value
}

// ---------------------------------------------------------------------------
// Terminal 日志流
// ---------------------------------------------------------------------------
const LOG_COLORS = {
  cmd: 'text-zinc-300',
  info: 'text-zinc-400',
  ok: 'text-brand',
  err: 'text-rose-400',
  warn: 'text-amber-400',
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

function resetCode() {
  code.value = starterCode.value
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

onBeforeUnmount(() => abortController?.abort())
</script>

<template>
  <div class="flex h-full w-full overflow-hidden bg-zinc-950 text-zinc-100 antialiased">
    <!-- 加载中 -->
    <div v-if="loading" class="flex w-full items-center justify-center gap-3 text-zinc-400">
      <span class="h-4 w-4 animate-spin rounded-full border-2 border-zinc-600 border-t-theme"></span>
      正在加载 Lab…
    </div>

    <!-- 加载失败 -->
    <div v-else-if="error" class="m-auto flex flex-col items-center gap-4 text-center">
      <div class="text-4xl">⚠️</div>
      <p class="text-zinc-300">{{ error }}</p>
      <button
        class="rounded-lg bg-theme-dark px-4 py-2 text-sm font-medium text-white transition hover:bg-theme"
        @click="fetchLab"
      >
        重试
      </button>
    </div>

    <!-- 主体：左右分栏 -->
    <template v-else-if="lab">
      <!-- 左栏 60%：Markdown 指南 -->
      <section class="flex w-3/5 min-w-0 flex-col border-r border-zinc-800">
        <header class="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-zinc-800 px-6 py-4">
          <span
            class="rounded-full px-2.5 py-0.5 text-xs font-medium ring-1"
            :class="
              lab.type === 'wireshark'
                ? 'bg-brand/10 text-brand ring-brand/30'
                : 'bg-theme/10 text-theme-light ring-theme/30'
            "
          >{{ typeLabel }}</span>
          <h1 class="text-lg font-semibold text-white">{{ lab.title }}</h1>
          <span class="text-xs text-zinc-500">{{ lab.summary }}</span>
        </header>

        <div class="flex-1 overflow-y-auto px-6 py-6">
          <article class="markdown-body" v-html="renderedGuide"></article>

          <!-- 作业要求文档（PDF）：像图片一样内嵌，随外层滚动自然展开 -->
          <section v-if="documentUrl" class="mt-10 px-12">
            <div class="w-full rounded-md bg-white shadow-sm">
              <VuePdfEmbed
                :source="documentUrl"
                @loading-failed="onPdfError"
                @rendering-failed="onPdfError"
              />
            </div>

            <p v-if="pdfError" class="mt-3 text-center text-sm text-rose-400">{{ pdfError }}</p>

            <p class="mt-3 text-center text-sm text-zinc-500">
              <a
                :href="documentUrl"
                target="_blank"
                rel="noopener"
                class="text-theme-light transition hover:underline"
              >
                {{ documentName }} ↗
              </a>
            </p>
          </section>
        </div>
      </section>

      <!-- 右栏 40%：编辑器 + 终端 -->
      <section class="flex w-2/5 min-w-0 flex-col">
        <!-- 代码编辑器 -->
        <div class="flex h-3/5 flex-col border-b border-zinc-800">
          <div class="flex items-center gap-3 border-b border-zinc-800 px-4 py-2">
            <div class="flex gap-1.5">
              <span class="h-3 w-3 rounded-full bg-rose-500/80"></span>
              <span class="h-3 w-3 rounded-full bg-amber-500/80"></span>
              <span class="h-3 w-3 rounded-full bg-emerald-500/80"></span>
            </div>
            <span class="font-mono text-xs text-zinc-400">{{ editorFileName }}</span>
            <span class="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-zinc-400">
              {{ langLabel }}
            </span>
            <div class="ml-auto flex items-center gap-3">
              <button
                class="text-xs text-zinc-500 transition hover:text-zinc-200"
                @click="openAnswer"
              >
                参考答案
              </button>
              <button
                class="text-xs text-zinc-500 transition hover:text-zinc-200"
                @click="resetCode"
              >
                重置
              </button>
            </div>
          </div>
          <textarea
            v-model="code"
            spellcheck="false"
            placeholder="# 在这里编写代码…"
            class="flex-1 resize-none bg-zinc-900 p-4 font-mono text-sm leading-6 text-zinc-100 outline-none placeholder:text-zinc-600"
          ></textarea>
        </div>

        <!-- 终端日志 -->
        <div class="flex h-2/5 flex-col">
          <div class="flex items-center gap-2 border-b border-zinc-800 px-4 py-2">
            <span class="h-2 w-2 rounded-full bg-brand"></span>
            <span class="text-xs font-medium text-zinc-400">Terminal</span>
            <div class="ml-auto flex items-center gap-2">
              <button
                class="rounded-md px-2 py-1 text-xs text-zinc-400 transition hover:bg-zinc-800"
                @click="clearLogs"
              >
                清空
              </button>
              <button
                :disabled="running"
                class="inline-flex items-center gap-1.5 rounded-md bg-theme-dark px-3 py-1 text-xs font-medium text-white transition hover:bg-theme disabled:cursor-not-allowed disabled:opacity-50"
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
            class="flex-1 overflow-y-auto bg-zinc-900 p-3 font-mono text-xs leading-5"
          >
            <p v-if="!logs.length" class="text-zinc-600">// 等待运行，点击「运行测试」查看输出…</p>
            <p v-for="(l, i) in logs" :key="i" :class="logColor(l.level)">
              <span class="select-none text-zinc-600">[{{ l.time }}]</span> {{ l.text }}
            </p>
            <span v-if="running" class="animate-pulse text-zinc-400">▋</span>
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
      <div class="flex h-full max-h-[80vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900">
        <div class="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
          <span class="text-sm font-semibold text-white">参考答案 — {{ editorFileName }}</span>
          <div class="flex items-center gap-2">
            <button
              class="rounded-md px-2 py-1 text-xs text-zinc-400 transition hover:bg-zinc-800"
              @click="copyAnswer"
            >
              {{ copied ? '已复制' : '复制' }}
            </button>
            <button
              class="rounded-md px-2 py-1 text-xs text-zinc-400 transition hover:bg-zinc-800"
              @click="closeAnswer"
            >
              关闭
            </button>
          </div>
        </div>
        <pre
          v-if="answerCode"
          class="flex-1 overflow-auto bg-zinc-950 p-4 font-mono text-sm leading-6 text-zinc-200"
        >{{ answerCode }}</pre>
        <p v-else class="grid flex-1 place-items-center text-sm text-zinc-500">暂无参考答案</p>
      </div>
    </div>
  </div>
</template>
