<script setup>
// 实验/练习卡片（章节页 Wireshark / Socket 区块）：悬停放大 + 右侧斜切渐变滑窗。
// props：
//   to    —— 点击跳转的目标路由
//   title —— 实验/练习标题
//   hint  —— 副标题（如 "Wireshark · 抓包分析"）
//   tone  —— 配色：'brand'（Wireshark，青绿）| 'theme'（Socket，紫）
import { computed } from 'vue'

const props = defineProps({
  to: { type: String, required: true },
  title: { type: String, required: true },
  hint: { type: String, default: '' },
  tone: { type: String, default: 'brand' },
})

const theme = computed(() => {
  if (props.tone === 'theme') {
    return {
      border: 'border-theme/30 hover:border-theme/70',
      // 实色（右）→ 半透明 → 全透明（左），透明度渐变
      panel: 'bg-gradient-to-l from-theme via-theme/70 to-transparent',
      arrow: 'text-primary',
    }
  }
  return {
    border: 'border-brand/30 hover:border-brand/70',
    panel: 'bg-gradient-to-l from-brand via-brand/70 to-transparent',
    arrow: 'text-inverse',
  }
})
</script>

<template>
  <RouterLink
    :to="to"
    class="group relative flex h-28 items-center overflow-hidden rounded-xl border bg-card transition-transform duration-300 hover:scale-[1.03]"
    :class="theme.border"
  >
    <!-- 左侧文字 -->
    <div class="relative z-10 px-6">
      <div class="text-lg font-semibold text-primary">{{ title }}</div>
      <div v-if="hint" class="mt-1 text-sm text-faint">{{ hint }}</div>
    </div>

    <!-- 右侧滑动窗：斜切（/）形状 + 透明度渐变，黄金分割 ≈ 61.8% -->
    <div
      class="slide-panel absolute inset-y-0 right-0 flex w-[61.8%] translate-x-full items-center justify-end pr-8 transition-transform duration-300 ease-out group-hover:translate-x-0"
      :class="theme.panel"
    >
      <span class="text-3xl font-bold" :class="theme.arrow" aria-hidden="true">→</span>
    </div>
  </RouterLink>
</template>

<style scoped>
/* 斜切平行四边形：左上角切掉一块，形成“/”走向的斜边 */
.slide-panel {
  clip-path: polygon(22% 0, 100% 0, 100% 100%, 0 100%);
}
</style>
