<script setup>
// 章节详情：直接请求单章接口 GET /api/v1/chapters/{chapterId}，只展示该章节的 Lab。
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import KnowledgeCard from '../components/KnowledgeCard.vue'
import LabCard from '../components/LabCard.vue'
import { chapterFlashcards } from '../content/flashcards'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const route = useRoute()
const chapterId = computed(() => route.params.chapterId)
const cards = computed(() => chapterFlashcards[chapterId.value] ?? [])

// 章节目录（用于“上一章 / 下一章”导航）
const chapters = ref([])
const chapterIndex = computed(() => chapters.value.findIndex((c) => c.id === chapterId.value))
const prevChapter = computed(() => (chapterIndex.value > 0 ? chapters.value[chapterIndex.value - 1] : null))
const nextChapter = computed(
  () =>
    chapterIndex.value >= 0 && chapterIndex.value < chapters.value.length - 1
      ? chapters.value[chapterIndex.value + 1]
      : null,
)

const chapter = ref(null)
const loading = ref(true)
const error = ref('')
const notFound = ref(false)

async function fetchChapter() {
  loading.value = true
  error.value = ''
  notFound.value = false
  chapter.value = null
  try {
    const res = await fetch(`${API_BASE}/api/v1/chapters/${chapterId.value}`)
    if (res.status === 404) {
      notFound.value = true
      return
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    chapter.value = await res.json()
  } catch (e) {
    error.value = `加载章节失败：${e.message}`
  } finally {
    loading.value = false
  }
}

// 初次挂载 + 章节参数变化时都重新请求
watch(chapterId, fetchChapter, { immediate: true })

// 从 flashcards6“Go to Lab”跳回时携带 #hash，平滑滚动到对应区块（如 #wireshark）。
function scrollToHash() {
  const hash = route.hash
  if (!hash) return
  nextTick(() =>
    document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
  )
}
onMounted(scrollToHash)
watch([() => route.hash, loading], () => {
  if (!loading.value && route.hash) scrollToHash()
})

async function fetchChaptersList() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/chapters`)
    if (res.ok) chapters.value = await res.json()
  } catch {
    /* 目录获取失败时不显示上一章/下一章 */
  }
}
onMounted(fetchChaptersList)
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="mx-auto max-w-6xl px-6 py-10">
      <!-- 加载中 -->
      <div v-if="loading" class="flex items-center justify-center gap-3 py-24 text-muted">
        <span class="h-4 w-4 animate-spin rounded-full border-2 border-line-strong border-t-theme"></span>
        正在加载…
      </div>

      <!-- 章节不存在 -->
      <div v-else-if="notFound" class="py-24 text-center text-muted">
        未找到该章节。
        <RouterLink to="/chapters" class="text-theme-light underline">返回目录</RouterLink>
      </div>

      <!-- 加载失败 -->
      <div v-else-if="error" class="flex flex-col items-center gap-4 py-24 text-center">
        <div class="text-4xl">⚠️</div>
        <p class="text-tertiary">{{ error }}</p>
        <button
          class="rounded-lg bg-btn-alt px-4 py-2 text-sm font-medium text-btn-alt-text transition hover:bg-btn-alt-hover"
          @click="fetchChapter"
        >
          重试
        </button>
      </div>

      <!-- 章节内容 -->
      <template v-else>
        <header class="mb-8">
          <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span class="text-2xl font-bold uppercase tracking-wider text-theme-light">
              {{ chapter.number }}
            </span>
            <h1 class="text-2xl font-bold text-primary">{{ chapter.title }}</h1>
          </div>
          <p v-if="chapter.summary" class="mt-1 text-sm text-muted">{{ chapter.summary }}</p>

          <div v-if="chapter.knowledge_points?.length" class="mt-4 flex flex-wrap gap-2">
            <span
              v-for="(kp, i) in chapter.knowledge_points"
              :key="i"
              class="rounded-md bg-elevated px-2 py-1 text-xs text-tertiary"
            >
              {{ kp }}
            </span>
          </div>
        </header>

        <!-- 知识卡片（Flashcards）：悬停翻转，点击进入详情 -->
        <section v-if="cards.length" class="mb-8">
          <h2 class="mb-3 text-2xl font-bold uppercase tracking-wider text-brand">
            知识卡片 · Flashcards
          </h2>
          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <KnowledgeCard
              v-for="(card, i) in cards"
              :key="card.slug"
              :card="card"
              :index="i + 1"
              :to="`/chapters/${chapterId}/${card.slug}`"
            />
          </div>
        </section>

        <!-- Wireshark 实验 -->
        <section v-if="chapter.wireshark_labs?.length" id="wireshark" class="mb-8 scroll-mt-4">
          <h2 class="mb-3 text-2xl font-bold uppercase tracking-wider text-brand">
            Wireshark 实验
          </h2>
          <div class="flex flex-col gap-3">
            <LabCard
              v-for="lab in chapter.wireshark_labs"
              :key="lab.id"
              :to="`/chapters/${chapterId}/labs/${lab.id}`"
              :title="lab.title"
              hint="Wireshark · 抓包分析"
              tone="brand"
            />
          </div>
        </section>

        <!-- Socket 编程练习 -->
        <section v-if="chapter.socket_exercises?.length" id="socket" class="scroll-mt-4">
          <h2 class="mb-3 text-2xl font-bold uppercase tracking-wider text-theme-light">
            Socket 编程练习
          </h2>
          <div class="flex flex-col gap-3">
            <LabCard
              v-for="ex in chapter.socket_exercises"
              :key="ex.id"
              :to="`/chapters/${chapterId}/labs/${ex.id}`"
              :title="ex.title"
              hint="Socket · 在线判题"
              tone="theme"
            />
          </div>
        </section>

        <!-- 上一章 / 下一章 -->
        <nav class="mt-12 grid gap-3 border-t border-line pt-6 sm:grid-cols-2">
          <RouterLink
            v-if="prevChapter"
            :to="`/chapters/${prevChapter.id}`"
            class="group flex items-center gap-3 rounded-xl border border-cardline bg-card/40 p-4 transition-transform duration-300 hover:scale-105 hover:border-brand/50"
          >
            <span class="text-2xl text-brand" aria-hidden="true">←</span>
            <div class="min-w-0">
              <div class="text-xs text-faint">上一章</div>
              <div class="truncate text-sm font-semibold text-primary group-hover:text-brand-light">
                {{ prevChapter.number }} · {{ prevChapter.title }}
              </div>
            </div>
          </RouterLink>

          <RouterLink
            v-if="nextChapter"
            :to="`/chapters/${nextChapter.id}`"
            class="group flex items-center justify-end gap-3 rounded-xl border border-cardline bg-card/40 p-4 text-right transition-transform duration-300 hover:scale-105 hover:border-theme/50"
          >
            <div class="min-w-0">
              <div class="text-xs text-faint">下一章</div>
              <div class="truncate text-sm font-semibold text-primary group-hover:text-theme-light">
                {{ nextChapter.number }} · {{ nextChapter.title }}
              </div>
            </div>
            <span class="text-2xl text-theme-light" aria-hidden="true">→</span>
          </RouterLink>
        </nav>
      </template>
    </div>
  </div>
</template>
