<script setup>
// 知识卡片详情页（/chapters/:chapterId/:slug，如 /chapters/ch1/flashcards1）。
// 用 Markdown 渲染该卡片的详细知识点讲解（内容在 src/content/flashcards/<chapterId>-<slug>.md），
// 底部用左右箭头翻页：第一章 flashcards1 只有“下一张”，最后一张只有“上一张”+“上手做实验”。
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createMarkdown } from '../markdown'
import { chapterFlashcards } from '../content/flashcards'
import ChapterNav from '../components/ChapterNav.vue'
import { useChapter } from '../composables/useChapter'

const route = useRoute()
const chapterId = computed(() => route.params.chapterId)
const slug = computed(() => route.params.slug)

// 章节概览：用于左侧导航列出本章的实验，以及判断「上手做实验」的跳转目标。
// 与导航共用同一份缓存（见 composables/useChapter.js），不会重复请求。
const chapter = useChapter(chapterId)

const cards = computed(() => chapterFlashcards[chapterId.value] ?? chapterFlashcards.ch1 ?? [])
const idx = computed(() => cards.value.findIndex((c) => c.slug === slug.value))
const card = computed(() => (idx.value >= 0 ? cards.value[idx.value] : null))
const prevCard = computed(() => (idx.value > 0 ? cards.value[idx.value - 1] : null))
const nextCard = computed(
  () => (idx.value >= 0 && idx.value < cards.value.length - 1 ? cards.value[idx.value + 1] : null),
)
const isLast = computed(() => idx.value === cards.value.length - 1)

// “上手做实验”跳转目标：ch2 跳到 Socket 编程练习区，其余有实验的章节跳到 Wireshark 实验区；
// 无实验的章节（如 ch5 网络层控制平面）不显示该按钮。
const ctaTarget = computed(() => {
  if (!chapter.value) return ''
  const hasWireshark = chapter.value.wireshark_labs?.length
  const hasSocket = chapter.value.socket_exercises?.length
  if (chapterId.value === 'ch2' && hasSocket) return 'socket'
  if (hasWireshark) return 'wireshark'
  if (hasSocket) return 'socket'
  return ''
})

// 卡片 Markdown 按需加载：按“chapterId-slug”建立「文件名 -> 动态 import」映射
// （文件名 ch1-flashcardsN.md -> ch1-flashcardsN）。
//
// 这里刻意不用 eager: true —— 51 张卡片的正文合计约 250 kB，全量内联会让本页 chunk
// 变成整站最大的一个；改成动态 import 后，每张卡片各自成为独立的小 chunk，
// 看哪张才下载哪张。
const mdModules = import.meta.glob('../content/flashcards/*.md', {
  query: '?raw',
  import: 'default',
})
const markdownBySlug = Object.fromEntries(
  Object.entries(mdModules).map(([path, load]) => [path.split('/').pop().replace(/\.md$/, ''), load]),
)

const md = createMarkdown()
const rawMarkdown = ref('')
watch(
  [chapterId, slug],
  async ([cid, s]) => {
    const load = markdownBySlug[`${cid}-${s}`]
    // 切换卡片时先清空，避免上一张的内容短暂残留；加载失败则显示空正文。
    rawMarkdown.value = ''
    if (load) rawMarkdown.value = await load()
  },
  { immediate: true },
)
const contentHtml = computed(() => (card.value ? md.render(rawMarkdown.value) : ''))
</script>

<template>
  <div class="flex h-full flex-col text-primary antialiased">
    <!-- 页头 -->
    <header class="border-b border-line px-6 py-4">
      <div class="flex items-center gap-4">
        <RouterLink
          :to="`/chapters/${chapterId}`"
          class="shrink-0 text-sm text-muted transition hover:text-primary"
        >
          ← 返回章节
        </RouterLink>
        <div class="min-w-0">
          <div class="text-xs font-semibold uppercase tracking-widest text-brand">
            Flashcards<template v-if="card"> · Card {{ idx + 1 }} / {{ cards.length }}</template>
          </div>
          <h1 class="truncate text-lg font-semibold text-primary">{{ card?.title ?? '知识卡片' }}</h1>
        </div>
      </div>
    </header>

    <!-- 主体：左侧本章导航 + 右侧正文 -->
    <div class="flex min-h-0 flex-1">
      <ChapterNav
        :chapter-id="chapterId"
        :chapter="chapter"
        current-kind="flashcard"
        :current-id="slug"
        class="hidden md:flex"
      />

      <div class="min-w-0 flex-1 overflow-y-auto">
        <div class="mx-auto max-w-4xl px-6 py-8">
          <!-- 未找到卡片 -->
          <div v-if="!card" class="py-24 text-center text-muted">
            未找到该卡片。
            <RouterLink :to="`/chapters/${chapterId}`" class="text-theme-light underline">返回章节</RouterLink>
          </div>

          <template v-else>
            <!-- 副标题 + Markdown 正文 -->
            <p class="text-xs font-semibold uppercase tracking-widest text-brand">{{ card.subtitle }}</p>
            <article class="markdown-body mt-4" v-html="contentHtml"></article>

            <!-- 翻页箭头：左上一张 / 右下一张 -->
            <nav class="mt-10 flex items-center justify-between gap-3 border-t border-line pt-6">
              <RouterLink
                v-if="prevCard"
                :to="`/chapters/${chapterId}/${prevCard.slug}`"
                class="inline-flex items-center gap-2 rounded-lg border border-line-strong px-4 py-2 text-sm font-medium text-secondary transition hover:border-line-strong hover:bg-elevated"
              >
                <span aria-hidden="true">←</span> 上一张
              </RouterLink>
              <span v-else class="w-28"></span>

              <RouterLink
                v-if="nextCard"
                :to="`/chapters/${chapterId}/${nextCard.slug}`"
                class="inline-flex items-center gap-2 rounded-lg border border-line-strong px-4 py-2 text-sm font-medium text-secondary transition hover:border-line-strong hover:bg-elevated"
              >
                下一张 <span aria-hidden="true">→</span>
              </RouterLink>
              <span v-else class="w-28"></span>
            </nav>

            <!-- 最后一张：“Go to Lab”—— 跳回章节页并滚动到 Wireshark 实验 -->
            <RouterLink
              v-if="isLast && ctaTarget"
              :to="`/chapters/${chapterId}#${ctaTarget}`"
              class="mt-6 flex items-center justify-center gap-2 rounded-xl bg-brand px-5 py-3 text-base font-semibold text-inverse transition hover:bg-brand-light"
            >
              Go to Lab <span aria-hidden="true">→</span>
            </RouterLink>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
