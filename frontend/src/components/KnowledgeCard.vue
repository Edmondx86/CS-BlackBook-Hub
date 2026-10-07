<script setup>
// 知识卡片（章节页网格卡片）：悬停放大 + 3D 翻转展示简介，点击跳转到详情页。
// props：
//   card  —— 单张卡片数据（来自 src/content/flashcards.js）
//   to    —— 点击跳转的目标路由
//   index —— 卡片序号（1 起），用于正面显示序号水印
defineProps({
  card: { type: Object, required: true },
  to: { type: String, required: true },
  index: { type: Number, default: 1 },
})
</script>

<template>
  <RouterLink
    :to="to"
    class="card-scene group block h-60 transition-transform duration-300 hover:scale-105"
  >
    <div class="flip-inner relative h-full w-full">
      <!-- 正面：序号水印 + 副标题 + 标题 + 金句 -->
      <div
        class="flip-face absolute inset-0 flex flex-col items-center justify-center rounded-xl border border-brand/20 bg-card p-5 text-center"
      >
        <span
          class="pointer-events-none absolute left-4 top-3 select-none text-5xl font-black text-brand/[var(--alpha-faint)]"
        >
          {{ String(index).padStart(2, '0') }}
        </span>
        <p class="text-[10px] font-semibold uppercase tracking-[0.2em] text-brand">
          {{ card.subtitle }}
        </p>
        <h3 class="mt-2 text-lg font-bold text-primary">{{ card.title }}</h3>
        <p class="mt-3 text-xs leading-relaxed text-muted">{{ card.frontSummary }}</p>
        <span class="absolute bottom-3 text-[10px] text-faint">悬停查看简介 · 点击进入</span>
      </div>

      <!-- 背面：简介（悬停时展示） -->
      <div
        class="flip-face flip-back absolute inset-0 flex flex-col justify-center rounded-xl border border-theme/30 bg-card p-5"
      >
        <p class="text-[10px] font-semibold uppercase tracking-widest text-theme-light">
          {{ card.subtitle }}
        </p>
        <h3 class="mt-1 text-lg font-bold text-primary">{{ card.title }}</h3>
        <p class="mt-3 text-xs leading-relaxed text-tertiary">{{ card.intro }}</p>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.card-scene {
  perspective: 1200px;
}
.flip-inner {
  transform-style: preserve-3d;
  transition: transform 0.5s cubic-bezier(0.4, 0.2, 0.2, 1);
}
.group:hover .flip-inner {
  transform: rotateY(180deg);
}
.flip-face {
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}
.flip-back {
  transform: rotateY(180deg);
}
</style>
