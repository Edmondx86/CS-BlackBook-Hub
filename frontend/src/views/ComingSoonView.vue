<script setup>
// 「还在做」的占位页。
//
// 顶栏的《深入理解计算机系统》用它兜底：与其留一个点不动的死条目，
// 不如让人点进来看到一句明确的话，顺便指回已经上线的内容。
// 书名从路由 meta.title 取，将来再加别的书只要加一条路由即可。
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => route.meta?.title ?? '这本书')
</script>

<template>
  <div class="flex h-full flex-col text-primary antialiased">
    <div class="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center px-6 text-center">
      <div class="text-5xl" aria-hidden="true">🐣</div>

      <h1 class="mt-6 text-2xl font-bold text-primary">{{ title }}</h1>

      <p class="mt-4 text-lg font-semibold text-brand">还什么都没有哦~</p>

      <p class="mt-3 max-w-md text-sm leading-relaxed text-muted">
        这本书的学习内容还在制作中，章节、知识卡片和实验都还没上线。
        做好了会第一时间放在这里，欢迎过段时间再来看看。
      </p>

      <div class="mt-8 flex flex-wrap items-center justify-center gap-3">
        <RouterLink
          to="/chapters"
          class="rounded-lg bg-btn px-5 py-2.5 text-sm font-semibold text-btn-text transition hover:bg-btn-hover"
        >
          先去看看《计算机网络：自顶向下方法》
        </RouterLink>
        <RouterLink
          to="/"
          class="rounded-lg border border-line-strong px-5 py-2.5 text-sm font-medium text-secondary transition hover:bg-elevated hover:text-primary"
        >
          返回首页
        </RouterLink>
      </div>
    </div>
  </div>
</template>
