import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import HomeView from './views/HomeView.vue'
import './theme.css'
import './style.css'
import './markdown.css'
import './highlight.css'

// 颜色模式初始化：挂载前按本地存储写入 <html data-theme>，避免主题闪烁（默认夜间）。
if (localStorage.getItem('theme') === 'light') {
  document.documentElement.setAttribute('data-theme', 'light')
}

// 路由层级：/ 首页大厅 → /chapters 章节目录 → /chapters/:chapterId 章节实验 → /chapters/:chapterId/labs/:labId Lab 详情
//
// 路由级代码分割：首页（首屏要用）保持同步引入，其余页面一律改成动态 import，
// 各自打成独立 chunk，访问到对应路由时才下载，首屏只加载首页需要的代码。
const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/chapters', name: 'chapters', component: () => import('./views/ChaptersView.vue') },
  { path: '/chapters/:chapterId', name: 'chapter', component: () => import('./views/ChapterView.vue') },
  {
    path: '/chapters/:chapterId/:slug',
    name: 'flashcard',
    component: () => import('./views/FlashcardsView.vue'),
  },
  {
    path: '/chapters/:chapterId/labs/:labId',
    name: 'lab',
    component: () => import('./components/LabDetailView.vue'),
  },
  { path: '/about', name: 'about', component: () => import('./views/AboutView.vue') },
  { path: '/tools/:slug', name: 'tool', component: () => import('./views/ToolView.vue') },
  // 尚未开课的书：占位页，书名放 meta.title（见 ComingSoonView.vue）
  {
    path: '/csapp',
    name: 'csapp',
    component: () => import('./views/ComingSoonView.vue'),
    meta: { title: '《深入理解计算机系统》' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

createApp(App).use(router).mount('#app')
