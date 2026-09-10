<script setup>
// 全局外壳：顶部导航栏 + <router-view /> 挂载点。
// 任何页面都能通过顶部「首页 / 章节」随时切换层级。
import { useRoute } from 'vue-router'

const route = useRoute()

// 计算导航高亮：首页精确匹配，章节按前缀匹配（覆盖 /chapters 与 /chapters/:id）
function navClass(path) {
  const active = path === '/' ? route.path === '/' : route.path.startsWith(path)
  return `rounded-md px-3 py-1.5 transition hover:bg-zinc-800 hover:text-white ${
    active ? 'bg-zinc-800 text-white' : 'text-zinc-300'
  }`
}
</script>

<template>
  <div class="flex h-screen flex-col bg-zinc-950 text-zinc-100 antialiased">
    <!-- 顶部导航栏 -->
    <header class="flex items-center gap-4 border-b border-zinc-800 px-6 py-3">
      <RouterLink to="/" class="flex items-center gap-2">
        <span
          class="grid h-7 w-7 place-items-center rounded-md bg-sky-600 text-sm font-bold text-white"
        >
          T
        </span>
        <span class="font-semibold text-white">CS Top-Down Hub</span>
      </RouterLink>

      <nav class="ml-auto flex items-center gap-1 text-sm">
        <RouterLink to="/" :class="navClass('/')">首页</RouterLink>
        <RouterLink to="/chapters" :class="navClass('/chapters')">章节</RouterLink>
      </nav>
    </header>

    <!-- 页面挂载点 -->
    <main class="min-h-0 flex-1 overflow-hidden">
      <router-view />
    </main>
  </div>
</template>
