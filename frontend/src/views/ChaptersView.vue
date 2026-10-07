<script setup>
// 章节目录：列出《自顶向下》所有章节，点击进入对应章节的实验列表。
import { onMounted, ref } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const chapters = ref([])
const loading = ref(true)
const error = ref('')

async function fetchChapters() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`${API_BASE}/api/v1/chapters`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    chapters.value = await res.json()
  } catch (e) {
    error.value = `加载目录失败：${e.message}`
  } finally {
    loading.value = false
  }
}

onMounted(fetchChapters)

// 从 "Chapter 5" 提取章节序号，用于快捷导航 chips 的短标签（如“第5章”）。
function chapterNum(ch) {
  return ch.number.replace(/Chapter\s*/i, '')
}
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="mx-auto max-w-6xl px-6 py-10">
      <header class="mb-8">
        <h1 class="text-2xl font-bold text-primary">章节目录</h1>
        <p class="mt-1 text-sm text-muted">选择一个章节，进入对应的实验与练习</p>
      </header>

      <!-- 章节快捷导航 -->
      <div v-if="chapters.length" class="mb-6 flex flex-wrap gap-2">
        <RouterLink
          v-for="ch in chapters"
          :key="ch.id"
          :to="`/chapters/${ch.id}`"
          class="rounded-full border border-line-strong px-3.5 py-1.5 text-xs font-medium text-tertiary transition hover:border-brand hover:text-primary"
        >
          第{{ chapterNum(ch) }}章
        </RouterLink>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="flex items-center justify-center gap-3 py-24 text-muted">
        <span class="h-4 w-4 animate-spin rounded-full border-2 border-line-strong border-t-theme"></span>
        正在加载…
      </div>

      <!-- 加载失败 -->
      <div v-else-if="error" class="flex flex-col items-center gap-4 py-24 text-center">
        <div class="text-4xl">⚠️</div>
        <p class="text-tertiary">{{ error }}</p>
        <button
          class="rounded-lg bg-btn-alt px-4 py-2 text-sm font-medium text-btn-alt-text transition hover:bg-btn-alt-hover"
          @click="fetchChapters"
        >
          重试
        </button>
      </div>

      <!-- 章节卡片列表 -->
      <div v-else class="space-y-4">
        <RouterLink
          v-for="ch in chapters"
          :key="ch.id"
          :to="`/chapters/${ch.id}`"
          class="group relative flex items-center overflow-hidden rounded-xl border border-cardline bg-card/40 transition-transform duration-300 hover:scale-[1.02] hover:border-brand/60"
        >
          <div class="relative z-10 p-5">
            <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span class="text-xs font-semibold uppercase tracking-wider text-brand-light">
                {{ ch.number }}
              </span>
              <h2 class="text-lg font-semibold text-primary">{{ ch.title }}</h2>
            </div>
            <p v-if="ch.summary" class="mt-1 text-sm text-muted">{{ ch.summary }}</p>
            <div class="mt-2 flex gap-4 text-xs text-faint">
              <span>{{ ch.wireshark_labs?.length ?? 0 }} 个 Wireshark 实验</span>
              <span>{{ ch.socket_exercises?.length ?? 0 }} 个 Socket 练习</span>
            </div>
          </div>

          <!-- 右侧渐变滑动窗（斜切） -->
          <div
            class="slide-panel absolute inset-y-0 right-0 flex w-[40%] translate-x-full items-center justify-end bg-gradient-to-l from-brand via-brand/70 to-transparent pr-8 transition-transform duration-300 ease-out group-hover:translate-x-0"
          >
            <span class="text-3xl font-bold text-inverse" aria-hidden="true">→</span>
          </div>
        </RouterLink>
      </div>
    </div>
  </div>
</template>
