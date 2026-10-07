<script setup>
// 工具介绍页（/tools/:slug）：根据路由参数展示对应工具的详细图文介绍。
// 内容用 Markdown 编写，存放在 src/content/tools/<slug>.md，与首页卡片共用 src/data/tools.js 的标题/描述/图标。
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { tools } from '../data/tools'
import { createMarkdown } from '../markdown'

const route = useRoute()
const tool = computed(() => tools.find((t) => t.slug === route.params.slug))

// 工具介绍 Markdown 按需加载（非 eager），每篇各自成为独立小 chunk，看哪个工具才下载哪篇。
const mdModules = import.meta.glob('../content/tools/*.md', {
  query: '?raw',
  import: 'default',
})
const markdownBySlug = Object.fromEntries(
  Object.entries(mdModules).map(([path, load]) => [path.split('/').pop().replace(/\.md$/, ''), load]),
)

const md = createMarkdown()
const rawMarkdown = ref('')
watch(
  () => route.params.slug,
  async (slug) => {
    const load = markdownBySlug[slug]
    rawMarkdown.value = ''
    if (load) rawMarkdown.value = await load()
  },
  { immediate: true },
)
const contentHtml = computed(() => (tool.value ? md.render(rawMarkdown.value) : ''))
</script>

<template>
  <div class="flex h-full flex-col text-primary antialiased">
    <!-- 页头 -->
    <header class="border-b border-line px-6 py-4">
      <div class="mx-auto flex max-w-4xl items-center gap-4">
        <RouterLink to="/" class="shrink-0 text-sm text-muted transition hover:text-primary">
          ← 返回首页
        </RouterLink>
        <div class="min-w-0">
          <div class="text-xs font-semibold uppercase tracking-widest text-brand">常见工具 · Tools</div>
          <h1 class="truncate text-lg font-semibold text-primary">{{ tool?.title ?? '工具' }}</h1>
        </div>
      </div>
    </header>

    <!-- 主体 -->
    <div class="flex-1 overflow-y-auto">
      <div class="mx-auto max-w-4xl px-6 py-10">
        <!-- 未找到工具 -->
        <div v-if="!tool" class="py-24 text-center text-muted">
          未找到该工具。
          <RouterLink to="/" class="text-theme-light underline">返回首页</RouterLink>
        </div>

        <template v-else>
          <!-- 工具横幅：图标 + 英文副标题 + 一句话简介 -->
          <div class="flex items-start gap-5 border-b border-line pb-8">
            <div class="shrink-0 text-brand" v-html="tool.icon"></div>
            <div class="min-w-0">
              <p class="text-xs font-semibold uppercase tracking-widest text-brand">{{ tool.subtitle }}</p>
              <p class="mt-2 max-w-2xl text-lg leading-relaxed text-tertiary">{{ tool.desc }}</p>
            </div>
          </div>

          <!-- 官方链接：由 data/tools.js 的 links 字段驱动，没配 links 的工具不显示 -->
          <section v-if="tool.links?.length" class="mt-8">
            <p class="text-xs font-semibold uppercase tracking-widest text-brand">官方链接 · Links</p>
            <div class="mt-3 flex flex-wrap gap-3">
              <a
                v-for="link in tool.links"
                :key="link.url"
                :href="link.url"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-2 rounded-lg border border-line-strong px-4 py-2 text-sm font-medium text-secondary transition hover:border-brand hover:bg-elevated hover:text-primary"
              >
                {{ link.label }}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  class="h-4 w-4 text-brand"
                  aria-hidden="true"
                >
                  <path d="M15 3h6v6" />
                  <path d="M10 14 21 3" />
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                </svg>
              </a>
            </div>
          </section>

          <!-- Markdown 图文介绍 -->
          <article class="markdown-body mt-8" v-html="contentHtml"></article>
        </template>
      </div>
    </div>
  </div>
</template>
