<script setup>
// 章节内的位置导航（左侧栏）。
//
// 把“本章的知识卡片”和“实验 / 练习”列成一份目录，并高亮当前所在的那一项，
// 让人在卡片页 / Lab 页随时知道自己在章节的哪个位置。
//
// 章节概览由父组件用 useChapter() 取好后传入（详情页本来就要这份数据），组件自身不发请求。
import { computed, ref, watch } from 'vue'
import { chapterFlashcards } from '../content/flashcards'

const props = defineProps({
  chapterId: { type: String, required: true },
  /** 章节概览（useChapter 的返回值），用于列出本章的实验 / 练习 */
  chapter: { type: Object, default: null },
  /** 'flashcard'：currentId 是卡片 slug；'lab'：currentId 是 lab id */
  currentKind: { type: String, default: '' },
  currentId: { type: String, default: '' },
})

const cards = computed(() => chapterFlashcards[props.chapterId] ?? [])
const wiresharkLabs = computed(() => props.chapter?.wireshark_labs ?? [])
const socketExercises = computed(() => props.chapter?.socket_exercises ?? [])
const allLabs = computed(() => [...wiresharkLabs.value, ...socketExercises.value])

const currentCardIndex = computed(() => cards.value.findIndex((c) => c.slug === props.currentId))
const currentLabIndex = computed(() => allLabs.value.findIndex((l) => l.id === props.currentId))

const isCurrentCard = (slug) => props.currentKind === 'flashcard' && props.currentId === slug
const isCurrentLab = (id) => props.currentKind === 'lab' && props.currentId === id

// “知识卡片 3 / 8”这类一句话定位
const positionLabel = computed(() => {
  if (props.currentKind === 'flashcard' && currentCardIndex.value >= 0) {
    return `知识卡片 ${currentCardIndex.value + 1} / ${cards.value.length}`
  }
  if (props.currentKind === 'lab' && currentLabIndex.value >= 0) {
    return `实验 ${currentLabIndex.value + 1} / ${allLabs.value.length}`
  }
  return ''
})

// 折叠状态持久化：Lab 页本来就是多栏，窄屏时用户多半想把它收起来
const STORAGE_KEY = 'chapterNavCollapsed'
const collapsed = ref(localStorage.getItem(STORAGE_KEY) === '1')
watch(collapsed, (value) => localStorage.setItem(STORAGE_KEY, value ? '1' : '0'))

const itemClass = (active) =>
  active
    ? 'bg-brand/10 font-medium text-brand'
    : 'text-tertiary transition hover:bg-elevated hover:text-primary'
</script>

<template>
  <aside
    class="shrink-0 flex-col border-r border-line bg-card/40 transition-[width] duration-200"
    :class="collapsed ? 'w-11' : 'w-60'"
  >
    <!-- 折叠开关 -->
    <div class="flex items-center gap-1.5 border-b border-line px-2 py-2">
      <button
        type="button"
        class="rounded-md p-1.5 text-muted transition hover:bg-elevated hover:text-primary"
        :title="collapsed ? '展开本章导航' : '收起本章导航'"
        :aria-label="collapsed ? '展开本章导航' : '收起本章导航'"
        :aria-expanded="!collapsed"
        @click="collapsed = !collapsed"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="h-4 w-4 transition-transform duration-200"
          :class="collapsed ? 'rotate-180' : ''"
          aria-hidden="true"
        >
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <span v-if="!collapsed" class="text-xs font-semibold uppercase tracking-widest text-brand">
        本章导航
      </span>
    </div>

    <!-- 展开态：章节 + 当前位置 + 卡片目录 + 实验目录 -->
    <nav v-if="!collapsed" class="min-h-0 flex-1 overflow-y-auto px-2 py-3 text-sm">
      <div class="px-2 pb-3">
        <RouterLink
          :to="`/chapters/${chapterId}`"
          class="text-xs font-semibold uppercase tracking-widest text-brand transition hover:underline"
        >
          {{ chapter?.number ?? 'Chapter' }}
        </RouterLink>
        <p v-if="chapter?.title" class="mt-1 text-xs leading-snug text-muted">{{ chapter.title }}</p>
        <p v-if="positionLabel" class="mt-2 rounded-md bg-brand/10 px-2 py-1 text-xs text-brand">
          {{ positionLabel }}
        </p>
      </div>

      <!-- 知识卡片 -->
      <section v-if="cards.length">
        <h3 class="px-2 pb-1 text-[11px] font-semibold uppercase tracking-widest text-faint">
          知识卡片
        </h3>
        <RouterLink
          v-for="(card, i) in cards"
          :key="card.slug"
          :to="`/chapters/${chapterId}/${card.slug}`"
          class="flex items-start gap-2 rounded-md px-2 py-1.5"
          :class="itemClass(isCurrentCard(card.slug))"
        >
          <span
            class="w-4 shrink-0 pt-px text-right text-xs"
            :class="isCurrentCard(card.slug) ? 'text-brand' : 'text-faint'"
          >
            {{ i + 1 }}
          </span>
          <span class="min-w-0 leading-snug">{{ card.title }}</span>
        </RouterLink>
      </section>

      <!-- 实验与练习 -->
      <section v-if="allLabs.length" class="mt-4">
        <h3 class="px-2 pb-1 text-[11px] font-semibold uppercase tracking-widest text-faint">
          实验与练习
        </h3>

        <template v-if="wiresharkLabs.length">
          <p class="px-2 pb-0.5 pt-1 text-[11px] text-faint">Wireshark</p>
          <RouterLink
            v-for="lab in wiresharkLabs"
            :key="lab.id"
            :to="`/chapters/${chapterId}/labs/${lab.id}`"
            class="block rounded-md px-2 py-1.5 leading-snug"
            :class="itemClass(isCurrentLab(lab.id))"
          >
            {{ lab.title }}
          </RouterLink>
        </template>

        <template v-if="socketExercises.length">
          <p class="px-2 pb-0.5 pt-2 text-[11px] text-faint">Socket 编程</p>
          <RouterLink
            v-for="ex in socketExercises"
            :key="ex.id"
            :to="`/chapters/${chapterId}/labs/${ex.id}`"
            class="block rounded-md px-2 py-1.5 leading-snug"
            :class="itemClass(isCurrentLab(ex.id))"
          >
            {{ ex.title }}
          </RouterLink>
        </template>
      </section>
    </nav>

    <!-- 折叠态：竖排标签，仍能看出这里是什么 -->
    <div v-else class="flex min-h-0 flex-1 justify-center pt-4">
      <span class="text-[11px] tracking-widest text-faint" style="writing-mode: vertical-rl">
        本章导航
      </span>
    </div>
  </aside>
</template>
