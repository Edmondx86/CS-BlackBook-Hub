<script setup>
// 章节详情：直接请求单章接口 GET /api/v1/chapters/{chapterId}，只展示该章节的 Lab。
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const route = useRoute()
const chapterId = computed(() => route.params.chapterId)

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
</script>

<template>
  <div class="h-full overflow-y-auto bg-zinc-950">
    <div class="mx-auto max-w-4xl px-6 py-10">
      <!-- 加载中 -->
      <div v-if="loading" class="flex items-center justify-center gap-3 py-24 text-zinc-400">
        <span class="h-4 w-4 animate-spin rounded-full border-2 border-zinc-600 border-t-theme"></span>
        正在加载…
      </div>

      <!-- 章节不存在 -->
      <div v-else-if="notFound" class="py-24 text-center text-zinc-400">
        未找到该章节。
        <RouterLink to="/chapters" class="text-theme-light underline">返回目录</RouterLink>
      </div>

      <!-- 加载失败 -->
      <div v-else-if="error" class="flex flex-col items-center gap-4 py-24 text-center">
        <div class="text-4xl">⚠️</div>
        <p class="text-zinc-300">{{ error }}</p>
        <button
          class="rounded-lg bg-theme-dark px-4 py-2 text-sm font-medium text-white transition hover:bg-theme"
          @click="fetchChapter"
        >
          重试
        </button>
      </div>

      <!-- 章节内容 -->
      <template v-else>
        <header class="mb-8">
          <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span class="text-xs font-semibold uppercase tracking-wider text-theme-light">
              {{ chapter.number }}
            </span>
            <h1 class="text-2xl font-bold text-white">{{ chapter.title }}</h1>
          </div>
          <p v-if="chapter.summary" class="mt-1 text-sm text-zinc-400">{{ chapter.summary }}</p>

          <div v-if="chapter.knowledge_points?.length" class="mt-4 flex flex-wrap gap-2">
            <span
              v-for="(kp, i) in chapter.knowledge_points"
              :key="i"
              class="rounded-md bg-zinc-800 px-2 py-1 text-xs text-zinc-300"
            >
              {{ kp }}
            </span>
          </div>
        </header>

        <!-- Wireshark 实验 -->
        <section v-if="chapter.wireshark_labs?.length" class="mb-8">
          <h2 class="mb-3 text-xs font-semibold uppercase tracking-wider text-brand">
            Wireshark 实验
          </h2>
          <div class="grid gap-3 sm:grid-cols-2">
            <RouterLink
              v-for="lab in chapter.wireshark_labs"
              :key="lab.id"
              :to="`/chapters/${chapterId}/labs/${lab.id}`"
              class="group rounded-lg border border-zinc-800 bg-zinc-900 p-4 transition hover:border-brand/50 hover:bg-zinc-900/80"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-sm font-medium text-zinc-200 group-hover:text-white">
                  {{ lab.title }}
                </span>
                <span class="text-brand transition group-hover:translate-x-0.5">→</span>
              </div>
              <div class="mt-1 text-xs text-zinc-500">Wireshark · 抓包分析</div>
            </RouterLink>
          </div>
        </section>

        <!-- Socket 编程练习 -->
        <section v-if="chapter.socket_exercises?.length">
          <h2 class="mb-3 text-xs font-semibold uppercase tracking-wider text-theme-light">
            Socket 编程练习
          </h2>
          <div class="grid gap-3 sm:grid-cols-2">
            <RouterLink
              v-for="ex in chapter.socket_exercises"
              :key="ex.id"
              :to="`/chapters/${chapterId}/labs/${ex.id}`"
              class="group rounded-lg border border-zinc-800 bg-zinc-900 p-4 transition hover:border-theme/50 hover:bg-zinc-900/80"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-sm font-medium text-zinc-200 group-hover:text-white">
                  {{ ex.title }}
                </span>
                <span class="text-theme-light transition group-hover:translate-x-0.5">→</span>
              </div>
              <div class="mt-1 text-xs text-zinc-500">Socket · 在线判题</div>
            </RouterLink>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>
