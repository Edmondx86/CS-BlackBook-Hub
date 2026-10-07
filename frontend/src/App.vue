<script setup>
// 全局外壳：统一顶部导航（logo + 右侧菜单）+ <router-view /> 挂载点。
// 页头固定悬浮：首页在走马灯上透明、滚过后半透明；其它页面始终半透明。
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { headerScrolled } from './composables/useHeader'

const route = useRoute()
const isHome = computed(() => route.path === '/')
const isAbout = computed(() => route.path === '/about')

// 页头背景：非首页固定半透明；首页滚动离开走马灯后切换为半透明。
const headerClass = computed(() => {
  const solid = 'border-b border-line/60 bg-header/70 backdrop-blur-md'
  if (!isHome.value) return solid
  return headerScrolled.value ? solid : 'bg-transparent'
})

// 离开首页时重置滚动状态，避免下次进入还停留在半透明。
watch(
  () => route.path,
  () => {
    headerScrolled.value = false
  },
)

// 章节下拉：从后端拉取章节目录，供顶栏“计算机入门”下拉逐章跳转。
const chapters = ref([])
async function fetchChapters() {
  try {
    const res = await fetch(`${import.meta.env.VITE_API_BASE ?? ''}/api/v1/chapters`)
    if (res.ok) chapters.value = await res.json()
  } catch {
    /* 目录获取失败时，下拉不显示章节列表 */
  }
}
onMounted(fetchChapters)

// 颜色模式：夜间（月亮）↔ 白天（太阳）。写入 <html data-theme> 并持久化到 localStorage。
const isDark = ref(document.documentElement.getAttribute('data-theme') !== 'light')

function toggleTheme() {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.documentElement.removeAttribute('data-theme')
    localStorage.setItem('theme', 'dark')
  } else {
    document.documentElement.setAttribute('data-theme', 'light')
    localStorage.setItem('theme', 'light')
  }
}
</script>

<template>
  <div class="flex h-screen flex-col text-primary antialiased">
    <header
      v-if="!isAbout"
      class="fixed inset-x-0 top-0 z-50 flex h-16 items-center justify-between gap-4 px-4 transition-colors duration-300"
      :class="headerClass"
    >
      <!-- 左：favicon + 站点名（点击回首页） -->
      <RouterLink to="/" class="flex shrink-0 items-center gap-2">
        <img src="/favicon.png" alt="站点图标" class="h-8 w-8 object-contain" />
        <span class="text-lg font-semibold text-primary">CS-BlackBook-Hub</span>
      </RouterLink>

      <!-- 右：导航 -->
      <nav class="flex items-center gap-1">
        <!-- 首页 -->
        <RouterLink
          to="/"
          class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-theme-light transition hover:bg-elevated/60 hover:text-primary"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="h-5 w-5 text-brand"
            aria-hidden="true"
          >
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            <polyline points="9 22 9 12 15 12 15 22" />
          </svg>
          <span>首页</span>
        </RouterLink>

        <!-- 计算机入门（悬停下拉） -->
        <div class="group relative">
          <button
            type="button"
            class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-theme-light transition hover:bg-elevated/60 hover:text-primary"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-5 w-5 text-brand"
              aria-hidden="true"
            >
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span>计算机入门</span>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-4 w-4 text-theme-light"
              aria-hidden="true"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          <div
            class="invisible absolute right-0 top-full pt-2 opacity-0 transition group-hover:visible group-hover:opacity-100"
          >
            <div class="min-w-72 rounded-lg border border-line bg-card p-1 shadow-xl">
              <RouterLink
                to="/chapters"
                class="block rounded-md px-3 py-2 text-sm font-medium text-brand-light transition hover:bg-elevated hover:text-primary"
              >
                《计算机网络：自顶向下方法》
              </RouterLink>
              <div class="my-1 border-t border-line"></div>
              <div class="max-h-80 overflow-y-auto">
                <RouterLink
                  v-for="ch in chapters"
                  :key="ch.id"
                  :to="`/chapters/${ch.id}`"
                  class="block rounded-md px-3 py-1.5 text-sm text-tertiary transition hover:bg-elevated hover:text-primary"
                >
                  <span class="text-xs font-semibold text-brand">{{ ch.number }}</span>
                  <span class="ml-2">{{ ch.title }}</span>
                </RouterLink>
              </div>
              <div class="my-1 border-t border-line"></div>
              <RouterLink
                to="/csapp"
                class="block rounded-md px-3 py-2 text-sm text-faint transition hover:bg-elevated hover:text-tertiary"
              >
                《深入理解计算机系统》(开发中)
              </RouterLink>
            </div>
            
          </div>
        </div>

        <!-- 说明（悬停下拉） -->
        <div class="group relative">
          <button
            type="button"
            class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-theme-light transition hover:bg-elevated/60 hover:text-primary"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-5 w-5 text-brand"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            <span>说明</span>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-4 w-4 text-theme-light"
              aria-hidden="true"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          <div
            class="invisible absolute right-0 top-full pt-2 opacity-0 transition group-hover:visible group-hover:opacity-100"
          >
            <div class="min-w-40 rounded-lg border border-line bg-card p-1 shadow-xl">
              <RouterLink
                to="/about"
                class="block rounded-md px-3 py-2 text-sm text-tertiary transition hover:bg-elevated hover:text-primary"
              >
                关于
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- 颜色模式切换：夜间月亮 ↔ 白天太阳 -->
        <button
          type="button"
          :title="isDark ? '切换到白天模式' : '切换到夜间模式'"
          :aria-label="isDark ? '切换到白天模式' : '切换到夜间模式'"
          class="rounded-lg p-2 text-theme-light transition hover:bg-elevated/60 hover:text-primary"
          @click="toggleTheme"
        >
          <!-- 月亮（夜间模式） -->
          <svg
            v-if="isDark"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="h-5 w-5 text-brand"
            aria-hidden="true"
          >
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
          <!-- 太阳（白天模式） -->
          <svg
            v-else
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="h-5 w-5 text-brand"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2" />
            <path d="M12 20v2" />
            <path d="m4.93 4.93 1.41 1.41" />
            <path d="m17.66 17.66 1.41 1.41" />
            <path d="M2 12h2" />
            <path d="M20 12h2" />
            <path d="m6.34 17.66-1.41 1.41" />
            <path d="m19.07 4.93-1.41 1.41" />
          </svg>
        </button>
      </nav>
    </header>

    <!-- 非首页占位：顶开固定页头的高度，避免内容被遮挡 -->
    <div v-if="!isHome && !isAbout" class="h-16 shrink-0" aria-hidden="true"></div>

    <!-- 页面挂载点 -->
    <main class="min-h-0 flex-1 overflow-hidden">
      <router-view />
    </main>
  </div>
</template>
