<script setup>
// 全局外壳：页首（favicon + 站点名 + 面包屑 / 首页·帮助 / 注册·登录）+ <router-view /> 挂载点。
// 仅首页使用「浮动岛」效果；「首页 | 帮助」也仅在首页显示。
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const route = useRoute()

const isHome = computed(() => route.path === '/')

// 章节编号（用于面包屑展示「Chapter N」）
const chapterNumber = ref('')

watch(
  () => route.params.chapterId,
  async (id) => {
    chapterNumber.value = ''
    if (!id) return
    try {
      const res = await fetch(`${API_BASE}/api/v1/chapters/${id}`)
      if (res.ok) {
        const data = await res.json()
        chapterNumber.value = data.number ?? ''
      }
    } catch {
      /* 获取失败时忽略，面包屑退化为「章节」 */
    }
  },
  { immediate: true },
)

// 面包屑：按路由层级生成，首页不显示。
const crumbs = computed(() => {
  if (route.path === '/chapters') {
    return [{ label: '首页', to: '/' }, { label: '章节' }]
  }
  if (route.path.startsWith('/chapters/')) {
    const items = [{ label: '首页', to: '/' }, { label: '章节', to: '/chapters' }]
    if (chapterNumber.value) items.push({ label: chapterNumber.value })
    if (route.params.labId) items.push({ label: '实验' })
    return items
  }
  return []
})
</script>

<template>
  <div class="flex h-screen flex-col bg-zinc-950 text-zinc-100 antialiased">
    <!-- 页首：首页浮动岛，其余普通顶部栏 -->
    <header
      class="grid grid-cols-[1fr_auto_1fr] items-center gap-4 px-4 py-6"
      :class="
        isHome
          ? 'fixed inset-x-4 top-4 z-50 mx-auto max-w-5xl rounded-2xl border border-white/10 bg-zinc-900/60 shadow-lg shadow-black/20 backdrop-blur-xl'
          : 'border-b border-zinc-800 bg-zinc-950'
      "
    >
      <!-- 左：favicon + 站点名 + 面包屑 -->
      <div class="flex min-w-0 items-center gap-3">
        <RouterLink to="/" class="flex shrink-0 items-center gap-2">
          <img src="/favicon.png" alt="站点图标" class="h-8 w-8 object-contain" />
          <span class="text-lg font-semibold text-white">CS-BlackBook-Hub</span>
        </RouterLink>

        <nav v-if="crumbs.length" class="flex min-w-0 items-center gap-1.5 text-sm text-zinc-400">
          <template v-for="(c, i) in crumbs" :key="c.label">
            <span v-if="i > 0" class="text-zinc-600">/</span>
            <RouterLink v-if="c.to" :to="c.to" class="shrink-0 transition hover:text-white">
              {{ c.label }}
            </RouterLink>
            <span v-else class="truncate text-zinc-300">{{ c.label }}</span>
          </template>
        </nav>
      </div>

      <!-- 中：首页 | 帮助（仅首页显示） -->
      <nav v-if="isHome" class="flex items-center gap-2 text-sm text-zinc-300">
        <RouterLink
          to="/"
          class="transition hover:text-theme-light"
          :class="route.path === '/' ? 'font-medium' : ''"
        >
          首页
        </RouterLink>
        <span class="text-zinc-600">|</span>
        <button type="button" class="transition hover:text-theme-light">帮助</button>
      </nav>

      <!-- 右：注册 | 登录（占位，暂未实现） -->
      <div class="flex items-center justify-self-end gap-2 text-sm text-zinc-300">
        <button type="button" class="transition hover:text-theme-light">注册</button>
        <span class="text-zinc-600">|</span>
        <button type="button" class="transition hover:text-theme-light">登录</button>
      </div>
    </header>

    <!-- 页面挂载点 -->
    <main class="min-h-0 flex-1 overflow-hidden">
      <router-view />
    </main>
  </div>
</template>
