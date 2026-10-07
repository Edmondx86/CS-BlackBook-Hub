import { ref } from 'vue'

// 首页滚动状态：是否已离开走马灯区域（页头据此在“透明”与“半透明”之间切换）。
// HomeView 在滚动时更新，App.vue 读取它来切换页头背景。
export const headerScrolled = ref(false)
