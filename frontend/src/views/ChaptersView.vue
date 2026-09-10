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
</script>

<template>
  <div class="h-full overflow-y-auto bg-zinc-950">
    <div class="mx-auto max-w-4xl px-6 py-10">
      <!-- 面包屑 -->
      <nav class="mb-2 text-xs text-zinc-500">
        <RouterLink to="/" class="transition hover:text-zinc-300">首页</RouterLink>
        <span class="mx-1">/</span>
        <span class="text-zinc-300">章节</span>
      </nav>

      <header class="mb-8">
        <h1 class="text-2xl font-bold text-white">章节目录</h1>
        <p class="mt-1 text-sm text-zinc-400">选择一个章节，进入对应的实验与练习</p>
      </header>

      <!-- 加载中 -->
      <div v-if="loading" class="flex items-center justify-center gap-3 py-24 text-zinc-400">
        <span class="h-4 w-4 animate-spin rounded-full border-2 border-zinc-600 border-t-sky-400"></span>
        正在加载…
      </div>

      <!-- 加载失败 -->
      <div v-else-if="error" class="flex flex-col items-center gap-4 py-24 text-center">
        <div class="text-4xl">⚠️</div>
        <p class="text-zinc-300">{{ error }}</p>
        <button
          class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500"
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
          class="group flex items-center justify-between gap-4 rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 transition hover:border-sky-500/50 hover:bg-zinc-900/70"
        >
          <div>
            <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span class="text-xs font-semibold uppercase tracking-wider text-sky-400">
                {{ ch.number }}
              </span>
              <h2 class="text-lg font-semibold text-white">{{ ch.title }}</h2>
            </div>
            <p v-if="ch.summary" class="mt-1 text-sm text-zinc-400">{{ ch.summary }}</p>
            <div class="mt-2 flex gap-4 text-xs text-zinc-500">
              <span>{{ ch.wireshark_labs?.length ?? 0 }} 个 Wireshark 实验</span>
              <span>{{ ch.socket_exercises?.length ?? 0 }} 个 Socket 练习</span>
            </div>
          </div>
          <span class="text-zinc-500 transition group-hover:translate-x-0.5 group-hover:text-sky-400">
            →
          </span>
        </RouterLink>
      </div>
    </div>
  </div>
</template>
