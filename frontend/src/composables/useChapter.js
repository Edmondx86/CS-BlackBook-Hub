// 章节概览的共享获取 + 进程内缓存。
//
// 详情页（卡片页 / Lab 页）与左侧的「本章导航」都要用同一份 `/api/v1/chapters/{id}` 概览，
// 这里把同一个 Promise 缓存起来，避免同一次渲染里重复请求同一个接口。
//
// 只在「成功」时保留缓存：失败会立刻删掉，这样网络恢复后重进页面还能重新拉取，
// 而不会把一个失败的 Promise 永久缓存住。
import { ref, watch } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const cache = new Map()

function fetchChapter(chapterId) {
  const cached = cache.get(chapterId)
  if (cached) return cached

  const pending = fetch(`${API_BASE}/api/v1/chapters/${chapterId}`)
    .then((res) => (res.ok ? res.json() : null))
    .catch(() => null)
    .then((data) => {
      if (!data) cache.delete(chapterId)
      return data
    })

  cache.set(chapterId, pending)
  return pending
}

/**
 * 读取章节概览。
 * @param {import('vue').Ref<string>|import('vue').ComputedRef<string>} chapterId 章节 id（响应式）
 * @returns {import('vue').Ref<object|null>} 章节概览；获取失败为 null
 */
export function useChapter(chapterId) {
  const chapter = ref(null)
  watch(
    chapterId,
    async (id) => {
      chapter.value = id ? await fetchChapter(id) : null
    },
    { immediate: true },
  )
  return chapter
}
