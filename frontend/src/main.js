import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import HomeView from './views/HomeView.vue'
import ChaptersView from './views/ChaptersView.vue'
import ChapterView from './views/ChapterView.vue'
import LabDetailView from './components/LabDetailView.vue'
import './style.css'
import './markdown.css'

// 路由层级：/ 首页大厅 → /chapters 章节目录 → /chapters/:chapterId 章节实验 → /chapters/:chapterId/labs/:labId Lab 详情
const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/chapters', name: 'chapters', component: ChaptersView },
  { path: '/chapters/:chapterId', name: 'chapter', component: ChapterView },
  { path: '/chapters/:chapterId/labs/:labId', name: 'lab', component: LabDetailView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

createApp(App).use(router).mount('#app')
